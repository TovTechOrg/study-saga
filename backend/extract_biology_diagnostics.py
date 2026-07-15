import re
import json
import os

def extract_biology_diagnostics():
    data_path = "backend/data.json"
    diag_path = "diagnostic_sampling_120.txt"
    output_path = "backend/biology_diagnostic_samples.md"

    if not os.path.exists(data_path) or not os.path.exists(diag_path):
        print("Data files not found.")
        return

    # Load biology questions from data.json
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    biology_syllabus = next((s for s in data.get('syllabus', []) if s['name'].lower() == 'biology'), None)
    if not biology_syllabus:
        print("Biology syllabus not found in data.json")
        return

    bio_questions = set()
    for q in biology_syllabus.get('questions', []):
        q_text = q.get('question', q.get('text', '')).strip().lower()
        # Clean string for matching
        q_clean = re.sub(r'[^\w\s]', '', q_text)
        bio_questions.add(q_clean)

    # Read diagnostic_sampling_120.txt
    with open(diag_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Parse samples
    pattern = r"Sample #(\d+)\nQuestion: (.*?)\nOptions: (.*?)\nHint: \"(.*?)\"\n--------------------------------------------------"
    matches = re.finditer(pattern, content, re.DOTALL)

    bio_samples = []
    for match in matches:
        num = int(match.group(1))
        question = match.group(2).strip()
        options = match.group(3).strip()
        hint = match.group(4).strip()

        # Clean question for matching
        q_clean = re.sub(r'[^\w\s]', '', question.lower())
        
        # Check if it's in the biology set
        if q_clean in bio_questions or "cell" in q_clean or "neuron" in q_clean or "blood" in q_clean or "fungi" in q_clean or "starfish" in q_clean or "dna" in q_clean or "genetics" in q_clean or "mitosis" in q_clean or "kidney" in q_clean or "photosynthesis" in q_clean:
            bio_samples.append({
                "number": num,
                "question": question,
                "options": options,
                "hint": hint
            })

    # Write to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Biology Diagnostic Samples (extracted from diagnostic_sampling_120.txt)\n\n")
        f.write("**Syllabus**: Biology\n\n---\n\n")
        
        for sample in bio_samples:
            f.write(f"### Sample #{sample['number']}\n")
            f.write(f"- **Question**: \"{sample['question']}\"\n")
            f.write(f"- **Options**: {sample['options']}\n")
            f.write(f"- **Hint (Hard)**: \"{sample['hint']}\"\n")
            f.write(f"- **Hint (Medium)**: \"N/A\"\n")
            f.write(f"- **Hint (Easy)**: \"N/A\"\n\n")

    print(f"Successfully extracted {len(bio_samples)} biology samples to {output_path}")

if __name__ == "__main__":
    extract_biology_diagnostics()
