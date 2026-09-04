"""One-time reconciliation for issue #24: cf-pages/functions/_lib/data.json
becomes the authoritative corpus. Before backend/data.json is retired to a
generated mirror, pull forward the one real improvement it has that
cf-pages' copy lacks -- better-written hints for 10 of the original 800
questions (backend's _gemini_regen_v1 pass). Everything else backend/data.json
has that differs (difficulty/id/difficulty_source tags defaulting ~779/800
questions to "easy") is a known-inadequate classification pass per
generate_tiered_questions.py's own docstring ("classification found ZERO
Hard-tier questions anywhere in the existing 800") -- not imported.

After this runs, cf-pages/functions/_lib/data.json is copied over
backend/data.json so the two are identical again.
"""
import json
import shutil

CF_PAGES_PATH = "../cf-pages/functions/_lib/data.json"
BACKEND_PATH = "data.json"


def index_by_text(data):
    idx = {}
    for s in data["syllabus"]:
        for q in s["questions"]:
            idx[(s["name"], q["text"])] = q
    return idx


def main():
    with open(BACKEND_PATH, encoding="utf-8") as f:
        backend = json.load(f)
    with open(CF_PAGES_PATH, encoding="utf-8") as f:
        cf_pages = json.load(f)

    backend_idx = index_by_text(backend)
    cf_idx = index_by_text(cf_pages)
    common = set(backend_idx.keys()) & set(cf_idx.keys())

    updated = []
    for key in common:
        b_hints = backend_idx[key].get("hints")
        c_hints = cf_idx[key].get("hints")
        if b_hints != c_hints:
            cf_idx[key]["hints"] = b_hints
            updated.append(key)

    print(f"Merged hints for {len(updated)} questions:")
    for realm, text in updated:
        print(f"  - {realm}: {text[:70]}")

    with open(CF_PAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(cf_pages, f, indent=2, ensure_ascii=False)
        f.write("\n")

    shutil.copyfile(CF_PAGES_PATH, BACKEND_PATH)
    print(f"\nCopied {CF_PAGES_PATH} -> {BACKEND_PATH} (now identical, cf-pages is master)")


if __name__ == "__main__":
    main()
