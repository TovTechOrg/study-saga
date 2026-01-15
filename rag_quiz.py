"""
Tiny RAG-style quiz helper using Flan-T5-small.
- Knowledge base: questions, options, answers, explanations.
- Retrieval: pick context for a given question (exact match fallback).
- LLM: generate a hint/explanation from retrieved context.
- Quiz loop: show question/options, generate hint, mock user selection, check correctness.
"""

import random
from transformers import pipeline

# 1) Mini knowledge base
KB = [
    {
        "question": "What is the powerhouse of the cell?",
        "options": ["Mitochondria", "Nucleus", "Ribosome", "Chloroplast"],
        "answer": "Mitochondria",
        "context": "Mitochondria generate ATP via cellular respiration, powering most cell activities.",
    },
    {
        "question": "How many chromosomes do humans have?",
        "options": ["23", "46", "48", "52"],
        "answer": "46",
        "context": "Humans have 23 pairs of chromosomes, totaling 46 in somatic cells.",
    },
    {
        "question": "What is the pH of stomach acid?",
        "options": ["7", "3-4", "10", "14"],
        "answer": "3-4",
        "context": "Gastric acid is highly acidic; fasting gastric pH is roughly 1.5–3.5, often cited as ~3–4.",
    },
]

# 2) Retrieval: pick relevant context (simple exact or fallback to first)
def retrieve_context(question_text: str) -> dict:
    for item in KB:
        if item["question"].strip().lower() == question_text.strip().lower():
            return item
    return KB[0]  # fallback


# 3) LLM: generate hint using Flan-T5-small (CPU-friendly)
hint_gen = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    tokenizer="google/flan-t5-small",
)


def generate_hint(item: dict) -> str:
    prompt = (
        "Provide a short, helpful hint for this quiz question using the context.\n\n"
        f"Question: {item['question']}\n"
        f"Options: {', '.join(item['options'])}\n"
        f"Context: {item['context']}\n"
        "Hint:"
    )
    out = hint_gen(prompt, max_new_tokens=40, num_beams=2, do_sample=False)[0]["generated_text"]
    return out.strip()


# 4) Quiz loop (single pass demo)
def run_quiz_once():
    item = random.choice(KB)
    print("\nQUESTION:", item["question"])
    for i, opt in enumerate(item["options"], 1):
        print(f"{i}. {opt}")

    # Generate and show hint
    hint = generate_hint(item)
    print("\nHINT:", hint)

    # Mock user selection (random for demo)
    user_idx = random.randint(0, len(item["options"]) - 1)
    user_answer = item["options"][user_idx]
    print(f"\nUser picked: {user_answer}")

    # Check correctness
    if user_answer == item["answer"]:
        print("Result: CORRECT ✅")
    else:
        print(f"Result: INCORRECT ❌ (correct: {item['answer']})")


if __name__ == "__main__":
    # Install tip (if needed): pip install transformers sentencepiece
    run_quiz_once()
