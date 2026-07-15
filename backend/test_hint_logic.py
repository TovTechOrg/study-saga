
import os
import json
import re

# Mock KB loading to ensure we test the logic exactly as it is in the file
def load_kb_mock():
    # Copying the exact entry from kb_external.json
    return [
        {"question": "Which hormone regulates blood sugar?", "hint": "Insulin lowers blood sugar by promoting glucose uptake; adrenaline and cortisol raise blood sugar, while thyroxine, testosterone, and estrogen have different roles."}
    ]

KB = load_kb_mock()

def get_hint_from_kb(question: str) -> str:
    q_clean = question.strip().lower()
    # Remove common punctuation
    q_words = set(re.findall(r'\w+', q_clean))
    
    print(f"[DEBUG] get_hint_from_kb called with: '{question}'")
    print(f"Q Words: {q_words}")
    
    best_match = None
    best_score = 0.0
    
    for entry in KB:
        entry_q = entry.get('question', '').strip().lower()
        entry_words = set(re.findall(r'\w+', entry_q))
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(q_words.intersection(entry_words))
        union = len(q_words.union(entry_words))
        
        if union == 0:
            continue
            
        score = intersection / union
        print(f"Checking '{entry_q}' -> Score: {score}")
        
        # If we have a very high match, use it
        if score > 0.4:  # 40% word overlap is sufficient given the limited domain
            if score > best_score:
                best_score = score
                best_match = entry
    
    if best_match:
        print(f"[DEBUG] Match found (score {best_score:.2f}). Returning hint: {best_match.get('hint', 'No hint available')}")
        return best_match.get('hint', 'No hint available')
        
    print(f"[DEBUG] No match found in KB. Best score was {best_score:.2f}")
    return None

# Test the specific case
question = "Which hormone regulates blood sugar?"
hint = get_hint_from_kb(question)
print("\nFINAL RESULT:", hint)
