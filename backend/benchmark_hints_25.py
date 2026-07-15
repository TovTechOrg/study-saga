import requests
import json
import random
import os
import sys

API_URL = "http://127.0.0.1:5000/api/get-hint"
DATA_PATH = "backend/data.json"

def score_hint(question, options, hint):
    """
    Score the quality of a hint.
    100: Perfect KB match or High-Quality RAG.
    70: Semantic fallback (Reasonable).
    20: Generic fallback (Low quality).
    0: Error/Empty.
    -50 Penalty if answer is in hint (LEAK).
    -20 Penalty if hint is a generic label (e.g. "Basic subtraction") or < 15 chars.
    """
    if not hint or "No hint available" in hint:
        return 0, "Failed"
    
    score = 0
    reason = ""
    
    # Identify the answer
    answer = ""
    for opt in options:
        if isinstance(opt, dict) and opt.get('isCorrect'):
            answer = str(opt.get('text', '')).lower()
            break
    
    # Check for direct answer leakage
    if answer and answer in hint.lower():
        score -= 50
        reason += "[LEAK] "

    # Determine retrieval type based on pattern
    if "Think about how" in hint and "relates to the options" in hint:
        score += 20
        reason += "Generic Fallback"
    elif "Think about how" in hint:
        score += 70
        reason += "Semantic Fallback"
    else:
        score += 100
        reason += "Direct KB Match"
        
    # Pedagogy Stricter Rules
    label_patterns = ["basic math", "biology fact", "calculation", "definition", "science fact"]
    definition_phrases = ["this theory suggests", "this process refers to", "explains that", "refers to", "suggests that", "is a process", "is the theory", "basically means"]
    functional_spoilers = ["powerhouse", "exterior", "entire exterior", "weight", "percentage of your", "named after", "gravity", "apple", "urine", "bean-shaped"]
    
    if any(p in hint.lower() for p in label_patterns) or len(hint) < 15:
        score -= 20
        reason += "[Low Pedagogical Value] "
    
    if any(p in hint.lower() for p in definition_phrases):
        score -= 30
        reason += "[Definition-style Hint] "

    if any(p in hint.lower() for p in functional_spoilers):
        score -= 30
        reason += "[Functional Spoiler Hint] "
        
    return max(0, score), reason

def run_benchmark():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_questions = []
    for syllabus in data.get("syllabus", []):
        for q in syllabus.get("questions", []):
            all_questions.append(q)

    # Calculate Unique Coverage
    unique_ids = set()
    for q in all_questions:
        unique_ids.add(q["text"])
    
    unique_count = len(unique_ids)
    
    if unique_count < 30:
        print(f"WARNING: Only {unique_count} unique questions found. Benchmark total samples (30) will contain duplicates.")
        test_questions = [random.choice(all_questions) for _ in range(30)]
    else:
        test_questions = random.sample(all_questions, 30)

    results = []
    total_score = 0
    unique_tested = set()

    print(f"{'#':<3} | {'Score':<5} | {'Type':<20} | {'Question Summary'}")
    print("-" * 100)

    for i, q in enumerate(test_questions):
        unique_tested.add(q["text"])
        payload = {
            "question": q["text"],
            "options": q["options"]
        }
        
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            if resp.status_code == 200:
                hint = resp.json().get("hint", "")
            else:
                hint = "No hint available (API error)"
        except Exception as e:
            hint = f"No hint available (Connection error: {e})"

        score, reason = score_hint(q["text"], q["options"], hint)
        total_score += score
        
        results.append({
            "idx": i+1,
            "question": q["text"],
            "hint": hint,
            "score": score,
            "reason": reason
        })
        
        q_summary = (q["text"][:45] + '...') if len(q["text"]) > 45 else q["text"]
        print(f"{i+1:<3} | {score:<5} | {reason:<25} | {q_summary}")

    avg_score = total_score / len(test_questions)
    coverage_pct = (len(unique_tested) / unique_count) * 100 if unique_count > 0 else 0
    
    print("-" * 100)
    print(f"AVERAGE QUALITY SCORE  : {avg_score:.2f} / 100")
    print(f"UNIQUE COVERAGE %      : {coverage_pct:.1f}% ({len(unique_tested)}/{unique_count})")
    
    status = "EXCELLENT" if avg_score > 90 else "GOOD" if avg_score > 75 else "FAIR" if avg_score > 50 else "POOR"
    print(f"FINAL RATING           : {status}")

    # Output detailed report to file
    with open("benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "average": avg_score, 
            "coverage_pct": coverage_pct,
            "unique_count": unique_count,
            "rating": status, 
            "results": results
        }, f, indent=2)

if __name__ == "__main__":
    run_benchmark()
