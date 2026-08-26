"""Checks that every relative link and in-page anchor in README.md (and
files it links to) resolves. External http(s) links are skipped -- checking
those in CI is flaky and slow, and the README currently has none anyway.

Usage: python check-readme-links.py
"""
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def slugify(heading):
    slug = heading.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def check_file(path, errors):
    text = path.read_text(encoding="utf-8")
    anchors = {slugify(h) for h in HEADING_RE.findall(text)}

    for link in LINK_RE.findall(text):
        if link.startswith(("http://", "https://", "mailto:")):
            continue
        if link.startswith("#"):
            if link[1:] not in anchors:
                errors.append(f"{path}: broken anchor link {link!r}")
            continue
        target = (path.parent / link).resolve()
        if not target.exists():
            errors.append(f"{path}: broken relative link {link!r} -> {target}")


def main():
    errors = []
    for name in ["README.md", "backend/README.md"]:
        path = Path(name)
        if path.exists():
            check_file(path, errors)

    if errors:
        print(f"README link check FAILED: {len(errors)} problem(s)", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("README link check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
