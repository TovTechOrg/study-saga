import json
import os

kb_path = r'c:\Users\talia\Desktop\study-saga\backend\kb_external.json'

with open(kb_path, 'r', encoding='utf-8') as f:
    kb = json.load(f)

unique_kb = {}
# By iterating and updating, we keep the LAST occurrence (which has the fixes)
for entry in kb:
    unique_kb[entry['question']] = entry

final_kb = list(unique_kb.values())

with open(kb_path, 'w', encoding='utf-8') as f:
    json.dump(final_kb, f, indent=4)

print(f"Deduplicated KB. Redundant entries removed. Total size: {len(final_kb)}")
