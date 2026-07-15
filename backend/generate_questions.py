"""
Question Pool Generator for Study Saga
Uses Groq (Llama 3) API to generate quiz questions for data.json syllabi.
Usage:
    set GROQ_API_KEY=your_key_here
    python generate_questions.py --syllabus biology --count 167
    python generate_questions.py --all  # generates to fill all syllabi to 200
"""

import json
import os
import sys
import time
import argparse
import requests
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
TARGET_COUNT = 200
BATCH_SIZE = 10  # questions per API call

# Topic pools for diversity
TOPICS = {
    "biology": [
        "cell biology", "genetics", "evolution", "ecology", "human anatomy",
        "plant biology", "microbiology", "biochemistry", "animal kingdom",
        "reproduction", "nervous system", "digestive system", "circulatory system",
        "respiratory system", "endocrine system", "immune system", "taxonomy",
        "photosynthesis", "cellular respiration", "DNA and RNA", "protein synthesis",
        "ecology and ecosystems", "food chains", "biodiversity", "adaptation"
    ],
    "math": [
        "algebra", "geometry", "statistics", "probability", "trigonometry",
        "number theory", "fractions and decimals", "percentages", "ratios",
        "linear equations", "quadratic equations", "exponents and logarithms",
        "sequences and series", "coordinate geometry", "area and volume",
        "integers and operations", "word problems", "inequalities",
        "functions", "graphs", "sets and Venn diagrams", "prime numbers",
        "factorial and combinations", "basic calculus", "measurement and units"
    ],
    "chemistry": [
        "periodic table", "chemical bonding", "chemical reactions", "acids and bases",
        "organic chemistry", "states of matter", "atomic structure", "stoichiometry",
        "electrochemistry", "thermochemistry", "solutions and mixtures",
        "oxidation and reduction", "chemical equilibrium", "gas laws",
        "nuclear chemistry", "polymers", "metals and nonmetals",
        "chemical nomenclature", "moles and molar mass", "chemical kinetics",
        "environmental chemistry", "laboratory techniques", "catalysts",
        "electrolytes", "hydrocarbons"
    ],
    "physics": [
        "mechanics", "electricity and magnetism", "optics", "thermodynamics",
        "waves and sound", "nuclear physics", "kinematics", "Newton's laws",
        "energy and work", "momentum", "gravity", "fluid mechanics",
        "electromagnetic spectrum", "circuits", "resistance and current",
        "reflection and refraction", "lenses and mirrors", "radioactivity",
        "quantum basics", "relativity basics", "pressure", "simple machines",
        "oscillations", "electrostatics", "power and efficiency"
    ]
}

VILLAIN_CORRECT_FEEDBACK = [
    "Curses! Your knowledge wounds me! EMOTIONAL DAMAGE!",
    "Argh! Correct! My misconceptions weaken!",
    "No! You see through my deception! EMOTIONAL DAMAGE!",
    "Impossible! Your wisdom strikes true!",
    "Gah! Knowledge is indeed power! My defenses crumble!",
    "You... you actually knew that?! EMOTIONAL DAMAGE to me!",
    "My ignorance shield shatters! Well played!",
]

VILLAIN_WRONG_FEEDBACK = [
    "Wrong! Your confusion fuels my power!",
    "Ha! Incorrect! I grow stronger from your mistake!",
    "Foolish! My misconception magic intensifies!",
    "Nope! Your error empowers me! Take EMOTIONAL DAMAGE!",
    "Wrong again! I cackle with dark delight!",
    "Incorrect! Your ignorance is my feast!",
    "Mistaken! I revel in your confusion!",
]


def get_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print("Set it with: set GROQ_API_KEY=your_key_here")
        sys.exit(1)
    return key


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved data.json ({DATA_PATH})")


def get_existing_questions(data, syllabus_name):
    """Get set of existing question texts for dedup."""
    for s in data.get("syllabus", []):
        if s.get("name", "").lower() == syllabus_name.lower():
            return set(q.get("text", "").lower().strip() for q in s.get("questions", []))
    return set()


