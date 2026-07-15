# KB Authoring Checklist for Robust Hints

For every quiz question, ensure the KB entry includes at least one of the following:

1. **Contrast Fact (Best)**
   - Explains how the correct answer differs from incorrect options.
   - Example: "Animals are multicellular eukaryotes that ingest food; plants photosynthesize and fungi absorb nutrients."

2. **Defining Characteristic (Fallback)**
   - A property that applies to the correct answer without naming it directly.
   - Example: "Prokaryotes lack a nucleus and membrane-bound organelles."

3. **Exclusion Rule (Gold for Multi-Select)**
   - States what does NOT qualify.
   - Example: "Viruses are acellular and not classified as prokaryotes."

**Invariant:**
No question enters the system unless its KB can support a conceptual hint that does not reveal the answer.

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

# Python Linter: KB Hintability Checker

This script checks kb_external.json for each question and flags any entry that lacks a 'hint' field or has an empty/weak hint.

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

This test ensures every question generates a non-empty hint.

```
def test_all_questions_have_hints():
    import json
    kb = json.load(open('backend/kb_external.json', encoding='utf-8'))
    for entry in kb:
        hint = entry.get('hint', '').strip()
        assert hint, f"No hint for question: {entry.get('question', '')}"
```

---

# Pre-Generation Validator (Optional)

Before running the game, run the linter above. If any question is flagged, add a contrast, definition, or exclusion fact to its KB entry before deployment.

---

# Summary
- Every question must have a robust, non-leaky hint in the KB.
- The backend and prompt must always allow a fallback conceptual reminder.
- Use the linter and unit test to enforce this invariant before every release.
