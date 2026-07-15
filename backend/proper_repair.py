#!/usr/bin/env python3
import re
import json
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path to import rag_pipeline
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_pipeline import generate_hint_groq

# No longer using dummy placeholder list – we regenerate every hint

DUMMY_HINTS = [
    "Consider a challenging scenario that requires deep reasoning related to the question.",
    "Think about a moderately complex aspect of the question without giving away the answer.",
    "Recall a basic fact relevant to the question that does not reveal the answer.",
    "A light gas.",
    "A tiny atom.",
    "A balloon filler.",
    "Think deeply.",
    "A basic truth.",
    "A vital gas.",
    "Connection failed",
    "AI API error",
    "No hint available",
    "Consider",
    "Imagine",
    "Think of"
]

def proper_repair():
    # Locate .env for GROQ_API_KEY
    env_file = "backend/.env"
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        # fallback search in possible locations
        for candidate in [".env", "backend/.env", "../backend/.env"]:
            if os.path.exists(candidate):
                with open(candidate, "r") as f:
                    for line in f:
                        if line.startswith('GROQ_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
                if api_key:
                    break
    if not api_key:
        print("Error: GROQ_API_KEY not found.")
        return

    files_to_repair = ["automated_samples.md", "expanded_samples.md"]

    for filename in files_to_repair:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            print(f"File {filepath} not found.")
            continue
        print(f"\nProcessing {filename}...")
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_question = ""
        current_answer = ""
        repaired_count = 0
        i = 0
        while i < len(lines):
            line = lines[i]
            q_match = re.search(r'- \*\*Question\*\*: "(.*?)"', line)
            if q_match:
                current_question = q_match.group(1).strip()
            a_match = re.search(r'- \*\*Correct Answer\*\*: (.*)', line)
            if a_match:
                current_answer = a_match.group(1).strip()
            hint_match = re.search(r'- \*\*Hint \((Hard|Medium|Easy)\)\*\*: ?"?(.*?)"?$', line)
            if hint_match:
                # Always regenerate hints for this sample
                options = [current_answer]
                hints_raw = generate_hint_groq(current_question, options, api_key)
                try:
                    new_hints = json.loads(hints_raw)
                except Exception:
                    new_hints = {"hard": "N/A", "medium": "N/A", "easy": "N/A"}
                def safe_trunc(h):
                    if len(h) > 200:
                        t = h[:196]
                        ls = t.rfind(" ")
                        if ls > 150:
                            t = t[:ls]
                        return t + "..."
                    return h
                hard = safe_trunc(new_hints.get("hard", "N/A"))
                medium = safe_trunc(new_hints.get("medium", "N/A"))
                easy = safe_trunc(new_hints.get("easy", "N/A"))
                # Find the line where the Hard hint starts (might be current line or a few lines earlier)
                start_idx = i
                while start_idx >= 0 and not lines[start_idx].lstrip().startswith("- **Hint (Hard)**:"):
                    start_idx -= 1
                if start_idx >= 0:
                    lines[start_idx] = re.sub(r'- \*\*Hint \(Hard\)\*\*: ".*?"', f'- **Hint (Hard)**: "{hard}"', lines[start_idx])
                    if start_idx + 1 < len(lines):
                        lines[start_idx+1] = re.sub(r'- \*\*Hint \(Medium\)\*\*: ".*?"', f'- **Hint (Medium)**: "{medium}"', lines[start_idx+1])
                    if start_idx + 2 < len(lines):
                        lines[start_idx+2] = re.sub(r'- \*\*Hint \(Easy\)\*\*: ".*?"', f'- **Hint (Easy)**: "{easy}"', lines[start_idx+2])
                repaired_count += 1
                # Respect Groq rate limit
                time.sleep(3.5)
                # Skip past the three hint lines we just processed
                i = start_idx + 2
            i += 1
        # Write back the repaired file
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"Successfully repaired {repaired_count} samples in {filename}!")

if __name__ == "__main__":
    proper_repair()
