import os
import json
import re
# Load KB from kb_external.json
def load_kb():
    try:
        kb_path = os.path.join(os.path.dirname(__file__), 'kb_external.json')
        log_msg = f"[DEBUG] Loading KB from: {kb_path}\n"
        
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
            
        # Flatten if wrapped in a list or dict
        if isinstance(kb_data, dict):
            kb_data = list(kb_data.values())
            
        if isinstance(kb_data, list):
            # Normalize data: Add 'text' field for compatibility with legacy retrieval
            for entry in kb_data:
                if 'text' not in entry:
                    q = entry.get('question', '')
                    h = entry.get('hint', '')
                    entry['text'] = f"{q} {h}".strip()
                    
            log_msg += f"[DEBUG] KB loaded successfully with {len(kb_data)} entries.\n"
            # Write to log file specifically for debugging
            try:
                with open("hint_debug_load.log", "a", encoding="utf-8") as lf:
                    lf.write(log_msg)
            except: 
                pass
            print(log_msg)
            return kb_data
            
        log_msg += "[DEBUG] KB loaded with 0 entries (unexpected format).\n"
        print(log_msg)
        return []
    except Exception as e:
        import traceback
        err = f"[ERROR] Failed to load KB: {e}\n{traceback.format_exc()}\n"
        try:
            with open("hint_debug_load.log", "a", encoding="utf-8") as lf:
                lf.write(err)
        except:
            pass
        print(err)
        return []

KB = load_kb()

def get_hint_from_kb(question: str) -> str:
    global KB
    if not KB:
        print("[DEBUG] KB is empty, attempting to reload...")
        KB = load_kb()

    q_clean = question.strip().lower()
    # Remove common punctuation
    import re
    q_words = set(re.findall(r'\w+', q_clean))
    
    log_file = "hint_matching.log"
    debug_msg = f"\n--- Matching '{question}' ---\n"
    debug_msg += f"Tokens: {q_words}\n"
    debug_msg += f"KB Size: {len(KB)}\n"
    debug_msg += f"KB Content Sample: {[k.get('question') for k in KB[:5]] if KB else 'Empty'}\n" # Log first 5 questions
    
    print(f"[DEBUG] get_hint_from_kb called with: '{question}'")
    
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
        
        if score > 0.1: # Log only decent matches
             debug_msg += f"  vs '{entry_q}' -> {score:.4f} (Int: {intersection}, Union: {union})\n"
        
        # If we have a very high match, use it
        if score > 0.4:  # 40% word overlap is sufficient given the limited domain
            if score > best_score:
                best_score = score
                best_match = entry
    
    if best_match:
        final_hint = best_match.get('hint', 'No hint available')
        debug_msg += f"MATCH FOUND! Score: {best_score:.4f} -> {final_hint}\n"
        try:
             with open(log_file, "a", encoding="utf-8") as f:
                 f.write(debug_msg)
        except: pass
        
        print(f"[DEBUG] Match found (score {best_score:.2f}). Returning hint: {final_hint}")
        return final_hint
        
    debug_msg += f"NO MATCH. Best score: {best_score:.4f}\n"
    try:
         with open(log_file, "a", encoding="utf-8") as f:
             f.write(debug_msg)
    except: pass
    
    print(f"[DEBUG] No match found in KB. Best score was {best_score:.2f}")
    return None
import requests

