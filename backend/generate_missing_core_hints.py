#!/usr/bin/env python3
"""
Resumable generator for core-subject questions in data.json that don't have
a "hints" field yet. Uses Groq (switched from Gemini: Gemini's free-tier
daily cap of 20 requests/day on gemini-3.5-flash / gemini-3-flash-preview was
too restrictive for bulk generation). Processes questions serially, saves
data.json after EVERY success so progress is never lost, and stops cleanly
if Groq's own retry/fallback logic (in generate_hint_groq) still can't get a
real hint -- detected via its placeholder-fallback text, since that function
returns a JSON string rather than raising on total failure.

Safe to re-run any time -- it always re-scans data.json for questions still
missing "hints" rather than tracking a separate static job list.
"""
import os
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_pipeline import generate_hint_groq

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
LOG_PATH = os.path.join(BASE_DIR, "groq_generation.log")

PLACEHOLDER_MARKERS = ("connection failed", "ai api error", "no hint available")


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_placeholder(hints: dict) -> bool:
    combined = " ".join(str(v) for v in hints.values()).lower()
    return any(marker in combined for marker in PLACEHOLDER_MARKERS)


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        log("ERROR: GROQ_API_KEY not set. Aborting.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    pending = []
    for syllabus in data.get("syllabus", []):
        for q in syllabus.get("questions", []):
            if not q.get("hints"):
                pending.append((syllabus.get("name"), q))

    if not pending:
        log("Nothing to do -- every core question already has hints.")
        return

    log(f"{len(pending)} questions still missing hints. Starting run (Groq)...")

    done = 0
    failed = 0
    consecutive_placeholder_failures = 0
    for syllabus_name, q in pending:
        qtext = q.get("text", q.get("question", ""))
        options = q.get("options", [])
        try:
            hints_raw = generate_hint_groq(qtext, options, api_key)
            hints = json.loads(hints_raw)
        except Exception as e:
            failed += 1
            log(f"FAILED (exception) [{syllabus_name}] {qtext[:60]} -> {e}")
            continue

        if is_placeholder(hints):
            failed += 1
            consecutive_placeholder_failures += 1
            log(f"FAILED (placeholder fallback) [{syllabus_name}] {qtext[:60]}")
            if consecutive_placeholder_failures >= 5:
                log("5 consecutive placeholder failures -- Groq likely rate-limited/exhausted. Stopping cleanly; resume later.")
                break
            continue

        consecutive_placeholder_failures = 0
        q["hints"] = hints
        # Persist immediately so a mid-run kill never loses progress.
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        done += 1
        log(f"OK [{syllabus_name}] {qtext[:60]}")

    remaining = len(pending) - done
    log(f"Run complete. Generated {done} new hints this run, {failed} failed, {remaining} still pending.")


if __name__ == "__main__":
    main()
