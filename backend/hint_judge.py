#!/usr/bin/env python3
"""
LLM-as-a-judge for hint quality, per the critique-and-verdict architecture
(chain-of-thought analysis BEFORE a verdict, to avoid the model just guessing
a score -- a judge that outputs a bare number tends to hallucinate the grade).

Three judge functions (Groq, Gemini, Claude) with the same rubric and return
shape. Claude never generates hints anywhere in this pipeline, so it judges
every subject in every phase with zero self-grading risk -- it's the primary
judge. The Groq/Gemini judges are kept for the cross-judge comparison that
originally surfaced the self-grading problem (Groq's judge missed a known
circular hint that Gemini's judge caught). Never let a model grade its own
output.
"""
import os
import sys
import json
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_pipeline import _call_gemini

JUDGE_PROMPT_TEMPLATE = '''You are an expert Education Quality Assurance judge evaluating an AI-generated
trivia hint for a quiz game. Rate the "{tier_label}" tier hint below.

CRITERIA -- note that each tier has a DIFFERENT expected proximity to the answer, and criterion 2
must be judged relative to that tier's own purpose, not a fixed absolute standard:
1. Factual accuracy: the hint must be strictly, mechanistically true. A clever-sounding but
   scientifically wrong analogy or claim is a serious failure, worse than a merely vague hint.
2. Appropriate leakage for this tier: "Hard" hints must not leak the answer or make it a trivial
   giveaway -- they should require real reasoning. "Medium" hints may narrow it down more directly.
   "Easy" hints are DESIGNED to point squarely at the answer -- being direct and naming a defining,
   near-identifying feature is the whole point of an Easy hint, not a flaw. Only penalize an Easy
   hint for literally stating the correct answer's exact text verbatim, not for being a strong clue.
3. Not circular/vague: the hint must add real information beyond restating the question, and must
   not be so generic it could equally describe a wrong option. (This applies at every tier -- even
   an Easy hint should add a genuine clue, not just rephrase the question.)
4. Multi-answer coverage: if there are multiple correct answers, the hint must give a way to
   distinguish EACH of them, not just the most distinctive one.

Question: {question}
Correct Answer(s): {correct_answer}
Hint ({tier_label} tier): {hint}

Think step by step: (1) what is the actual correct mechanism/fact behind the correct answer(s)?
(2) does the hint's claim match that mechanism/fact exactly, or does it get any detail wrong?
(3) judged against THIS tier's expected proximity to the answer (see criterion 2 above), does the
hint leak the answer's exact text or fail to engage the question at all? (4) if there are multiple
correct answers, does the hint address every one of them distinguishably?

Return ONLY a JSON object with this exact schema:
{{"analysis": "your step-by-step reasoning in 2-4 sentences", "issues": "specific factual errors, leakage, circularity, or coverage gaps found, or \\"None\\" if none", "score": <integer 1-10, where 10 is a flawless hint and 1 is broken/actively wrong>}}'''


def _build_prompt(question: str, correct_answer: str, hint: str, tier: str = "hard") -> str:
    return JUDGE_PROMPT_TEMPLATE.format(question=question, correct_answer=correct_answer, hint=hint, tier_label=tier.capitalize())


def _parse_judge_response(text: str) -> dict:
    try:
        parsed = json.loads(text)
        score = int(parsed.get("score", 0))
        score = max(1, min(10, score))
        return {
            "score": score,
            "analysis": str(parsed.get("analysis", "")),
            "issues": str(parsed.get("issues", "None")),
        }
    except Exception:
        return {"score": None, "analysis": "", "issues": f"Judge response unparseable: {text[:200]}"}


def judge_hint_quality_gemini(question: str, correct_answer: str, hint: str, api_key: str, tier: str = "hard") -> dict:
    """Gemini judges a hint (used for Groq-generated math hints in the composite setup)."""
    prompt = _build_prompt(question, correct_answer, hint, tier)
    try:
        text = _call_gemini(prompt, api_key, max_tokens=400, temperature=0.0)
        return _parse_judge_response(text)
    except Exception as e:
        return {"score": None, "analysis": "", "issues": f"Judge call failed: {e}"}


GEMMA_MODEL = "gemma-4-31b-it"


def judge_hint_quality_gemma(question: str, correct_answer: str, hint: str, api_key: str, tier: str = "hard") -> dict:
    """Gemma judges a hint, via the Gemini API (Gemma isn't hosted on Groq).
    Used as a fallback judge when Groq's judge is rate-limited -- NOT fully
    independent of Gemini (same provider/API key), but a different model
    architecture, and useful purely as a resilience fallback, not a primary
    self-grading-free judge."""
    import requests
    prompt = _build_prompt(question, correct_answer, hint, tier)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 3000,  # Gemma always "thinks" first; 1500 was still truncating mid-JSON on more detailed critiques
            "responseMimeType": "application/json",
        },
    }
    # 30s with zero retry meant a single slow response killed the call outright
    # -- the only recovery was waiting for an entire outer loop pass (90s+) to
    # retry that one item. Retry transient timeouts here instead, immediately.
    last_exc = None
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=60)
            break
        except requests.exceptions.RequestException as e:
            # Broadened from just Timeout -- a raw connection drop/protocol
            # error was slipping past this except clause entirely and
            # crashing the whole script instead of being recorded as one
            # failed item and moving on.
            last_exc = e
            continue
    else:
        return {"score": None, "analysis": "", "issues": f"Gemma judge call failed after 3 attempts: {last_exc}"}
    try:
        if response.status_code == 429:
            return {"score": None, "analysis": "", "issues": f"Gemma judge rate limited: {response.text[:200]}"}
        if response.status_code != 200:
            return {"score": None, "analysis": "", "issues": f"Gemma judge HTTP {response.status_code}: {response.text[:200]}"}
        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        return _parse_judge_response(text)
    except Exception as e:
        return {"score": None, "analysis": "", "issues": f"Gemma judge call failed: {e}"}


