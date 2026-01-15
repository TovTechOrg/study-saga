"""
Lightweight RAG-style hint generator for quiz questions.
Uses a tiny in-memory KB and Flan-T5-small to produce short hints.
Falls back to deterministic text if the model is unavailable.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Dict, List


# Minimal knowledge base with contexts for key questions.
KB: List[Dict[str, str]] = [
    {
        "question": "What is the powerhouse of the cell?",
        "context": "Mitochondria generate ATP via cellular respiration, powering the cell.",
    },
    {
        "question": "How many chromosomes do humans have?",
        "context": "Humans have 23 pairs of chromosomes, totaling 46 in somatic cells.",
    },
    {
        "question": "What is the pH of stomach acid?",
        "context": "Gastric acid is highly acidic; fasting gastric pH is roughly 1.5–3.5, often cited as ~3–4.",
    },
    {
        "question": "Which blood cells fight infections?",
        "context": "White blood cells (leukocytes) detect and attack pathogens to protect the body.",
    },
    {
        "question": "Which organ pumps blood?",
        "context": "The heart pumps oxygenated blood to the body and returns deoxygenated blood to the lungs.",
    },
    {
        "question": "What do plants use for photosynthesis",
        "context": "Plants use sunlight, water, carbon dioxide, and chlorophyll to produce glucose and oxygen.",
    },
]


def retrieve_context(question_text: str) -> str:
    """Return context string for the given question, or a generic fallback."""
    q_lower = question_text.strip().lower()
    for item in KB:
        if item["question"].strip().lower() == q_lower:
            return item["context"]
    return "Use your reasoning on the topic to pick the best option."


@lru_cache(maxsize=1)
def _get_pipeline():
    """Lazy-load the text generation pipeline to keep startup fast."""
    try:
        from transformers import pipeline

        return pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
            tokenizer="google/flan-t5-small",
        )
    except Exception:
        return None


def generate_hint(question_text: str, options: List[str]) -> str:
    """
    Generate a short hint using Flan-T5-small over retrieved context.
    Falls back to a deterministic hint if the model is unavailable.
    """
    context = retrieve_context(question_text)

    pipe = _get_pipeline()
    if pipe is None:
        # Fallback deterministic hint
        return f"Think about: {context}"

    prompt = (
        "Give one concise hint (<=20 words) for this multiple-choice question using the context. "
        "Do not state or repeat any option text.\n\n"
        f"Question: {question_text}\n"
        f"Options: {', '.join(options)}\n"
        f"Context: {context}\n"
        "Hint:"
    )

    output = pipe(
        prompt,
        max_new_tokens=32,
        num_beams=2,
        do_sample=False,
    )[0]["generated_text"].strip()

    # Light guardrail: mask any option words that leaked into the model output
    lowered = output.lower()
    for opt in options:
        opt_clean = opt.strip()
        if not opt_clean:
            continue
        if opt_clean.lower() in lowered:
            output = output.replace(opt_clean, "the correct option")
    return output
