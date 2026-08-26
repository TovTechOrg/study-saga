"""Schema/invariant validator for the live question corpus.

Checks cf-pages/functions/_lib/data.json (the file Pages Functions actually
serves) against the invariants the game logic assumes. Exits non-zero on any
violation, for use in CI (see .github/workflows/ci.yml) and locally:

    python backend/validate_corpus.py
"""
import json
import sys
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "cf-pages" / "functions" / "_lib" / "data.json"
VALID_TYPES = {"multiple_choice_single", "multiple_choice_multiple"}
REQUIRED_HINT_TIERS = {"easy", "medium", "hard"}


def check_question(realm, index, q, errors):
    where = f"{realm}[{index}]"

    qtype = q.get("type")
    if qtype not in VALID_TYPES:
        errors.append(f"{where}: invalid type {qtype!r}")

    text = q.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{where}: missing or empty text")

    options = q.get("options")
    if not isinstance(options, list) or len(options) < 2:
        errors.append(f"{where}: needs at least 2 options")
        options = []

    correct_count = 0
    for i, opt in enumerate(options):
        if not isinstance(opt, dict):
            errors.append(f"{where}.options[{i}]: not an object")
            continue
        if not isinstance(opt.get("text"), str) or not opt["text"].strip():
            errors.append(f"{where}.options[{i}]: missing or empty text")
        if not isinstance(opt.get("isCorrect"), bool):
            errors.append(f"{where}.options[{i}]: isCorrect must be a boolean")
        elif opt["isCorrect"]:
            correct_count += 1

    if qtype == "multiple_choice_single" and correct_count != 1:
        errors.append(f"{where}: multiple_choice_single must have exactly 1 correct option, found {correct_count}")
    elif qtype == "multiple_choice_multiple" and correct_count < 1:
        errors.append(f"{where}: multiple_choice_multiple must have at least 1 correct option, found {correct_count}")

    hints = q.get("hints")
    if not isinstance(hints, dict) or set(hints.keys()) != REQUIRED_HINT_TIERS:
        errors.append(f"{where}: hints must have exactly the keys {sorted(REQUIRED_HINT_TIERS)}, found {sorted(hints.keys()) if isinstance(hints, dict) else hints!r}")
    else:
        for tier, hint_text in hints.items():
            if not isinstance(hint_text, str) or not hint_text.strip():
                errors.append(f"{where}.hints[{tier}]: missing or empty")


def main():
    if not DATA_PATH.exists():
        print(f"ERROR: corpus file not found at {DATA_PATH}", file=sys.stderr)
        return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    syllabus = data.get("syllabus")
    if not isinstance(syllabus, list) or not syllabus:
        print("ERROR: top-level 'syllabus' must be a non-empty list", file=sys.stderr)
        return 1

    errors = []
    total_questions = 0
    for realm in syllabus:
        name = realm.get("name", "<unnamed>")
        questions = realm.get("questions")
        if not isinstance(questions, list) or not questions:
            errors.append(f"{name}: 'questions' must be a non-empty list")
            continue
        for i, q in enumerate(questions):
            check_question(name, i, q, errors)
        total_questions += len(questions)

    if errors:
        print(f"Corpus validation FAILED: {len(errors)} problem(s) across {total_questions} questions\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"Corpus validation passed: {total_questions} questions across {len(syllabus)} realms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
