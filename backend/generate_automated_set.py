import re
import json
import requests
import os
import sys
from rag_pipeline import generate_hint_groq
from dotenv import load_dotenv

# Ensure stdout can handle Unicode characters on Windows
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def generate_automated_set(count, start, syllabus_name):
    output_file = "backend/automated_samples.md"
    data_path = "backend/data.json"
    
    # Load dataset
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find the syllabus/syllabi
    syllabi_list = data.get('syllabus', [])
    if syllabus_name.lower() == "all":
        num_syllabi = len(syllabi_list)
        if num_syllabi == 0:
            print("Error: No syllabi found.")
            return
        count_per_syllabus = max(1, count // num_syllabi)
        subset_with_syllabus = []
        for s in syllabi_list:
            s_questions = s.get('questions', [])
            s_subset = s_questions[start:start+count_per_syllabus]
            for q in s_subset:
                subset_with_syllabus.append((q, s['name']))
        count = len(subset_with_syllabus)
    else:
        syllabus = next((s for s in syllabi_list if s['name'].lower() == syllabus_name.lower()), None)
        if not syllabus:
            print(f"Error: Syllabus '{syllabus_name}' not found.")
            return
        questions = syllabus.get('questions', [])
        subset_with_syllabus = [(q, syllabus_name) for q in questions[start:start+count]]
    
    api_key = os.environ.get("GROQ_API_KEY", "")

    header = f"# Automated Diagnostic Samples (#0–#{count-1})\n\n**Syllabus**: {syllabus_name}\n**Generated**: 2026-05-12\n\n---\n\n"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)

    for i, (q, s_name) in enumerate(subset_with_syllabus):
        q_text = q.get('question', q.get('text', ''))
        options = q.get('options', [])
        # Correct answer extraction for report
        correct_list = [opt['text'] for opt in q.get('options', []) if opt.get('isCorrect') or opt.get('is_answer')]
        correct = ", ".join(correct_list) if correct_list else "Unknown"
        
        print(f"[{i+1}/{len(subset_with_syllabus)}] Generating hint for {s_name.capitalize()}...")
        
        hints_raw = generate_hint_groq(q_text, options, api_key)
        try:
            hints = json.loads(hints_raw)
        except:
            hints = {"hard": hints_raw, "medium": "Error parsing", "easy": "Error parsing"}
        
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"### Sample #{i}\n")
            f.write(f"- **Question**: \"{q_text}\"\n")
            f.write(f"- **Correct Answer**: {correct}\n")
            f.write(f"- **Hint (Hard)**: \"{hints.get('hard', 'N/A')}\"\n")
            f.write(f"- **Hint (Medium)**: \"{hints.get('medium', 'N/A')}\"\n")
            f.write(f"- **Hint (Easy)**: \"{hints.get('easy', 'N/A')}\"\n\n")
        
        import time
        time.sleep(2)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate automated hint samples.")
    parser.add_argument("--count", type=int, default=5, help="Number of questions to process")
    parser.add_argument("--start", type=int, default=0, help="Start index in the syllabus")
    parser.add_argument("--syllabus", type=str, default="biology", help="Syllabus name (e.g. biology, physics)")
    args = parser.parse_args()
    
    generate_automated_set(args.count, args.start, args.syllabus)