def generate_hint_groq(question: str, options: list, api_key: str) -> str:
    """
    Commercial-safe hint generation using Groq Llama 3 API.
    Paraphrases the answer to generate an original, pedagogically sound hint.
    """
    import requests
    answers_list = []
    for opt in options:
        if isinstance(opt, dict) and (opt.get('is_answer') or opt.get('isCorrect')):
            answers_list.append(opt.get('text'))
        elif isinstance(opt, str) and not answers_list:
            # Fallback for simple string list (assuming first is answer or handled elsewhere)
            answers_list.append(opt)
    
    target_answers = ", ".join(answers_list) if answers_list else ""
    # If no answers found, fallback to first option
    # Extract distractors from options
    distractors = []
    if options:
        for opt in options:
            opt_text = opt['text'] if isinstance(opt, dict) else opt
            if opt_text.lower() not in target_answers.lower():
                distractors.append(opt_text)
    distractors_str = ", ".join(distractors)

    # Fact extraction step
    fact_prompt = f'''
Extract exactly 3 concise trivia facts about the Target Answers that would help generate a layered hint.
CRITICAL: Replace any direct mentions of the Target Answers "{target_answers}" in the facts with "[REDACTED]".
Focus on mechanisms and analogies.

Question: {question}
Target Answers: {target_answers}
Facts (as a JSON list):
'''
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # API Request with Retry Logic
    def call_groq(payload, max_retries=5):
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429: # Rate limit
                    error_msg = ""
                    try:
                        error_msg = response.json().get("error", {}).get("message", "")
                    except Exception:
                        pass
                    
                    if "tokens per day" in error_msg.lower() or "tpd" in error_msg.lower():
                        current_model = payload.get("model", "")
                        if current_model == "llama-3.3-70b-versatile":
                            print(f"[TPD Rate Limit] Daily limit reached for {current_model}. Falling back to llama-3.1-8b-instant...")
                            payload["model"] = "llama-3.1-8b-instant"
                            continue
                    
                    import time
                    wait_sec = 60 if attempt == 0 else 90
                    print(f"[429 Rate Limit in call_groq] Sleeping for {wait_sec} seconds to reset sliding window. Error: {error_msg}")
                    time.sleep(wait_sec)
                else:
                    import time
                    print(f"[API Error in call_groq] Status {response.status_code}: {response.text}")
                    time.sleep(2)
            except Exception as e:
                import time
                print(f"[Exception in call_groq] {e}")
                time.sleep(2)
        return None

    fact_data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a trivia fact extractor."},
            {"role": "user", "content": fact_prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }
    
    fact_response = call_groq(fact_data)
    facts = []
    if fact_response:
        try:
            content = fact_response.json()["choices"][0]["message"]["content"].strip()
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = list(parsed.values())
            if isinstance(parsed, list):
                cleaned_facts = []
                for item in parsed:
                    if isinstance(item, str):
                        cleaned_facts.append(item)
                    elif isinstance(item, dict):
                        val = item.get('fact', item.get('text', ''))
                        if not val and item:
                            val = next(iter(item.values()))
                        if isinstance(val, str):
                            cleaned_facts.append(val)
                facts = cleaned_facts
        except Exception:
            facts = []

    # Tiered hint prompt using extracted facts
    context_facts = "\n".join(facts) if facts else question
    prompt = f'''
You are a Trivia Game Master. Your goal is to guide the player to the Target Answers "{target_answers}" using analogies.

### GUIDELINES:
- ANALOGY FRESHNESS: Use scientific analogies appropriate to the concept's domain:
  * For micro-level concepts (cells, DNA, atoms, chemical reactions, molecules), use cellular, biochemical, molecular, or subatomic metaphors.
  * For macro-level concepts (organisms, ecosystems, food chains, physics, math equations), use macro-system metaphors (ecosystems, celestial systems, computing/logical flows, architectural frameworks, or physical machinery).
  * Avoid forcing micro-cellular analogies on macro-level concepts (e.g. do not describe a predator as "cells" or a math equation as "mitosis").
- NO LEAKAGE: Never use the target words "{target_answers}" or their obvious roots.
- NO PLACEHOLDERS: Do not output the literal word "[REDACTED]" in your hints. Instead, describe the concept or use appropriate general terms (e.g., "these cells", "this mechanism", "these particles", "this quantity").
- DEFINITION AVOIDANCE: If the correct answer defines a concept named in the question (e.g., "What is photosynthesis?"), do NOT use simple, common definitions or obvious direct associations (like "capturing sunlight to make food"). Instead, describe the mechanism using highly abstract scientific analogies (e.g., "an assembly line wrapping photons into chemical bonds").
- CONTEXTUAL CLUE: Use the following facts (where the answer may be [REDACTED]) to build your hint:
{context_facts}

### FORMAT:
Return EXACTLY 3 hints as a JSON object.
{{"hard": "Intricate scientific analogy", "medium": "Mechanism-based clue", "easy": "Simpler functional description"}}
'''
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a Trivia Game Master."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    hint_response = call_groq(data)
    if hint_response:
        result = hint_response.json()
        content = result["choices"][0]["message"]["content"].strip()
        try:
            hints = json.loads(content)
            hints = {k: get_safe_hint(v, target_answers) for k, v in hints.items()}
            return json.dumps(hints)
        except Exception:
            return content
    else:
        return json.dumps({"hard": "Connection failed", "medium": "AI API error", "easy": "No hint available"})


