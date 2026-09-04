#!/usr/bin/env python3
"""Merges the 800-topic Claude-authored tiered content corpus into the live
game's data file (cf-pages/functions/_lib/data.json).

Design decision (no pre-existing spec found for a difficulty-picker UI --
see conversation): each of a topic's 3 difficulty-tiered questions becomes
its OWN independent question entry in the syllabus's flat `questions` list,
tagged with a `difficulty` field, carrying its own 3-tier hints object.
This reuses the existing question/hint schema exactly (hints: {hard,
medium, easy} per question) -- no changes needed to combat-action.js,
get-hint.js, or the frontend. It just adds 2,400 more real, Gemini-judged
questions (9.98/10 avg) to the pool the game already draws from randomly.

Idempotent by content: re-running after adding more topics only adds
topics not already present (matched by exact question text), so this is
safe to re-run if Eyal's domains get merged later via a similar script,
or if more of Talia's topics are added.
"""
import os
import sys
import json
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "cf-pages", "functions", "_lib", "data.json")
SUBJECTS = ["biology", "chemistry", "math", "physics"]
TIERS = ["easy", "medium", "hard"]


def load_topics_for_subject(subject):
    topics = []
    for fname in sorted(glob.glob(os.path.join(BASE_DIR, f"claude_tiered_batch*_{subject}.json"))):
        data = json.load(open(fname, encoding="utf-8"))
        topics.extend(data)
    return topics


def build_question(tier_q, topic_hints_for_tier):
    return {
        "type": tier_q.get("type", "multiple_choice_single"),
        "text": tier_q["text"],
        "options": tier_q["options"],
        "difficulty": tier_q.get("difficulty"),
        "hints": topic_hints_for_tier,
    }


def main():
    data = json.load(open(DATA_PATH, encoding="utf-8"))
    syllabus_by_name = {s["name"]: s for s in data["syllabus"]}

    total_added = 0
    for subject in SUBJECTS:
        syllabus = syllabus_by_name.get(subject)
        if syllabus is None:
            print(f"WARNING: no syllabus named {subject!r} in data.json -- skipping.")
            continue

        existing_texts = {q["text"] for q in syllabus["questions"]}
        topics = load_topics_for_subject(subject)

        added = 0
        for topic in topics:
            for tier in TIERS:
                tier_q = topic[tier]
                if tier_q["text"] in existing_texts:
                    continue  # already merged (idempotent re-run)
                new_q = build_question(tier_q, topic["hints"][tier])
                syllabus["questions"].append(new_q)
                existing_texts.add(tier_q["text"])
                added += 1

        print(f"{subject}: +{added} questions (now {len(syllabus['questions'])} total)")
        total_added += added

    backup_path = DATA_PATH + ".pre-merge-backup"
    if not os.path.exists(backup_path):
        json.dump(json.load(open(DATA_PATH, encoding="utf-8")), open(backup_path, "w", encoding="utf-8"), indent=2)
        print(f"Backup written to {backup_path}")

    json.dump(data, open(DATA_PATH, "w", encoding="utf-8"), indent=2)
    print(f"\nTotal questions added: {total_added}")


if __name__ == "__main__":
    main()
