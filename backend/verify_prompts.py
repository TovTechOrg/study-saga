import os
import json
from dotenv import load_dotenv
from rag_pipeline import generate_hint_groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def test_prompt(question, options, label):
    print(f"\n--- Testing: {label} ---")
    print(f"Question: {question}")
    hint_json = generate_hint_groq(question, options, GROQ_API_KEY)
    try:
        hints = json.loads(hint_json)
        print(json.dumps(hints, indent=2))
    except:
        print(f"Fallback/Error Output: {hint_json}")

if __name__ == "__main__":
    # Test 1: Alveoli (The failure case)
    test_prompt(
        "Which part of the respiratory system is responsible for exchanging oxygen and carbon dioxide between the air and the blood?",
        [
            {"text": "Trachea", "is_answer": False},
            {"text": "Bronchi", "is_answer": False},
            {"text": "Alveoli", "is_answer": True},
            {"text": "Diaphragm", "is_answer": False}
        ],
        "Alveoli (Sample #27 Fix)"
    )

    # Test 2: Prokaryotes (Multi-select)
    test_prompt(
        "Which are prokaryotic organisms?",
        [
            {"text": "Bacteria", "is_answer": True},
            {"text": "Archaea", "is_answer": True},
            {"text": "Humans", "is_answer": False},
            {"text": "Fungi", "is_answer": False}
        ],
        "Prokaryotes (Multi-select / Sample #28)"
    )
