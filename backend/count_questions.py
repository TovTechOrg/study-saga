import json

with open('backend/data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data.get('syllabus', []):
    name = s.get('name', 'Unknown')
    questions = s.get('questions', [])
    print(f"{name}: {len(questions)} questions")
