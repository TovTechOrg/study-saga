#!/usr/bin/env python3
"""
One-off merge: pulls clean, pre-generated tiered hints (Hard/Medium/Easy) from the
curated sample files into data.json, keyed by exact question text match.

Run once (idempotent): re-running just re-applies the same merge.
Source of truth for matches is _hint_inventory_cache.json (built by inventory_hints.py).
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
INVENTORY_PATH = os.path.join(BASE_DIR, "_hint_inventory_cache.json")


def norm(q):
    return re.sub(r'\s+', ' ', q or '').strip().lower()


def main():
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = 0
    skipped_bad = 0
    missing = []

    for syllabus in data.get("syllabus", []):
        for q in syllabus.get("questions", []):
            qtext = norm(q.get("text", q.get("question", "")))
            entry = inventory.get(qtext)
            if not entry:
                missing.append({"syllabus": syllabus.get("name"), "question": q.get("text", q.get("question", ""))})
                continue
            if entry["bad"]:
                skipped_bad += 1
                missing.append({"syllabus": syllabus.get("name"), "question": q.get("text", q.get("question", ""))})
                continue
            q["hints"] = {
                "hard": entry["hard"].strip(),
                "medium": entry["medium"].strip(),
                "easy": entry["easy"].strip(),
            }
            merged += 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Merged clean hints into {merged} questions.")
    print(f"Skipped (placeholder/bad): {skipped_bad}")
    print(f"Still missing hints: {len(missing)}")

    with open(os.path.join(BASE_DIR, "_missing_core_hints.json"), "w", encoding="utf-8") as f:
        json.dump(missing, f, ensure_ascii=False, indent=2)
    print("Wrote list of still-missing questions to backend/_missing_core_hints.json")


if __name__ == "__main__":
    main()
