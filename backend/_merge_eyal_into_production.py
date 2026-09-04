#!/usr/bin/env python3
"""Transform Eyal's 4 tiered subjects (geography, history, literature,
computer_science) from the topic-grouped/3x3-hint claude_tiered_batch*.json
format into the flat-question/single-hints-tier format used by production's
cf-pages/functions/_lib/data.json, and merge them in as new syllabus entries.

Does NOT touch the existing biology/math/chemistry/physics entries.
Writes to a separate output file first for review -- does not overwrite
data.json directly.
"""
import json
import glob

QTIERS = ["easy", "medium", "hard"]
SUBJECTS = ["geography", "history", "literature", "computer_science"]


def load_subject_topics(subject):
    topics = []
    for fname in sorted(glob.glob(f"claude_tiered_batch*_{subject}.json")):
        data = json.load(open(fname, encoding="utf-8"))
        topics.extend(data)
    return topics


def flatten_topic(topic):
    """One topic -> up to 3 flat questions (easy/medium/hard)."""
    questions = []
    for qtier in QTIERS:
        q = topic.get(qtier)
        if not q:
            continue
        hint_block = topic.get("hints", {}).get(qtier, {})
        flat = {
            "type": q["type"],
            "text": q["text"],
            "options": q["options"],
            "difficulty": q.get("difficulty", qtier),
            "hints": {
                "hard": hint_block.get("hard", ""),
                "medium": hint_block.get("medium", ""),
                "easy": hint_block.get("easy", ""),
            },
            "_hints_v2": True,
            "_topic": topic["topic"],  # provenance, harmless extra field
        }
        questions.append(flat)
    return questions


def main():
    new_syllabus_entries = []
    for subject in SUBJECTS:
        topics = load_subject_topics(subject)
        questions = []
        for topic in topics:
            questions.extend(flatten_topic(topic))
        new_syllabus_entries.append({"name": subject, "questions": questions})
        print(f"{subject}: {len(topics)} topics -> {len(questions)} flat questions")

    # Check for question-text collisions against existing production data
    # (get-hint.js matches hints by exact question text globally).
    prod = json.load(open("../cf-pages/functions/_lib/data.json", encoding="utf-8"))
    existing_texts = set()
    for syl in prod["syllabus"]:
        for q in syl["questions"]:
            existing_texts.add((q.get("text") or "").strip().lower())

    collisions = []
    for entry in new_syllabus_entries:
        for q in entry["questions"]:
            t = q["text"].strip().lower()
            if t in existing_texts:
                collisions.append((entry["name"], q["text"]))

    print(f"\nCollisions with existing production question text: {len(collisions)}")
    for subj, text in collisions[:20]:
        print(f"  [{subj}] {text[:80]}")

    # Check for internal collisions across the 4 new subjects themselves
    seen = {}
    internal_collisions = []
    for entry in new_syllabus_entries:
        for q in entry["questions"]:
            t = q["text"].strip().lower()
            if t in seen:
                internal_collisions.append((seen[t], entry["name"], q["text"]))
            else:
                seen[t] = entry["name"]
    print(f"Collisions within the 4 new subjects: {len(internal_collisions)}")
    for a, b, text in internal_collisions[:20]:
        print(f"  [{a}] vs [{b}] {text[:80]}")

    total_new_questions = sum(len(e["questions"]) for e in new_syllabus_entries)
    print(f"\nTotal new questions: {total_new_questions}")

    json.dump(new_syllabus_entries, open("_new_syllabus_entries.json", "w", encoding="utf-8"), indent=2)
    print("Written: backend/_new_syllabus_entries.json (review before merging into data.json)")


if __name__ == "__main__":
    main()
