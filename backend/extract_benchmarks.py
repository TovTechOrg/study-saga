import re
import json
import os
import sys

# Ensure stdout can handle UTF-8 symbols in the report
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    # Fallback for environments where reconfigure is not available
    pass

REPORT_PATH = r"C:\Users\talia\.gemini\antigravity\brain\30f8a4e7-f5f9-4083-908a-da02baa7bfe9\diagnostic_report.md"
OUTPUT_PATH = r"c:\Users\talia\Desktop\study-saga\backend\benchmarks.json"

def extract_benchmarks():
    if not os.path.exists(REPORT_PATH):
        print(f"Error: {REPORT_PATH} not found.")
        return

    with open(REPORT_PATH, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    print(f"DEBUG: Content length: {len(content)}")
    # Regex to find sample blocks - looking for "### #"
    samples = re.split(r'### \d+\.', content)
    print(f"DEBUG: Samples split into {len(samples)} blocks")
    
    benchmarks = []
    
    for i, sample in enumerate(samples[1:]): # Skip preamble
        # Extract Score - look for "Score:" followed by a number anywhere
        score_match = re.search(r'Score\D*(\d+(?:\.\d+)?)', sample, re.IGNORECASE | re.DOTALL)
        
        score = 0
        if score_match:
            score = float(score_match.group(1))
        else:
            continue
            
        if score < 8.0:
            continue
            
        # Extract Question - look for "- **Question**:" and grab everything until the end of the line
        q_match = re.search(r'Question\D*(.*)', sample, re.IGNORECASE)
        question = q_match.group(1).replace('"', '').strip() if q_match else "Unknown"
        
        # Extract Hints - be broad
        hints = {}
        hard_match = re.search(r'Hard\s*(?:\(Hard\))?\s*\*?:\s*(.*?)(?:\n|-)', sample, re.IGNORECASE)
        med_match = re.search(r'Medium\s*(?:\(Medium\))?\s*\*?:\s*(.*?)(?:\n|-)', sample, re.IGNORECASE)
        easy_match = re.search(r'Easy\s*(?:\(Easy\))?\s*\*?:\s*(.*?)(?:\n|-)', sample, re.IGNORECASE)
        
        if hard_match: hints["hard"] = hard_match.group(1).replace('"', '').strip()
        if med_match: hints["medium"] = med_match.group(1).replace('"', '').strip()
        if easy_match: hints["easy"] = easy_match.group(1).replace('"', '').strip()
        
        # Extract Target Answer
        ans_target = re.search(r'Answer\D*(.*?)(?:\n|$)', sample, re.IGNORECASE)
        target = ans_target.group(1).strip() if ans_target else "Unknown"

        if hints and question != "Unknown":
            benchmarks.append({
                "question": question,
                "target": target,
                "hints": hints,
                "score": score
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmarks, f, indent=2)
        
    print(f"Extracted {len(benchmarks)} high-quality benchmarks to {OUTPUT_PATH}")

if __name__ == "__main__":
    extract_benchmarks()
