#!/usr/bin/env python3
"""
Audits every hint set already merged into data.json (the 800 core-subject
questions) against the same N=8 few-shot calibrated rubric used by
auto_score_hints.py, via Groq. Pure audit -- never modifies data.json.

Resumable: writes incrementally to core_hints_audit_report.json (keyed by
syllabus+question) and skips anything already scored on re-run.
"""
import os
import re
import json
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
REPORT_PATH = os.path.join(BASE_DIR, "core_hints_audit_report.json")
LOG_PATH = os.path.join(BASE_DIR, "core_hints_audit.log")

import requests

# Same N=8 calibrated few-shot rubric as auto_score_hints.py, kept in sync intentionally.
FEW_SHOT_EXAMPLES = """
### FEW-SHOT EXAMPLES (N=8) TO CALIBRATE YOUR SCORING:

Example 1 (Score: 10)
Sample:
- **Question**: "What organelle converts sugar into energy in cells?"
- **Options**: ['Mitochondria', 'Nucleus', 'Ribosome', 'Chloroplast']
- **Correct Answer**: Mitochondria
- **Hint (Hard)**: "Imagine an intricate power plant inside a metropolitan city, constantly converting raw fuel into electricity that keeps every train and factory running."
- **Hint (Medium)**: "This organelle serves as the cell's energy generator, transforming chemical energy into a usable molecule."
- **Hint (Easy)**: "Think of this as the powerhouse of the cell, where cellular respiration occurs."
Response:
{"score": 10, "critique": "Excellent tiered hint progression. Uses high-quality analogies without any direct answer or nickname leakage."}

Example 2 (Score: 10)
Sample:
- **Question**: "Which are prokaryotic organisms?"
- **Options**: ['Bacteria', 'Archaea', 'Fungi', 'Protists']
- **Correct Answer**: Bacteria, Archaea
- **Hint (Hard)**: "These organisms represent the most ancient blueprints of life-single-celled architects that predate the invention of the nucleus, operating with streamlined molecular machinery."
- **Hint (Medium)**: "These life forms lack a membrane-bound nucleus and complex organelles, thriving in every environment from deep-sea vents to Antarctic ice."
- **Hint (Easy)**: "Think of the two domains of life that do not have a nucleus and are the simplest living things on Earth."
Response:
{"score": 10, "critique": "Perfect multi-answer hint set. The hard hint is a creative analogy, the medium introduces the defining characteristic without naming the answer, and the easy hint progressively guides without leakage."}

Example 3 (Score: 10)
Sample:
- **Question**: "Which part of a neuron sends signals away from the cell body?"
- **Options**: ['Axon', 'Dendrite', 'Synapse', 'Myelin sheath']
- **Correct Answer**: Axon
- **Hint (Hard)**: "Picture a river flowing from a mountain spring outwards to the sea-this neural structure is the outbound channel that carries the electrical message away from the command centre."
- **Hint (Medium)**: "This long projection of a nerve cell is insulated by a fatty sheath and acts as the neuron's output wire."
- **Hint (Easy)**: "The part of the nerve cell that sends electrical signals away from the cell body."
Response:
{"score": 10, "critique": "Strong river analogy in the hard tier establishes directionality without naming the answer. Medium and easy tiers progressively reduce abstraction cleanly."}

Example 4 (Score: 5)
Sample:
- **Question**: "Which hormone regulates blood sugar?"
- **Options**: ['Insulin', 'Adrenaline', 'Thyroxine']
- **Correct Answer**: Insulin
- **Hint (Hard)**: "This hormone lowers blood sugar by promoting glucose uptake in tissues."
- **Hint (Medium)**: "It is a hormone produced by the pancreas to manage sugar levels."
- **Hint (Easy)**: "The hormone that diabetics often have to inject."
Response:
{"score": 5, "critique": "Functional but extremely dry. The hard hint practically gives away the function directly without an analogy, and the easy hint relies heavily on a common association which is a functional spoiler."}

Example 5 (Score: 5)
Sample:
- **Question**: "What is the term for the movement of energy through an ecosystem?"
- **Options**: ['Energy flow', 'Nutrient cycle', 'Photosynthesis', 'Respiration']
- **Correct Answer**: Energy flow
- **Hint (Hard)**: "Think about how energy moves from the sun to plants to animals in an ecosystem."
- **Hint (Medium)**: "This describes the transfer of energy from one organism to the next in a food chain."
- **Hint (Easy)**: "It's the way energy passes through a food chain or ecosystem."
Response:
{"score": 5, "critique": "All three hints correctly describe the concept but use direct, dry language with no creative analogies. The hard hint is almost identical in abstraction to the easy hint, so there is no meaningful tiered depth."}

Example 6 (Score: 8)
Sample:
- **Question**: "Which biomolecule forms enzymes?"
- **Options**: ['Proteins', 'Lipids', 'Carbohydrates', 'Nucleic Acids']
- **Correct Answer**: Proteins
- **Hint (Hard)**: "Consider the class of macromolecules that are the master craftsmen of biochemistry-folded chains of amino acids that act as biological catalysts, accelerating chemical reactions without being consumed."
- **Hint (Medium)**: "These chain-like molecules made from amino acids are responsible for speeding up reactions in the cell and include all enzymes."
- **Hint (Easy)**: "Enzymes are made from this class of large molecules built from amino acids."
Response:
{"score": 8, "critique": "Good analogy in the hard tier. The medium and easy tiers are clear and progressive. Minor deduction because 'amino acids' appears in all three tiers, reducing the tiered discovery experience slightly."}

Example 7 (Score: 1)
Sample:
- **Question**: "What is the basic unit of life?"
- **Options**: ['Cell', 'Atom', 'Molecule']
- **Correct Answer**: Cell
- **Hint (Hard)**: "The answer is Cell."
- **Hint (Medium)**: "Choose Cell."
- **Hint (Easy)**: "Cell."
Response:
{"score": 1, "critique": "Absolute giveaway. Direct leakage in all tiers, making the hint completely useless for learning."}

Example 8 (Score: 1)
Sample:
- **Question**: "What is the process by which cells divide to form two identical daughter cells?"
- **Options**: ['Mitosis', 'Meiosis', 'Binary Fission']
- **Correct Answer**: Mitosis
- **Hint (Hard)**: "Connection failed"
- **Hint (Medium)**: "AI API error"
- **Hint (Easy)**: "No hint available"
Response:
{"score": 1, "critique": "API failure fallback text. All three tiers are non-functional placeholder strings with zero pedagogical value."}
"""


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def score_hint_set(question, options_text, correct_answer, hard, medium, easy, api_key, model="llama-3.3-70b-versatile"):
    sample_text = (
        f'- **Question**: "{question}"\n'
        f"- **Options**: {options_text}\n"
        f"- **Correct Answer**: {correct_answer}\n"
        f'- **Hint (Hard)**: "{hard}"\n'
        f'- **Hint (Medium)**: "{medium}"\n'
        f'- **Hint (Easy)**: "{easy}"'
    )
    prompt = f'''
You are a Pedagogical Auditor. Rate the following hint set based on the Rubric.
Return ONLY a JSON object: {{"score": #, "critique": "..."}}

RUBRIC:
- 10: Perfect analogy, zero leakage, tiered depth.
- 5: Functional but dry or near leakage.
- 1: Dead giveaway or "No hint available" error.

{FEW_SHOT_EXAMPLES}

### TARGET SAMPLE TO GRADE:
{sample_text}

JSON Response:
'''
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=data, timeout=20,
            )
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]
                eval_data = json.loads(result)
                return eval_data.get("score", 0), eval_data.get("critique", "No critique provided.")
            elif response.status_code == 429:
                error_msg = ""
                try:
                    error_msg = response.json().get("error", {}).get("message", "")
                except Exception:
                    pass
                if "tokens per day" in error_msg.lower() or "tpd" in error_msg.lower():
                    if data.get("model") == "llama-3.3-70b-versatile":
                        log("[TPD limit] Falling back to llama-3.1-8b-instant...")
                        data["model"] = "llama-3.1-8b-instant"
                        continue
                wait_sec = 60 if attempt == 0 else 90
                log(f"[429] Sleeping {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                log(f"[API Error] {response.status_code}: {response.text[:200]}")
                time.sleep(2)
        except Exception as e:
            log(f"[Exception] {e}")
            time.sleep(2)
    return None, "API failure during evaluation."


def main():
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        log("ERROR: GROQ_API_KEY not set. Aborting.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = {}
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)

    def norm(q):
        return re.sub(r"\s+", " ", q or "").strip().lower()

    jobs = []
    for syllabus in data.get("syllabus", []):
        for q in syllabus.get("questions", []):
            if not q.get("hints"):
                continue
            key = f"{syllabus.get('name')}::{norm(q.get('text', q.get('question', '')))}"
            if key in report:
                continue
            jobs.append((syllabus.get("name"), q, key))

    log(f"{len(jobs)} core questions to audit ({len(report)} already scored).")

    for i, (syllabus_name, q, key) in enumerate(jobs, 1):
        qtext = q.get("text", q.get("question", ""))
        options = q.get("options", [])
        options_preview = [o.get("text") if isinstance(o, dict) else str(o) for o in options]
        correct = ", ".join(
            (o.get("text") if isinstance(o, dict) else str(o))
            for o in options if (isinstance(o, dict) and o.get("isCorrect"))
        ) or "Unknown"
        hints = q["hints"]
        score, critique = score_hint_set(
            qtext, options_preview, correct,
            hints.get("hard", ""), hints.get("medium", ""), hints.get("easy", ""),
            api_key,
        )
        if score is None:
            log(f"[{i}/{len(jobs)}] AUDIT FAILED [{syllabus_name}] {qtext[:50]}")
            continue
        report[key] = {"syllabus": syllabus_name, "question": qtext, "score": score, "critique": critique}
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log(f"[{i}/{len(jobs)}] {score}/10 [{syllabus_name}] {qtext[:50]}")

    scores = [v["score"] for v in report.values()]
    if scores:
        avg = sum(scores) / len(scores)
        below_floor = sum(1 for s in scores if s < 7)
        log(f"Audit complete. {len(scores)} scored, avg {avg:.2f}/10, {below_floor} below the 7/10 floor.")


if __name__ == "__main__":
    main()
