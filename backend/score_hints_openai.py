import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def parse_samples(filepath, start_sample=14, end_sample=30):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    samples = []
    # Match block for a sample
    pattern = r"Sample #(\d+)\nQuestion: (.*?)\nOptions: (.*?)\nHint: \"(.*?)\""
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        num = int(match.group(1))
        if start_sample <= num <= end_sample:
            samples.append({
                "number": num,
                "question": match.group(2).strip(),
                "options": match.group(3).strip(),
                "hint": match.group(4).strip()
            })
    return samples

def evaluate_hint(sample):
    sys_prompt = """
You are an expert pedagogical evaluator. Evaluate the provided hint for a multiple choice question based on the following rubric:
1. Pedagogical Score (0-10): Rate how well the hint guides reasoning without giving away the answer. A 10/10 requires conceptual reasoning, eliminates distractors, and avoids literal spoilers. A hint that gives the answer away entirely gets a low score.
2. Strengths: List strengths (e.g., Concept-based cue, Discriminates distractors).
3. Penalties: List penalties (e.g., Definition Proximity, Functional Spoiler, Nickname Leakage, Answer Leakage, Trivializes Ambiguity).
4. Bloom Level: Estimate the Bloom's Taxonomy level required to answer (e.g., Level 1 (Remembering), Level 2 (Understanding), Level 3 (Applying)).
5. Notes: Provide a concise justification for the score with a summary of its strengths vs weaknesses.

Provide the response strictly in JSON format with the following keys:
"score" (number),
"strengths" (list of strings),
"penalties" (list of strings),
"bloom_level" (string),
"notes" (string)
"""
    user_prompt = f"Question: {sample['question']}\nOptions: {sample['options']}\nHint: {sample['hint']}"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return json.loads(response.choices[0].message.content)

def main():
    # Let's batch samples 14 through 23 (10 samples)
    start = 14
    end = 23
    samples = parse_samples("../diagnostic_sampling_120.txt", start_sample=start, end_sample=end)
    print(f"Found {len(samples)} samples to evaluate (Samples {start}-{end}).")
    
    results = []
    for s in samples:
        print(f"Evaluating Sample #{s['number']}...")
        try:
            eval_result = evaluate_hint(s)
            s['evaluation'] = eval_result
            results.append(s)
            print(f"  Score: {eval_result.get('score')}/10 - {eval_result.get('bloom_level')}")
            print(f"  Notes: {eval_result.get('notes')}")
        except Exception as e:
            print(f"Error evaluating Sample #{s['number']}: {e}")
    
    output_file = f"chatgpt_evaluations_{start}_{end}.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