def generate_batch(api_key, syllabus_name, topics, existing_texts, batch_num, batch_size=BATCH_SIZE):
    """Generate a batch of questions using Groq API."""
    # Pick random topics for this batch
    selected_topics = random.sample(topics, min(3, len(topics)))
    topics_str = ", ".join(selected_topics)

    # Mix of single and multiple choice
    single_count = int(batch_size * 0.8)
    multi_count = batch_size - single_count

    prompt = f"""Generate exactly {batch_size} unique quiz questions for a {syllabus_name} course.
Topics to cover: {topics_str}

Requirements:
- {single_count} questions should be "multiple_choice_single" (one correct answer)
- {multi_count} questions should be "multiple_choice_multiple" (2-3 correct answers)
- Each question must have 4-6 options
- Questions should be educational and suitable for high school / early university level
- Do NOT repeat any of these existing questions (check text carefully):
  [existing questions are tracked separately - just make fresh, unique questions]
- Each option needs:
  - "text": the option text
  - "isCorrect": true/false
  - "feedback": a short villain-style feedback (~10-15 words, the villain gloats when wrong, winces when right)

Return ONLY a valid JSON array of question objects. No markdown, no code fences, just raw JSON.
Example format:
[
  {{
    "type": "multiple_choice_single",
    "text": "What is the chemical symbol for gold?",
    "options": [
      {{"text": "Au", "isCorrect": true, "feedback": "Curses! Your knowledge strikes true!"}},
      {{"text": "Ag", "isCorrect": false, "feedback": "Wrong! Silver thinking! I grow stronger!"}},
      {{"text": "Fe", "isCorrect": false, "feedback": "Iron-ically wrong! My power surges!"}},
      {{"text": "Cu", "isCorrect": false, "feedback": "Copper confusion! I cackle with glee!"}}
    ]
  }}
]"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": f"You are a quiz question generator for {syllabus_name}. Return ONLY valid JSON arrays. No markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4000,
        "temperature": 0.8
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 429:
            # Rate limited - wait and retry
            retry_after = int(response.headers.get("retry-after", 30))
            print(f"  [RATE LIMIT] Waiting {retry_after}s...")
            time.sleep(retry_after)
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            print(f"  [ERROR] API returned {response.status_code}: {response.text[:200]}")
            return []

        content = response.json()["choices"][0]["message"]["content"].strip()

        # Clean up common JSON issues
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        questions = json.loads(content)
        if not isinstance(questions, list):
            print(f"  [ERROR] Expected list, got {type(questions)}")
            return []

        # Validate and deduplicate
        valid = []
        for q in questions:
            text = q.get("text", "").lower().strip()
            if not text or text in existing_texts:
                continue
            if not q.get("options") or len(q.get("options", [])) < 4:
                continue
            if q.get("type") not in ("multiple_choice_single", "multiple_choice_multiple"):
                q["type"] = "multiple_choice_single"
            # Ensure feedback exists on all options
            for opt in q.get("options", []):
                if not opt.get("feedback"):
                    if opt.get("isCorrect"):
                        opt["feedback"] = random.choice(VILLAIN_CORRECT_FEEDBACK)
                    else:
                        opt["feedback"] = random.choice(VILLAIN_WRONG_FEEDBACK)
            # Ensure at least one correct answer
            has_correct = any(opt.get("isCorrect") for opt in q.get("options", []))
            if not has_correct:
                continue
            valid.append(q)
            existing_texts.add(text)

        return valid

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed: {e}")
        return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


def expand_syllabus(api_key, data, syllabus_name, target=TARGET_COUNT):
    """Expand a single syllabus to target question count."""
    syllabus_entry = None
    for s in data.get("syllabus", []):
        if s.get("name", "").lower() == syllabus_name.lower():
            syllabus_entry = s
            break

    if not syllabus_entry:
        print(f"[ERROR] Syllabus '{syllabus_name}' not found in data.json")
        return 0

    current = len(syllabus_entry.get("questions", []))
    needed = target - current
    if needed <= 0:
        print(f"[OK] {syllabus_name} already has {current} questions (target: {target})")
        return 0

    print(f"\n{'='*60}")
    print(f"  Expanding {syllabus_name}: {current} -> {target} ({needed} needed)")
    print(f"{'='*60}")

    topics = TOPICS.get(syllabus_name.lower(), ["general knowledge"])
    existing = get_existing_questions(data, syllabus_name)
    generated_total = 0
    batch_num = 0
    max_retries = 5

    while generated_total < needed:
        batch_num += 1
        remaining = needed - generated_total
        batch_size = min(BATCH_SIZE, remaining)
        retry = 0

        print(f"\n  Batch {batch_num}: Generating {batch_size} questions ({generated_total}/{needed} done)...")

        while retry < max_retries:
            new_questions = generate_batch(api_key, syllabus_name, topics, existing, batch_num, batch_size)
            if new_questions:
                break
            retry += 1
            print(f"  Retry {retry}/{max_retries}...")
            time.sleep(2)

        if not new_questions:
            print(f"  [WARN] Failed to generate batch {batch_num} after {max_retries} retries. Continuing...")
            continue

        syllabus_entry["questions"].extend(new_questions)
        generated_total += len(new_questions)
        print(f"  [OK] +{len(new_questions)} questions (total: {current + generated_total})")

        # Rate limiting: pause between batches
        time.sleep(2)

    # Save after each syllabus
    save_data(data)
    final = len(syllabus_entry.get("questions", []))
    print(f"\n  [DONE] {syllabus_name}: {current} -> {final} questions")
    return generated_total


def main():
    parser = argparse.ArgumentParser(description="Generate quiz questions for Study Saga")
    parser.add_argument("--syllabus", type=str, help="Syllabus name (biology, math, chemistry, physics)")
    parser.add_argument("--count", type=int, default=TARGET_COUNT, help=f"Target question count (default: {TARGET_COUNT})")
    parser.add_argument("--all", action="store_true", help="Expand all syllabi to target count")
    args = parser.parse_args()

    api_key = get_api_key()
    data = load_data()

    if args.all:
        total = 0
        for syllabus_name in ["biology", "math", "chemistry", "physics"]:
            total += expand_syllabus(api_key, data, syllabus_name, args.count)
        print(f"\n{'='*60}")
        print(f"  DONE: Generated {total} total new questions across all syllabi")
        print(f"{'='*60}")
    elif args.syllabus:
        expand_syllabus(api_key, data, args.syllabus, args.count)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
