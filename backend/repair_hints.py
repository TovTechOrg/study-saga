import re
import json
import time
import os
import sys

# Add backend to path to import rag_pipeline
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_pipeline import generate_hint_groq

def repair_hints():
    batch_file = "backend/batch_samples.md"
    env_file = "backend/.env"

    if not os.path.exists(batch_file):
        print(f"Error: {batch_file} not found.")
        return

    # Extract API Key
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key and os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break

    if not api_key:
        print("Error: GROQ_API_KEY not found in env or .env")
        return

    with open(batch_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split the file by "### Sample #" to parse samples safely
    parts = re.split(r'(### Sample #\d+)', content)
    header = parts[0]
    
    repaired_count = 0
    updated_parts = [header]

    # Process each sample
    for i in range(1, len(parts), 2):
        label = parts[i]
        sample_body = parts[i+1]

        # Extract fields
        q_match = re.search(r'- \*\*Question\*\*: "(.*?)"', sample_body)
        opts_match = re.search(r'- \*\*Options\*\*: (\[.*?\])', sample_body)
        
        # Check if hints are failed / placeholder
        has_error = ("N/A" in sample_body or 
                     "No hint available" in sample_body or 
                     "AI API error" in sample_body or 
                     "Connection failed" in sample_body or
                     "describes a functional characteristic" in sample_body or
                     "involves a specific process" in sample_body)

        if has_error and q_match and opts_match:
            q_text = q_match.group(1).strip()
            # Safely evaluate options string to a list
            try:
                options = eval(opts_match.group(1))
            except:
                options = []

            print(f"Repairing {label}: '{q_text[:50]}...'")

            # Call generator
            hints_raw = generate_hint_groq(q_text, options, api_key)
            try:
                hints = json.loads(hints_raw)
            except:
                hints = {"hard": hints_raw, "medium": "N/A", "easy": "N/A"}

            hard = hints.get("hard", "N/A")
            medium = hints.get("medium", "N/A")
            easy = hints.get("easy", "N/A")

            # Replace hints in body
            sample_body = re.sub(r'- \*\*Hint \(Hard\)\*\*: ".*?"', rf'- \*\*Hint (Hard)\*\*: "{hard}"', sample_body)
            sample_body = re.sub(r'- \*\*Hint \(Medium\)\*\*: ".*?"', rf'- \*\*Hint (Medium)\*\*: "{medium}"', sample_body)
            sample_body = re.sub(r'- \*\*Hint \(Easy\)\*\*: ".*?"', rf'- \*\*Hint (Easy)\*\*: "{easy}"', sample_body)

            repaired_count += 1
            # Respect rate limits on Groq
            time.sleep(3)
        
        updated_parts.append(label)
        updated_parts.append(sample_body)

    # Write back to file
    new_content = "".join(updated_parts)
    with open(batch_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nSuccessfully repaired {repaired_count} failed samples in {batch_file}!")

if __name__ == "__main__":
    repair_hints()
