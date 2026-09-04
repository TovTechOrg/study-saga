"""Regenerates backend/data.json (a local dev mirror) from
cf-pages/functions/_lib/data.json -- the authoritative corpus as of issue
#24's resolution. cf-pages' copy is master because it's what's actually
live (3,152 questions across the merged tiered content) and because it
already carries fixes that never made it back into backend/data.json before
this; backend/data.json is not edited directly going forward.

Run this after any edit to the live corpus. CI (.github/workflows/ci.yml)
runs it and fails if backend/data.json doesn't match a fresh regeneration --
that's what makes drift impossible to commit unnoticed.
"""
import json
import sys

MASTER_PATH = "../cf-pages/functions/_lib/data.json"
MIRROR_PATH = "data.json"


def main():
    with open(MASTER_PATH, encoding="utf-8") as f:
        master = json.load(f)
    with open(MIRROR_PATH, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Regenerated {MIRROR_PATH} from {MASTER_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
