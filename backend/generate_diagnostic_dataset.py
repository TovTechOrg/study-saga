import requests
import json
import random
import os

API_URL = "http://127.0.0.1:5000/api/get-hint"
DATA_PATH = "backend/data.json"
OUTPUT_FILE = "diagnostic_sampling_120.txt"

def generate_samples():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_questions = []
    for syllabus in data.get("syllabus", []):
        for q in syllabus.get("questions", []):
            all_questions.append(q)

    # Exclude baseline questions
    baseline_questions = [
        "What organelle converts sugar into energy in cells?",
        "What is the largest organ in the human body?",
        "Which theory explains the origin of mitochondria and chloroplasts?"
    ]
    
    filtered_questions = [q for q in all_questions if q["text"] not in baseline_questions]

    # Sample exactly 117 (or all if less)
    target_count = min(117, len(filtered_questions))
    samples = random.sample(filtered_questions, target_count)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("--- PHASE 1: DIAGNOSTIC SAMPLING (120 SAMPLES) ---\n")
        out.write("Goal: Collect raw system behavior for ChatGPT scoring.\n\n")
        
        for i, q in enumerate(samples):
            payload = {
                "question": q["text"],
                "options": q["options"]
            }
            
            try:
                resp = requests.post(API_URL, json=payload, timeout=5)
                hint = resp.json().get("hint", "No hint available") if resp.status_code == 200 else "API Error"
            except Exception as e:
                hint = f"Connection Error: {e}"

            out.write(f"Sample #{i+1}\n")
            out.write(f"Question: {q['text']}\n")
            out.write(f"Options: {[opt['text'] if isinstance(opt, dict) else opt for opt in q['options']]}\n")
            out.write(f"Hint: \"{hint}\"\n")
            out.write("-" * 50 + "\n\n")

    print(f"Generated {target_count} samples in {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_samples()