def get_safe_hint(hint: str, answers_str: str) -> str:
    """
    Masking-based answer-leak scrubber (not wiping): replaces leaked answer
    words with "[concept]" in place, preserving the rest of the hint's quality
    instead of discarding it outright.
    """
    # Clean up any leftover [REDACTED] placeholders from LLM copy-paste
    hint = hint.replace("[REDACTED]", "these components").replace("[redacted]", "these components")

    hint_clean = hint.lower()
    for ans in answers_str.split(", "):
        ans_clean = ans.strip().lower()
        if not ans_clean or len(ans_clean) < 3:
            continue
        # Block exact string match
        if ans_clean in hint_clean:
            pattern = re.compile(re.escape(ans_clean), re.IGNORECASE)
            hint = pattern.sub("[concept]", hint)
        # Block significant word match
        glue_words = {"the", "and", "ion", "cell", "acid", "base", "gas", "data"}
        ans_words = [w for w in re.findall(r"\w+", ans_clean) if len(w) > 4 and w not in glue_words]
        for word in ans_words:
            if word in hint_clean:
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                hint = pattern.sub("[concept]", hint)
    return hint


"""
RAG pipeline for game knowledge base: embedding, retrieval, and LLM hint generation.
"""

import os
from typing import List, Dict
from functools import lru_cache

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    SentenceTransformer = None
    np = None

# KB definition removed - already loaded via load_kb() above

@lru_cache(maxsize=1)
def get_model():
    if SentenceTransformer is None:
        raise ImportError("sentence-transformers not installed")
    # You can switch to a more advanced model for better semantic retrieval, e.g. 'all-mpnet-base-v2'
    return SentenceTransformer('all-mpnet-base-v2')

@lru_cache(maxsize=1)
def get_kb_embeddings():
    model = get_model()
    texts = [item['text'] for item in KB]
    return np.array(model.encode(texts, show_progress_bar=False))

