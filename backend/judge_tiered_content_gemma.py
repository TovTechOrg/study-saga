#!/usr/bin/env python3
"""Same 800-topic tiered-content judge pass as judge_tiered_content.py, but
with Gemma (via the Gemini API, since Gemma isn't hosted on Groq) as the
judge instead of Gemini -- for a direct comparison between the two judges
on the identical rubric/prompt/schema. Reuses the prompt/payload/scoring
helpers from judge_tiered_content.py so the two runs are apples-to-apples;
only the underlying model call differs.

Separate output file (OUT_PATH) so this never touches the Gemini results.
Resumable, same pattern as judge_tiered_content.py.
"""
import os
import sys
import json
import glob
import time
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from judge_tiered_content import JUDGE_PROMPT_TEMPLATE, _build_payload, TIERS, avg_score, is_complete, load_topics

API_KEY = os.environ["GEMINI_API_KEY"]
OUT_PATH = "tiered_content_judge_results_gemma.json"
GEMMA_MODEL = "gemma-4-31b-it"
MAX_CONSECUTIVE_FAILURES = 10
MIN_INTERVAL_SEC = 2.0  # Gemma's free tier isn't paced by rag_pipeline.py's
                        # 13s/gemini-specific logic; a light delay is still
                        # polite/safer than hammering it with zero pacing.
_last_call_at = [0.0]


def _call_gemma_raw(prompt, max_tokens=4500):
    elapsed = time.time() - _last_call_at[0]
    if elapsed < MIN_INTERVAL_SEC:
        time.sleep(MIN_INTERVAL_SEC - elapsed)
    _last_call_at[0] = time.time()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            # Gemma always "thinks" first, consuming tokens before the actual
            # JSON answer -- this combined per-topic prompt is much larger
            # than a single-hint judge call, so budget generously.
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }
    last_exc = None
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=90)
            break
        except requests.exceptions.RequestException as e:
            last_exc = e
            continue
    else:
        raise RuntimeError(f"Gemma call failed after 3 attempts: {last_exc}")

    if response.status_code == 429:
        raise RuntimeError(f"Gemma rate limited: {response.text[:300]}")
    if response.status_code != 200:
        raise RuntimeError(f"Gemma HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemma response shape ({e}): {data}")


def judge_topic_gemma(topic_obj):
    payload = _build_payload(topic_obj)
    prompt = JUDGE_PROMPT_TEMPLATE.format(topic=topic_obj["topic"], payload=json.dumps(payload, indent=2))
    text = _call_gemma_raw(prompt)
    parsed = json.loads(text)
    for tier in TIERS:
        parsed["questions"][tier]["score"] = max(1, min(10, int(parsed["questions"][tier]["score"])))
        for hint_tier in TIERS:
            cell = parsed["hints"][tier][hint_tier]
            cell["score"] = max(1, min(10, int(cell["score"])))
    return parsed


def load_results():
    if os.path.exists(OUT_PATH):
        return json.load(open(OUT_PATH, encoding="utf-8"))
    return {}


def main():
    topics = load_topics()
    results = load_results()
    todo = [t for t in topics if not is_complete(results.get(t[0]))]
    print(f"{len(topics) - len(todo)}/{len(topics)} already done, {len(todo)} remaining.")

    consecutive_failures = 0
    for i, (key, subj, topic_obj) in enumerate(todo):
        try:
            scores = judge_topic_gemma(topic_obj)
            results[key] = {"subject": subj, "topic": topic_obj["topic"], "scores": scores}
            json.dump(results, open(OUT_PATH, "w", encoding="utf-8"), indent=2)
            avg = avg_score(scores)
            flag = " FLAGGED" if (scores.get("critical_issues", "None") != "None" or avg < 7) else ""
            done = sum(1 for r in results.values() if is_complete(r))
            print(f"[{i+1}/{len(todo)}] [{subj}] {topic_obj['topic'][:55]!r} -> avg {avg:.1f}{flag}  ({done}/{len(topics)} total complete)")
            consecutive_failures = 0
        except (RuntimeError, json.JSONDecodeError, KeyError, ValueError, requests.exceptions.RequestException) as e:
            consecutive_failures += 1
            print(f"[{i+1}/{len(todo)}] [{subj}] {key} FAILED ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print("Too many consecutive failures -- stopping. Re-run this script later to resume (already-scored topics are cached).")
                break
            # Gemma's backend has been intermittently throwing transient
            # 500/503s tonight (not a quota wall -- successes interleave
            # with failures within a run), so back off progressively longer
            # per consecutive failure rather than a fixed short sleep, to
            # ride through a bad patch without needing a manual resume.
            time.sleep(min(90, 15 * consecutive_failures))

    done = sum(1 for r in results.values() if is_complete(r))
    print(f"{len(topics) - done}/{len(topics)} remaining.")
    if done == len(topics):
        avgs = [avg_score(r["scores"]) for r in results.values()]
        flagged = [k for k, r in results.items() if is_complete(r) and (r["scores"].get("critical_issues", "None") != "None" or avg_score(r["scores"]) < 7)]
        print(f"\nAll {len(topics)} topics judged. Overall average score: {sum(avgs)/len(avgs):.2f}/10")
        print(f"Flagged for review ({len(flagged)}): {flagged}")


if __name__ == "__main__":
    main()