def judge_hint_quality_groq_with_gemma_fallback(question: str, correct_answer: str, hint: str, groq_key: str, gemini_key: str, tier: str = "hard") -> dict:
    """Groq judges first; if Groq is rate-limited (TPD/TPM), falls back to
    Gemma via the Gemini API instead of stalling. Records which judge actually
    produced the score so results stay traceable."""
    verdict = judge_hint_quality_groq(question, correct_answer, hint, groq_key, tier=tier)
    if verdict.get("score") is not None:
        verdict["judge"] = "groq"
        return verdict
    issues = (verdict.get("issues") or "").lower()
    if "tokens per day (tpd)" in issues or "rate limit reached for model" in issues:
        fallback = judge_hint_quality_gemma(question, correct_answer, hint, gemini_key, tier=tier)
        fallback["judge"] = "gemma" if fallback.get("score") is not None else "none"
        if fallback.get("score") is None:
            fallback["issues"] = f"Groq rate-limited AND Gemma fallback failed: {fallback.get('issues')}"
        return fallback
    verdict["judge"] = "none"
    return verdict


def _is_rate_limit_issue(issues: str) -> bool:
    t = (issues or "").lower()
    return any(s in t for s in ("429", "resource_exhausted", "rate limit", "quota", "rate-limited"))


def judge_hint_quality_gemini_with_gemma_fallback(question: str, correct_answer: str, hint: str, api_key: str, tier: str = "hard") -> dict:
    """Gemini judges first (the default primary judge going forward); if
    Gemini is rate-limited (per-minute OR the free-tier daily RPD cap -- see
    judge_tiered_content.py's postmortem on gemini-3-flash's 20/day wall),
    falls back to Gemma via the same Gemini API/key instead of stalling.
    Mirrors judge_hint_quality_groq_with_gemma_fallback's shape/semantics,
    just with Gemini as the primary instead of Groq. Records which judge
    actually produced the score so results stay traceable.

    NOT used by judge_tiered_content.py's 800-topic tiered-content pass --
    that pass intentionally stays Gemini-only for methodological consistency
    across the run. This is for judge work going forward."""
    verdict = judge_hint_quality_gemini(question, correct_answer, hint, api_key, tier=tier)
    if verdict.get("score") is not None:
        verdict["judge"] = "gemini"
        return verdict
    if _is_rate_limit_issue(verdict.get("issues")):
        fallback = judge_hint_quality_gemma(question, correct_answer, hint, api_key, tier=tier)
        fallback["judge"] = "gemma" if fallback.get("score") is not None else "none"
        if fallback.get("score") is None:
            fallback["issues"] = f"Gemini rate-limited AND Gemma fallback failed: {fallback.get('issues')}"
        return fallback
    verdict["judge"] = "none"
    return verdict


JUDGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string"},
        "issues": {"type": "string"},
        "score": {"type": "integer"},
    },
    "required": ["analysis", "issues", "score"],
    "additionalProperties": False,
}


def judge_hint_quality_claude(question: str, correct_answer: str, hint: str, api_key: str, model: str = "claude-haiku-4-5", tier: str = "hard") -> dict:
    """Claude judges a hint. Claude never generates hints in this pipeline, so this
    is the primary, self-grading-free judge for every subject in every phase."""
    import anthropic
    prompt = _build_prompt(question, correct_answer, hint, tier)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=400,
            temperature=0.0,
            output_config={"format": {"type": "json_schema", "schema": JUDGE_JSON_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in response.content if b.type == "text")
        return _parse_judge_response(text)
    except Exception as e:
        return {"score": None, "analysis": "", "issues": f"Judge call failed: {e}"}


def judge_hint_quality_groq(question: str, correct_answer: str, hint: str, api_key: str, model: str = "openai/gpt-oss-120b", tier: str = "hard") -> dict:
    """Groq judges a hint (used for Gemini-generated bio/chem/physics hints in the composite setup)."""
    import requests
    prompt = _build_prompt(question, correct_answer, hint, tier)
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600,
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=20,
        )
        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"]
            return _parse_judge_response(text)
        return {"score": None, "analysis": "", "issues": f"Judge HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"score": None, "analysis": "", "issues": f"Judge call failed: {e}"}
