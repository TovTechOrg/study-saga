import json, glob
per = {}
mine = 0
bad = []
for f in glob.glob("claude_tiered_batch*_*.json"):
    if any(s in f for s in ["geography","history","literature","computer_science"]):
        continue
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        bad.append((f,str(e))); continue
    subj = f.split("_")[-1].replace(".json","")
    per[subj] = per.get(subj,0)+len(d)
    mine += len(d)
print(per, "total", mine)
print("bad:", bad)
