import json
import re

# Paths to your files
DATA_PATH = 'backend/data.json'
KB_PATH = 'backend/kb_external.json'

# Load quiz questions
def load_questions():
    with open(DATA_PATH, encoding='utf-8') as f:
        data = json.load(f)
    questions = []
    # Support nested syllabus structure
    if isinstance(data, dict) and 'syllabus' in data:
        for subject in data['syllabus']:
            for q in subject.get('questions', []):
                # Use 'text' field for question
                if 'text' in q:
                    questions.append(q['text'])
    elif isinstance(data, dict) and 'questions' in data:
        questions = [q['question'] for q in data['questions']]
    elif isinstance(data, list):
        questions = [q['question'] for q in data]
    else:
        raise ValueError('Unrecognized data.json format')
    return questions

# Load KB entries
def load_kb():
    with open(KB_PATH, encoding='utf-8') as f:
        kb = json.load(f)
    # Support both list and dict formats
    if isinstance(kb, list):
        return {entry['question']: entry for entry in kb}
    elif isinstance(kb, dict):
        return {entry['question']: entry for entry in kb.get('entries', [])}
    else:
        raise ValueError('Unrecognized kb_external.json format')

# Check for generic/fallback hints
def is_generic_hint(hint, question, answers=None):
    generic_patterns = [
        r'think about',
        r'relates to the options',
        r'always output a hint',
        r'conceptual reminder',
        r'focus on the question',
        r'if unsure',
    ]
    if not hint or len(hint.strip()) < 15:
        return True
    for pat in generic_patterns:
        if re.search(pat, hint, re.IGNORECASE):
            return True
    if answers:
        for ans in answers:
            if ans.lower() in hint.lower():
                return True
    if question.lower() in hint.lower():
        return True
    return False

def main():
    questions = load_questions()
    kb = load_kb()
    failed = []
    flagged = []
    for q in questions:
        entry = kb.get(q)
        if not entry or not entry.get('hint'):
            failed.append(q)
        else:
            # Optionally, check for generic/fallback hints
            if is_generic_hint(entry['hint'], q):
                flagged.append((q, entry['hint']))
    print(f"\n=== KB Completeness Check ===")
    if failed:
        print(f"Missing or empty hint for {len(failed)} questions:")
        for q in failed:
            print(f"- {q}")
    else:
        print("All quiz questions have a KB entry with a non-empty hint.")
    print(f"\n=== Hint Quality Linter ===")
    if flagged:
        print(f"{len(flagged)} hints flagged as too generic or problematic:")
        for q, hint in flagged:
            print(f"- {q}\n  Hint: {hint}\n")
    else:
        print("No generic or problematic hints detected.")

if __name__ == '__main__':
    main()
