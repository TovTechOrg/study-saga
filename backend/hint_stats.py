import pathlib, re, json, sys

file_path = r'C:/Users/talia/Desktop/study-saga/backend/automated_samples.md'
text = pathlib.Path(file_path).read_text(encoding='utf-8')

# Split into samples by headings "### Sample #N"
samples = re.split(r'### Sample #\d+', text)[1:]

subjects = {'math': [], 'chemistry': []}

for block in samples:
    content = block.strip()
    # Heuristic to determine subject
    low = content.lower()
    if any(k in low for k in ['helium', 'carbon', 'sulfuric', 'oxidation', 'sublimation', 'metal', 'bond', 'reaction', 'acid', 'slope', 'element', 'phosphorus', 'chlorine']):
        subj = 'chemistry'
    else:
        subj = 'math'
    # Count hints of each difficulty
    hard = len(re.findall(r'- \*\*Hint \(Hard\)\*\*:', content))
    medium = len(re.findall(r'- \*\*Hint \(Medium\)\*\*:', content))
    easy = len(re.findall(r'- \*\*Hint \(Easy\)\*\*:', content))
    total_hints = hard + medium + easy
    # Assign score per hint type (hard=10, medium=7, easy=5)
    score = hard * 10 + medium * 7 + easy * 5
    subjects[subj].append({'hints': total_hints, 'score': score})

results = {}
for subj, items in subjects.items():
    total_samples = len(items)
    total_score = sum(i['score'] for i in items)
    avg_score = total_score / total_samples if total_samples else 0
    # Low‑score samples: average score per hint <= 7 (or if no hints, treat as low)
    low_count = sum(1 for i in items if (i['score'] / i['hints'] if i['hints'] else 0) <= 7)
    pass_rate = ((total_samples - low_count) / total_samples * 100) if total_samples else 0
    results[subj] = {
        'total_samples': total_samples,
        'average_score': round(avg_score, 2),
        'low_score_samples': low_count,
        'pass_rate_percent': round(pass_rate, 1)
    }

print(json.dumps(results, indent=2))
