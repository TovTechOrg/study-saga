"""
Lightweight RAG-style hint generator for quiz questions.
Uses a tiny in-memory KB and Flan-T5-small to produce short hints.
Falls back to deterministic text if the model is unavailable.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Dict, List
import json
import os

# Load external KB from JSON file (US-sourced, commercial-safe)
KB_PATH = os.path.join(os.path.dirname(__file__), "kb_external.json")
def load_external_kb() -> List[Dict[str, str]]:
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

KB: List[Dict[str, str]] = load_external_kb()


def retrieve_context(question_text: str) -> str:
    """Return hint (preferred) or context string for the given question, or a generic fallback."""
    q_clean = question_text.strip().lower()
    for item in KB:
        if item["question"].strip().lower() == q_clean:
            # Prefer 'hint' if present, else 'context'
            if "hint" in item and item["hint"].strip():
                return item["hint"].strip()
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
    Generate a robust hint using the KB 'hint' field if present, else context, else fallback.
    Copilot-safe: Always output a hint, even if only a conceptual reminder.
    """
    hint_or_context = retrieve_context(question_text)
    if hint_or_context and hint_or_context != "Use your reasoning on the topic to pick the best option.":
        return f"Hint: {hint_or_context}"
    # Copilot-safe fallback: always output a hint
    return "Hint: Recall the main concept or definition related to this question, even if it does not fully eliminate all incorrect options."
