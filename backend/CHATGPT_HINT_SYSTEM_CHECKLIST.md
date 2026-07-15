# Step-by-Step Diagnostic Checklist for Missing Hints

## Step 1: Confirm the question text matches KB exactly
- Copy the exact question string from kb_external.json.
- Compare it character by character with your quiz/backend input.
- Fix any mismatch (capitalization, whitespace, punctuation).

## Step 2: Validate kb_external.json syntax
- Run kb_external.json through a JSON validator (e.g., https://jsonlint.com/).
- Fix any missing commas, extra commas, improper quotes, or duplicate entries.

## Step 3: Confirm each entry has a single “hint” field
- Ensure every question object in kb_external.json has exactly one "hint" field.

## Step 4: Ensure the backend loads the latest KB
- Restart Flask after editing kb_external.json.
- (Optional) Add a debug print to confirm KB is loaded: print(f"Loaded {len(kb_data)} KB entries")

## Step 5: Confirm fallback logic works
- Ensure the backend always checks the KB "hint" field first.
- LLM fallback is only used if KB is missing.
- Add logging: print(f"Fetching hint for: {question_text}")

## Step 6: Test a “problem” question manually
- In Python shell or Flask debug console, run: print(get_hint("Exact question text here"))
- If "No hint available" appears, repeat Steps 1–3.

## Step 7: Optional – add KB completeness check
- Run a script to detect missing hint fields or questions in the quiz not present in kb_external.json.

---

# Python Linter: KB Hintability Checker

```
import json

KB_PATH = 'backend/kb_external.json'

with open(KB_PATH, 'r', encoding='utf-8') as f:
    kb = json.load(f)

problems = []
for entry in kb:
    q = entry.get('question', '').strip()
    hint = entry.get('hint', '').strip()
    if not hint or len(hint) < 10:
        problems.append(q)

if problems:
    print('Questions with missing or weak hints:')
    for q in problems:
        print('-', q)
else:
    print('All questions have robust hints!')
```

---

# Unit Test Template: Hint Generation

```
def test_all_questions_have_hints():
    import json
    kb = json.load(open('backend/kb_external.json', encoding='utf-8'))
    for entry in kb:
        hint = entry.get('hint', '').strip()
        assert hint, f"No hint for question: {entry.get('question', '')}"
```

---

# Copilot-Safe Prompt Template

Generate a single educational hint for a multiple-choice science question.

Rules:
- Do not directly state the correct answer.
- Use only the provided knowledge base facts.
- Keep the hint to 1–2 sentences.
- The hint should help narrow down the correct choice(s) by focusing on defining or contrasting characteristics.

If a distinguishing hint cannot be generated, provide a relevant conceptual reminder related to the question.

Always output at least one sentence.

Question:
{question}

Answer choices:
{choices}

Correct answer(s):
{correct}

Knowledge base facts:
{kb_facts}

---

# KB Authoring Checklist

For every quiz question, ensure the KB entry includes at least one of the following:
- Contrast fact (how correct ≠ incorrect options)
- Defining characteristic (applies to the correct answer, but not so specific it gives it away)
- Exclusion rule (what does NOT qualify, especially for multi-select)

No question enters the system unless its KB can support a conceptual hint that does not reveal the answer.

---

# Debug Logging Example (for backend)

Add to your backend hint retrieval function:

```
def get_hint(question_text):
    print(f"Fetching hint for: '{question_text}'")
    # ...existing code...
```

This will help you instantly spot mismatches or missing KB entries.
