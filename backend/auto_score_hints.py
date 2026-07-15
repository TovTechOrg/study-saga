import re
import json
import requests
import os
import sys

# Ensure stdout can handle UTF-8 symbols
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import argparse

def auto_score_hints(input_file, api_key, rubric_version='classic'):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    # Find all sample numbers and contents dynamically using regex
    matches = list(re.finditer(r'### Sample #(\d+)(.*?)(?=### Sample #\d+|$)', content, re.DOTALL))
    
    if not matches:
        print("No samples found in the input file.")
        return

    # Load existing audit report if present to implement incremental grading
    output_path = input_file.replace(".md", "_automated_audit.md")
    existing_scores = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            # Match existing samples and their critiques
            existing_matches = re.finditer(
                r'### Sample #(\d+)\r?\n- \*\*Score\*\*: (\d+) / 10(?: \(Audit Failed\))?\r?\n- \*\*Critique\*\*: (.*?)(?=\r?\n\r?\n### Sample #|\Z)',
                existing_content,
                re.DOTALL
            )
            for em in existing_matches:
                s_num = int(em.group(1))
                score = int(em.group(2))
                critique = em.group(3).strip()
                # Skip if it was an API failure
                if "API failure during evaluation" not in critique and "Audit Failed" not in critique:
                    existing_scores[s_num] = (score, critique)
        except Exception as e:
            print(f"Warning: Could not parse existing audit report: {e}")

    report_content = ""
    total_score = 0
    sample_count = 0

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # N=8 Calibrated Few-Shot Examples for Prompt Injection (full set for maximum grading accuracy)
    few_shot_examples = """
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
- **Hint (Hard)**: "These organisms represent the most ancient blueprints of life—single-celled architects that predate the invention of the nucleus, operating with streamlined molecular machinery."
- **Hint (Medium)**: "These life forms lack a membrane-bound nucleus and complex organelles, thriving in every environment from deep-sea vents to Antarctic ice."
- **Hint (Easy)**: "Think of the two domains of life that do not have a nucleus and are the simplest living things on Earth."
Response:
{"score": 10, "critique": "Perfect multi-answer hint set. The hard hint is a creative analogy ('blueprints of life'), the medium introduces the defining characteristic (no nucleus) without naming the answer, and the easy hint progressively guides without leakage."}

Example 3 (Score: 10)
Sample:
- **Question**: "Which part of a neuron sends signals away from the cell body?"
- **Options**: ['Axon', 'Dendrite', 'Synapse', 'Myelin sheath']
- **Correct Answer**: Axon
- **Hint (Hard)**: "Picture a river flowing from a mountain spring outwards to the sea—this neural structure is the outbound channel that carries the electrical message away from the command centre."
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
{"score": 5, "critique": "Functional but extremely dry. The hard hint practically gives away the function directly without an analogy, and the easy hint relies heavily on a common association (diabetics) which is a functional spoiler."}

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
- **Hint (Hard)**: "Consider the class of macromolecules that are the master craftsmen of biochemistry—folded chains of amino acids that act as biological catalysts, accelerating chemical reactions without being consumed."
- **Hint (Medium)**: "These chain-like molecules made from amino acids are responsible for speeding up reactions in the cell and include all enzymes."
- **Hint (Easy)**: "Enzymes are made from this class of large molecules built from amino acids."
Response:
{"score": 8, "critique": "Good analogy in the hard tier ('master craftsmen of biochemistry'). The medium and easy tiers are clear and progressive. Minor deduction because 'amino acids' appears in all three tiers, reducing the tiered discovery experience slightly."}

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

    for match in matches:
        sample_num = int(match.group(1))
        sample_text = match.group(2).strip()
        
        # Check if already successfully graded
        if sample_num in existing_scores:
            score, critique = existing_scores[sample_num]
            total_score += score
            sample_count += 1
            report_content += f"### Sample #{sample_num}\n"
            report_content += f"- **Score**: {score} / 10\n"
            report_content += f"- **Critique**: {critique}\n\n"
            # print(f"Loaded Sample #{sample_num} from cache: {score}/10")
            continue

        prompt = f'''
You are a Pedagogical Auditor. Rate the following hint set based on the Rubric.
Return ONLY a JSON object: {{"score": #, "critique": "..."}}

RUBRIC:
- 10: Perfect analogy, zero leakage, tiered depth.
- 5: Functional but dry or near leakage.
- 1: Dead giveaway or "No hint available" error.

{few_shot_examples}

### TARGET SAMPLE TO GRADE:
{sample_text}

JSON Response:
'''
        data = {
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        # Groq API Call with retry
        max_retries = 5
        success = False
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=20
                )
                if response.status_code == 200:
                    result = response.json()["choices"][0]["message"]["content"]
                    eval_data = json.loads(result)
                    
                    score = eval_data.get("score", 0)
                    critique = eval_data.get("critique", "No critique provided.")
                    
                    total_score += score
                    sample_count += 1
                    
                    report_content += f"### Sample #{sample_num}\n"
                    report_content += f"- **Score**: {score} / 10\n"
                    report_content += f"- **Critique**: {critique}\n\n"
                    print(f"Scored Sample #{sample_num}: {score}/10")
                    success = True
                    break
                elif response.status_code == 429: # Rate limit
                    error_msg = ""
                    try:
                        error_msg = response.json().get("error", {}).get("message", "")
                    except Exception:
                        pass
                    
                    if "tokens per day" in error_msg.lower() or "tpd" in error_msg.lower():
                        current_model = data.get("model", "")
                        if current_model == "llama-3.3-70b-versatile":
                            print(f"[TPD Rate Limit] Daily limit reached for {current_model}. Falling back to llama-3.1-8b-instant...")
                            data["model"] = "llama-3.1-8b-instant"
                            continue
                    
                    import time
                    wait_sec = 60 if attempt == 0 else 90
                    print(f"[429 Rate Limit] Sleeping for {wait_sec} seconds to reset sliding window. Error: {error_msg}")
                    time.sleep(wait_sec)
                else:
                    print(f"[API Error] Status {response.status_code}: {response.text}")
                    import time
                    time.sleep(2)
            except Exception as e:
                print(f"[Exception] {e}")
                import time
                time.sleep(2)

        if not success:
            print(f"Failed to score sample {sample_num} after {max_retries} attempts.")
            # Fallback entry in report
            report_content += f"### Sample #{sample_num}\n"
            report_content += f"- **Score**: 1 / 10 (Audit Failed)\n"
            report_content += f"- **Critique**: API failure during evaluation.\n\n"
            total_score += 1
            sample_count += 1

        # Sleep between API calls to prevent rate limits
        import time
        time.sleep(5)

    if sample_count > 0:
        avg = total_score / sample_count
        report_content = f"# Automated Hint Audit Report\n**Average Score**: {avg:.2f} / 10\n\n" + report_content

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"Audit complete. Report saved to {output_path}")

if __name__ == "__main__":
    # Get API KEY from env or dotenv
    api_key = os.environ.get("GROQ_API_KEY", "") 
    if not api_key:
        # Fallback reading .env manually
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('GROQ_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break

    if len(sys.argv) > 1:
        auto_score_hints(sys.argv[1], api_key)
    else:
        print("Usage: python auto_score_hints.py <filename>")
