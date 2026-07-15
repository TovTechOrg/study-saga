import pathlib, re, json

file_path = r'C:/Users/talia/Desktop/study-saga/backend/automated_samples.md'
text = pathlib.Path(file_path).read_text(encoding='utf-8')

# Split samples by heading
samples = re.split(r'### Sample #\d+', text)[1:]

subject_stats = {}

for block in samples:
    content = block.strip()
    # Extract syllabus line, e.g., "**Syllabus**: physics"
    m = re.search(r'\*\*Syllabus\*\*:\s*(\w+)', content, re.IGNORECASE)
    if m:
        subj = m.group(1).lower()
    else:
        # fallback heuristic if missing
        low = content.lower()
        if any(k in low for k in ['helium', 'carbon', 'sulfuric', 'oxidation', 'sublimation', 'metal', 'bond', 'reaction', 'acid', 'slope', 'element', 'phosphorus', 'chlorine']):
            subj = 'chemistry'
        else:
            subj = 'math'
    # Count hints
    hard = len(re.findall(r'- \*\*Hint \(Hard\)\*\*:', content))
    medium = len(re.findall(r'- \*\*Hint \(Medium\)\*\*:', content))
    easy = len(re.findall(r'- \*\*Hint \(Easy\)\*\*:', content))
    total_hints = hard + medium + easy
    score = hard * 10 + medium * 7 + easy * 5
    if subj not in subject_stats:
        subject_stats[subj] = {'samples': 0, 'total_score': 0, 'low': 0}
    subject_stats[subj]['samples'] += 1
    subject_stats[subj]['total_score'] += score
    # low score if avg per hint <=7 or no hints
    avg_per_hint = (score / total_hints) if total_hints else 0
    if avg_per_hint <= 7:
        subject_stats[subj]['low'] += 1

# Build results
results = {}
for subj, data in subject_stats.items():
    total = data['samples']
    avg_score = data['total_score'] / total if total else 0
    low = data['low']
    pass_rate = (total - low) / total * 100 if total else 0
    results[subj] = {
        'total_samples': total,
        'average_score': round(avg_score, 2),
        'low_score_samples': low,
        'pass_rate_percent': round(pass_rate, 1)
    }

print(json.dumps(results, indent=2))