def retrieve_context(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    if SentenceTransformer is None or np is None:
        # Fallback: return first N
        return KB[:top_k]
    model = get_model()
    kb_emb = get_kb_embeddings()
    query_emb = model.encode([query])[0]
    scores = np.dot(kb_emb, query_emb) / (np.linalg.norm(kb_emb, axis=1) * np.linalg.norm(query_emb) + 1e-8)
    # Increase top_k for broader context retrieval
    top_k_retrieval = max(top_k, 5)
    top_idx = np.argsort(scores)[::-1][:top_k_retrieval]
    return [KB[i] for i in top_idx]

# LLM hint generation (reuse rag_helper or add OpenAI/Azure API here)
def generate_hint(query: str, options: List[str]) -> str:
    # 1. Try to get a direct hint from KB
    kb_hint = get_hint_from_kb(query)
    if kb_hint:
        return kb_hint
    # 2. Fallback: semantic retrieval (legacy)
    if SentenceTransformer is None or np is None:
        return "No hint available (embedding model not installed)."
    contexts = retrieve_context(query, top_k=8)
    model = get_model()
    query_emb = model.encode([query])[0]
    selected_facts = []
    for c in contexts:
        fact_emb = model.encode([c['text']])[0]
        score = float(np.dot(fact_emb, query_emb) / (np.linalg.norm(fact_emb) * np.linalg.norm(query_emb) + 1e-8))
        if score >= 0.65:
            selected_facts.append(c['text'])
    if selected_facts:
        best_fact = selected_facts[0]
        return f"Consider this: {best_fact}"
    else:
        # Better fallback: use keywords from the options
        opt_preview = ", ".join(options[:3])
        return f"Look closely at the differences between options like {opt_preview}. One of these is fundamentally different in its function."


# ---------------------------------------------------------------------------
# Gemini "Iteration 4" pipeline: fact extraction -> tiered hint generation,
# with strict structural quotas, Pydantic validation, and tenacity-based
# exponential back-off. Reuses get_safe_hint() for answer-leak masking.
# ---------------------------------------------------------------------------
import time
import requests
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# gemini-3.5-flash turned out to be paid-tier-only (hence the harsh 20/day cap).
# gemini-3-flash-preview is on the actual free tier: 5 requests/minute, much
# higher daily ceiling. Pace calls to stay safely under the per-minute limit
# rather than relying purely on reactive 429 back-off.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MIN_INTERVAL_SEC = float(os.getenv("GEMINI_MIN_INTERVAL_SEC", "13"))
_last_call_at = [0.0]


class HintModel(BaseModel):
    hard: str
    medium: str
    easy: str


class GeminiRateLimitError(Exception):
    pass


class GeminiAPIError(Exception):
    pass


def _call_gemini_raw(prompt: str, api_key: str, max_tokens: int = 800, temperature: float = 0.7) -> str:
    # Proactive pacing: stay under the 5-req/min free-tier limit instead of
    # just reacting to 429s after the fact.
    elapsed = time.time() - _last_call_at[0]
    if elapsed < GEMINI_MIN_INTERVAL_SEC:
        time.sleep(GEMINI_MIN_INTERVAL_SEC - elapsed)
    _last_call_at[0] = time.time()

    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            # Disable extended thinking: on gemini-3.5-flash it was consuming the
            # entire token budget before the actual JSON answer, truncating output.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    response = requests.post(url, json=payload, timeout=30)
    if response.status_code == 429:
        raise GeminiRateLimitError(response.text)
    if response.status_code != 200:
        raise GeminiAPIError(f"HTTP {response.status_code}: {response.text}")
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiAPIError(f"Unexpected response shape ({e}): {data}")


@retry(
    retry=retry_if_exception_type((GeminiRateLimitError, GeminiAPIError)),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_gemini(prompt: str, api_key: str, **kwargs) -> str:
    return _call_gemini_raw(prompt, api_key, **kwargs)


def _extract_facts_gemini(question: str, target_answers: str, api_key: str) -> list:
    """Step 1: exactly 4 distinct facts + 1 surprising fact, answer pre-redacted."""
    fact_prompt = f'''
Extract exactly 4 distinct factual details about the Target Answers, plus exactly 1 surprising or lesser-known fact, useful for building a layered trivia hint.
CRITICAL: Replace any direct mention of the Target Answers "{target_answers}" in the facts with "[REDACTED]".

Question: {question}
Target Answers: {target_answers}

Return ONLY a JSON object: {{"facts": ["fact1", "fact2", "fact3", "fact4"], "surprising_fact": "..."}}
'''
    try:
        text = _call_gemini(fact_prompt, api_key, max_tokens=300, temperature=0.6)
        parsed = json.loads(text)
        facts = list(parsed.get("facts", []))
        surprising = parsed.get("surprising_fact", "")
        if surprising:
            facts.append(surprising)
        return facts
    except Exception:
        return []


def generate_hint_gemini(question: str, options: list, api_key: str) -> str:
    """
    Iteration-4 pipeline (facts -> tiered hints), mirroring generate_hint_groq's
    answer/distractor handling but on Gemini, with strict structural quotas,
    Pydantic schema validation, and a JSON-repair retry before falling back.
    """
    answers_list = []
    for opt in options:
        if isinstance(opt, dict) and (opt.get('is_answer') or opt.get('isCorrect')):
            answers_list.append(opt.get('text'))
        elif isinstance(opt, str) and not answers_list:
            answers_list.append(opt)
    target_answers = ", ".join(answers_list) if answers_list else ""

    facts = _extract_facts_gemini(question, target_answers, api_key)
    context_facts = "\n".join(facts) if facts else question

    hint_prompt = f'''
You are a Trivia Game Master. Guide the player to the Target Answers "{target_answers}" using analogies, WITHOUT ever naming them.

### STRUCTURAL REQUIREMENTS (exact, non-negotiable):
- Hard: a detailed, intricate analogy weaving together multiple facts (long-form).
- Medium: a concise, mechanism-based summary.
- Easy: a single, vivid, highly descriptive clue.
- Domain-appropriate analogies: micro-level concepts (cells, atoms, molecules, chemical reactions) get cellular/molecular/subatomic metaphors; macro-level concepts (organisms, ecosystems, physics, math) get macro-system metaphors (ecosystems, machinery, computing, architecture). Never force micro metaphors onto macro concepts or vice versa.
- NO LEAKAGE: never use the words "{target_answers}" or their obvious roots in any tier.
- NO PLACEHOLDERS, NO MARKDOWN, NO CONVERSATIONAL FILLER.

### FACTS TO WEAVE IN (the answer may already appear as [REDACTED]):
{context_facts}

Return ONLY a raw JSON object: {{"hard": "...", "medium": "...", "easy": "..."}}
'''
    try:
        text = _call_gemini(hint_prompt, api_key, max_tokens=800, temperature=0.7)
        hints = HintModel(**json.loads(text))
    except (json.JSONDecodeError, ValidationError, GeminiAPIError, GeminiRateLimitError):
        # One repair attempt: lower temperature, blunter formatting instruction.
        # If this also fails, raise so the caller can fall back to another provider.
        text = _call_gemini(
            hint_prompt + "\n\nReturn ONLY strictly valid JSON. No trailing characters, no commentary.",
            api_key, max_tokens=800, temperature=0.2,
        )
        hints = HintModel(**json.loads(text))

    sanitized = {k: get_safe_hint(v, target_answers) for k, v in hints.model_dump().items()}
    return json.dumps(sanitized)


class EasyHintModel(BaseModel):
    easy: str


def regenerate_easy_hint_gemini(question: str, correct_answer: str, hard_hint: str, medium_hint: str, api_key: str) -> str:
    """
    Targeted single-call repair: regenerates ONLY the Easy tier, matching the
    tone/style of an existing (good) Hard/Medium pair, for samples where just
    the Easy hint broke (e.g. the "...the correct value." placeholder bug).
    One Gemini call instead of the full facts+hints chain, since the Hard/Medium
    already establish the facts and don't need to be touched.
    """
    prompt = f'''
You are a Trivia Game Master. Below is a question with an existing Hard and Medium hint that are already good. Write ONLY a matching Easy hint: a single, vivid, highly descriptive clue, simpler than the Medium hint, that never names the answer.

Question: {question}
Correct Answer: {correct_answer}
Existing Hard hint: {hard_hint}
Existing Medium hint: {medium_hint}

NO LEAKAGE: never use the word(s) "{correct_answer}" or their obvious roots.
NO PLACEHOLDERS, NO MARKDOWN, NO CONVERSATIONAL FILLER.

Return ONLY a raw JSON object: {{"easy": "..."}}
'''
    try:
        text = _call_gemini(prompt, api_key, max_tokens=300, temperature=0.7)
        result = EasyHintModel(**json.loads(text))
    except (json.JSONDecodeError, ValidationError, GeminiAPIError, GeminiRateLimitError):
        text = _call_gemini(
            prompt + "\n\nReturn ONLY strictly valid JSON. No trailing characters, no commentary.",
            api_key, max_tokens=300, temperature=0.2,
        )
        result = EasyHintModel(**json.loads(text))

    return get_safe_hint(result.easy, correct_answer)
