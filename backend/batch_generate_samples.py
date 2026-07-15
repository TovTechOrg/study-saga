"""
Batch Sample Generator for Study Saga Diagnostic Audit
========================================================
Reads biology questions from data.json, picks N unique ones (skipping
any already evaluated), calls the /api/get-hint endpoint for each,
and writes the results to a markdown file ready for AI Studio scoring.

Usage:
    python batch_generate_samples.py [--count 30] [--start 62]
"""

import json
import os
import random
import requests
import argparse
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
API_URL = "http://127.0.0.1:5000/api/get-hint"
OUTPUT_FILE = os.path.join(BASE_DIR, "batch_samples.md")


def load_questions(syllabus_name="biology"):
    """Load all questions for a given syllabus."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for entry in data.get("syllabus", []):
        if entry.get("name", "").lower() == syllabus_name.lower():
            return entry.get("questions", [])
    return []


def get_option_text(opt):
    """Extract text from an option (could be dict or string)."""
    if isinstance(opt, dict):
        return opt.get("text", str(opt))
    return str(opt)


def get_correct_answer(question):
    """Determine the correct answer text for a question."""
    opts = question.get("options", [])
    q_type = question.get("type", "multiple_choice_single")

    if q_type == "multiple_choice_multiple":
        correct_indices = set(question.get("answer_indices", []))
        if not correct_indices:
            correct_indices = set(
                i for i, opt in enumerate(opts)
                if (isinstance(opt, dict) and opt.get("isCorrect"))
            )
        return ", ".join(get_option_text(opts[i]) for i in sorted(correct_indices) if i < len(opts))
    else:
        correct_idx = question.get("answer_index")
        if correct_idx is None:
            for i, opt in enumerate(opts):
                if isinstance(opt, dict) and opt.get("isCorrect"):
                    correct_idx = i
                    break
            if correct_idx is None:
                correct_idx = 0
        if correct_idx < len(opts):
            return get_option_text(opts[correct_idx])
    return "Unknown"


def extract_hard_hint(hint_str):
    """Extract just the hard hint if the response is JSON with tiers."""
    try:
        parsed = json.loads(hint_str)
        if isinstance(parsed, dict) and "hard" in parsed:
            return parsed["hard"]
    except (json.JSONDecodeError, TypeError):
        pass
    return hint_str


def call_hint_api(question_text, options_text_list, max_retries=3):
    """Call the /api/get-hint endpoint with retry logic."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, json={
                "question": question_text,
                "options": options_text_list,
            }, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                hint = data.get("hint", "No hint returned.")
                # Check for error hints
                if "error" in hint.lower() or "No hint available" in hint:
                    if attempt < max_retries - 1:
                        wait = 10 * (attempt + 1)
                        print(f"    [Retry {attempt+1}] Got error, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                return hint
            else:
                if attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)
                    print(f"    [Retry {attempt+1}] HTTP {resp.status_code}, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return f"API Error (HTTP {resp.status_code})"
        except requests.exceptions.ConnectionError:
            return "ERROR: Backend not running (connection refused)"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(10)
                continue
            return f"ERROR: {e}"
    return "ERROR: All retries failed"


def main():
    parser = argparse.ArgumentParser(description="Batch generate hint samples")
    parser.add_argument("--count", type=int, default=30, help="Number of samples to generate")
    parser.add_argument("--start", type=int, default=62, help="Starting sample number")
    parser.add_argument("--syllabus", type=str, default="biology", help="Syllabus name")
    args = parser.parse_args()

    print(f"Loading {args.syllabus} questions from data.json...")
    questions = load_questions(args.syllabus)
    print(f"Found {len(questions)} total questions.")

    if len(questions) < args.count:
        print(f"WARNING: Only {len(questions)} questions available, reducing count.")
        args.count = len(questions)

    # Shuffle to avoid getting the same order every time
    indexed_questions = list(enumerate(questions))
    random.shuffle(indexed_questions)

    # Track seen question texts to avoid duplicates
    seen_texts = set()
    selected = []

    for idx, q in indexed_questions:
        q_text = q.get("question", q.get("text", ""))
        if q_text in seen_texts:
            continue
        seen_texts.add(q_text)
        selected.append((idx, q))
        if len(selected) >= args.count:
            break

    print(f"Selected {len(selected)} unique questions. Generating hints...")

    # Build output
    lines = []
    lines.append(f"# Batch Diagnostic Samples (#{args.start}–#{args.start + len(selected) - 1})")
    lines.append(f"")
    lines.append(f"**Syllabus**: {args.syllabus.title()}")
    lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Total Samples**: {len(selected)}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"Please rate each hint on a scale of 1-10 for pedagogical quality.")
    lines.append(f"For each sample, provide: Score (1-10) and a brief critique.")
    lines.append(f"")

    for i, (orig_idx, q) in enumerate(selected):
        sample_num = args.start + i
        q_text = q.get("question", q.get("text", ""))
        opts = q.get("options", [])
        opts_text = [get_option_text(o) for o in opts]
        correct = get_correct_answer(q)
        q_type = q.get("type", "multiple_choice_single")

        print(f"  [{i+1}/{len(selected)}] Generating hint for: {q_text[:60]}...")

        hint_raw = call_hint_api(q_text, opts_text)
        
        # Try to parse the hint as JSON to get tiers
        easy, medium, hard = "N/A", "N/A", hint_raw
        try:
            # First, clean the raw string in case it's double-encoded or has extra text
            clean_raw = hint_raw.strip()
            if clean_raw.startswith("```json"):
                clean_raw = clean_raw.replace("```json", "").replace("```", "").strip()
            
            hint_data = json.loads(clean_raw)
            if isinstance(hint_data, dict):
                easy = hint_data.get("easy", "N/A")
                medium = hint_data.get("medium", "N/A")
                hard = hint_data.get("hard", "N/A")
        except Exception:
            pass

        # Longer delay to respect Groq API rate limits  
        time.sleep(5)

        lines.append(f"### Sample #{sample_num}")
        lines.append(f"- **Question**: \"{q_text}\"")
        lines.append(f"- **Type**: {q_type}")
        lines.append(f"- **Options**: {opts_text}")
        lines.append(f"- **Correct Answer**: {correct}")
        lines.append(f"- **Hint (Hard)**: \"{hard}\"")
        lines.append(f"- **Hint (Medium)**: \"{medium}\"")
        lines.append(f"- **Hint (Easy)**: \"{easy}\"")
        lines.append(f"- **Progression Quality Score**: __ / 10")
        lines.append(f"- **Your Critique**: ")
        lines.append(f"")

    # Write to file
    output = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\nDone! {len(selected)} samples written to: {OUTPUT_FILE}")
    print(f"   Open this file and paste into Google AI Studio for batch scoring.")


if __name__ == "__main__":
    main()
