#!/usr/bin/env python3
"""Gemini-as-judge pass over the 800-topic Claude-authored tiered content
corpus (claude_tiered_batch*_{biology,chemistry,math,physics}.json).

Each topic file holds one object with three question tiers (easy/medium/hard,
each a 4-option multiple-choice question) and a matching hints object (three
hint tiers per question tier). Rather than one judge call per hint (9 calls
per topic -> 7200 calls total, far too slow at the free-tier 5 req/min pace),
this makes ONE combined call per topic that scores all three questions and
all nine hints together, keeping the run to 800 calls (~3 hours).

Resumable: results are saved to OUT_PATH after every topic, keyed by
filename, so a killed/interrupted run picks up where it left off.
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
# Must match bcp_full_bakeoff.py / regenerate_all_hints_gemini.py's override --
# rag_pipeline.py's own default (gemini-3-flash-preview) resolves to the
# "gemini-3-flash" quota bucket, which has only a 20-requests/day free-tier
# cap. gemini-3.5-flash-lite is the model that has actually processed
# hundreds of calls per day successfully elsewhere in this project.
os.environ["GEMINI_MODEL"] = "gemini-3.5-flash-lite"

from rag_pipeline import _call_gemini, GeminiRateLimitError, GeminiAPIError

API_KEY = os.environ["GEMINI_API_KEY"]
OUT_PATH = "tiered_content_judge_results.json"
SUBJECTS = ["biology", "chemistry", "math", "physics"]
TIERS = ["easy", "medium", "hard"]
MAX_CONSECUTIVE_FAILURES = 5

JUDGE_PROMPT_TEMPLATE = '''You are an expert Education Quality Assurance judge evaluating one full "tiered" trivia topic for a quiz game. The topic has THREE question tiers (easy/medium/hard), each a multiple-choice question with one correct option and three distractors, plus a "feedback" explanation for each option. It also has hints: for each question tier, there are three hint tiers (hard/medium/easy) a player can request before answering that specific question.

TOPIC: {topic}

QUESTIONS AND HINTS (JSON):
{payload}

Evaluate using these criteria:

Each question has a "type" field: "multiple_choice_single" means the player picks ONE answer and exactly one option should have isCorrect true; "multiple_choice_multiple" means the player picks ALL that apply and two or more options should have isCorrect true. Both are valid, supported question formats in this game -- do not penalize a "multiple_choice_multiple" question for having more than one correct option.

QUESTION CRITERIA (for each of easy/medium/hard):
1. Factual accuracy: the correct answer(s) must be genuinely correct, and each distractor's feedback must be factually accurate about why it's wrong.
2. Correct-answer count matches type: for "multiple_choice_single", verify exactly one option has isCorrect true and it is actually correct. For "multiple_choice_multiple", verify the set of options marked isCorrect true is exactly the full correct set implied by the question text (no correct option missing isCorrect true, no incorrect option wrongly marked true).
3. Plausible, distinct distractors: distractors should be genuinely different from each other and from the correct answer(s), not near-duplicates, and should represent believable misconceptions rather than absurd or obviously-wrong options.
4. Difficulty match: the question's actual conceptual depth should match its stated difficulty tier (easy = basic recall/definition, medium = explains a mechanism/relationship, hard = deeper reasoning, edge case, or synthesis).

HINT CRITERIA (for each hint, evaluated against the question it belongs to) -- each hint tier has a DIFFERENT expected proximity to the answer:
1. Factual accuracy: the hint must be strictly, mechanistically true.
2. Appropriate leakage for its tier: "hard" hints must require real reasoning and not leak the answer; "medium" hints may narrow it down more directly; "easy" hints are DESIGNED to point squarely at the answer and should be direct, but must not state the answer's exact text verbatim.
3. Not circular/vague: the hint must add real information beyond restating the question.

Score each question tier and each hint 1-10 (10 = flawless, 1 = broken/actively wrong). For any score below 8, give a brief one-sentence reason in "issues"; otherwise use "None".

Return ONLY a JSON object with this exact schema:
{{"questions": {{"easy": {{"score": <int>, "issues": <string>}}, "medium": {{"score": <int>, "issues": <string>}}, "hard": {{"score": <int>, "issues": <string>}}}}, "hints": {{"easy": {{"hard": {{"score": <int>, "issues": <string>}}, "medium": {{"score": <int>, "issues": <string>}}, "easy": {{"score": <int>, "issues": <string>}}}}, "medium": {{"hard": {{"score": <int>, "issues": <string>}}, "medium": {{"score": <int>, "issues": <string>}}, "easy": {{"score": <int>, "issues": <string>}}}}, "hard": {{"hard": {{"score": <int>, "issues": <string>}}, "medium": {{"score": <int>, "issues": <string>}}, "easy": {{"score": <int>, "issues": <string>}}}}}}, "critical_issues": <string, "None" if nothing severe like a wrong answer marked correct or a hint leaking the exact answer text>}}'''


def _build_payload(topic_obj):
    payload = {}
    for tier in TIERS:
        q = topic_obj[tier]
        payload[tier] = {
            "type": q.get("type"),
            "difficulty": q.get("difficulty"),
            "text": q["text"],
            "options": [{"text": o["text"], "isCorrect": o["isCorrect"], "feedback": o["feedback"]} for o in q["options"]],
            "hints": topic_obj["hints"][tier],
        }
    return payload


def judge_topic_gemini(topic_obj):
    payload = _build_payload(topic_obj)
    prompt = JUDGE_PROMPT_TEMPLATE.format(topic=topic_obj["topic"], payload=json.dumps(payload, indent=2))
    text = _call_gemini(prompt, API_KEY, max_tokens=2200, temperature=0.0)
    parsed = json.loads(text)
    for tier in TIERS:
        parsed["questions"][tier]["score"] = max(1, min(10, int(parsed["questions"][tier]["score"])))
        for hint_tier in TIERS:
            cell = parsed["hints"][tier][hint_tier]
            cell["score"] = max(1, min(10, int(cell["score"])))
    return parsed


def load_topics():
    """Each file holds an array of one or more topic objects (early batches
    bundled several topics per file; later batches wrote one per file), so
    files alone under-count -- key results per (file, index) topic instead."""
    topics = []
    for subj in SUBJECTS:
        for fname in sorted(glob.glob(f"claude_tiered_batch*_{subj}.json")):
            data = json.load(open(fname, encoding="utf-8"))
            for idx, topic_obj in enumerate(data):
                key = f"{fname}::{idx}" if len(data) > 1 else fname
                topics.append((key, subj, topic_obj))
    return topics


def load_results():
    if os.path.exists(OUT_PATH):
        return json.load(open(OUT_PATH, encoding="utf-8"))
    return {}


def is_complete(row):
    if row is None or "scores" not in row:
        return False
    s = row["scores"]
    try:
        all(s["questions"][t]["score"] for t in TIERS)
        all(s["hints"][t][h]["score"] for t in TIERS for h in TIERS)
        return True
    except (KeyError, TypeError):
        return False


def avg_score(scores):
    vals = [scores["questions"][t]["score"] for t in TIERS]
    vals += [scores["hints"][t][h]["score"] for t in TIERS for h in TIERS]
    return sum(vals) / len(vals)


def main():
    topics = load_topics()
    results = load_results()
    todo = [t for t in topics if not is_complete(results.get(t[0]))]
    print(f"{len(topics) - len(todo)}/{len(topics)} already done, {len(todo)} remaining.")

    consecutive_failures = 0
    for i, (key, subj, topic_obj) in enumerate(todo):
        try:
            scores = judge_topic_gemini(topic_obj)
            results[key] = {"subject": subj, "topic": topic_obj["topic"], "scores": scores}
            json.dump(results, open(OUT_PATH, "w", encoding="utf-8"), indent=2)
            avg = avg_score(scores)
            flag = " FLAGGED" if (scores.get("critical_issues", "None") != "None" or avg < 7) else ""
            done = sum(1 for r in results.values() if is_complete(r))
            print(f"[{i+1}/{len(todo)}] [{subj}] {topic_obj['topic'][:55]!r} -> avg {avg:.1f}{flag}  ({done}/{len(topics)} total complete)")
            consecutive_failures = 0
        except (GeminiRateLimitError, GeminiAPIError, json.JSONDecodeError, KeyError, ValueError, requests.exceptions.RequestException) as e:
            consecutive_failures += 1
            print(f"[{i+1}/{len(todo)}] [{subj}] {key} FAILED ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print("Too many consecutive failures -- stopping. Re-run this script later to resume (already-scored topics are cached).")
                break
            time.sleep(30)

    done = sum(1 for r in results.values() if is_complete(r))
    print(f"{len(topics) - done}/{len(topics)} remaining.")
    if done == len(topics):
        avgs = [avg_score(r["scores"]) for r in results.values()]
        flagged = [k for k, r in results.items() if is_complete(r) and (r["scores"].get("critical_issues", "None") != "None" or avg_score(r["scores"]) < 7)]
        print(f"\nAll {len(topics)} topics judged. Overall average score: {sum(avgs)/len(avgs):.2f}/10")
        print(f"Flagged for review ({len(flagged)}): {flagged}")


if __name__ == "__main__":
    main()
