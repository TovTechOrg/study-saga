#!/usr/bin/env python3
"""
Targeted, resumable repair for the ~8 Geography samples in expanded_samples.md
whose Easy hint broke to the literal "...the correct value." placeholder
(everything else in those samples -- Hard, Medium -- is already good).

Only regenerates the broken Easy tier (one Gemini call per sample via
regenerate_easy_hint_gemini), and rewrites expanded_samples.md in place after
EVERY successful fix so progress is never lost mid-run. Safe to re-run: it
always re-scans for remaining "the correct value" hits.
"""
import os
import re
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_pipeline import regenerate_easy_hint_gemini, GeminiRateLimitError, GeminiAPIError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_PATH = os.path.join(BASE_DIR, "expanded_samples.md")
LOG_PATH = os.path.join(BASE_DIR, "gemini_daily_generation.log")

TARGET_SYLLABUS = "geography"
BAD_MARKER = "the correct value"


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [geo-repair] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_quota_exhausted(exc) -> bool:
    """True only for a genuine daily-cap hit, not a transient per-minute 429
    (tenacity's internal retries + rag_pipeline's proactive pacing already
    absorb those before they ever reach this outer catch)."""
    msg = str(exc).lower()
    return "perday" in msg or "per_day" in msg


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log("ERROR: GEMINI_API_KEY not set. Aborting.")
        return

    with open(SAMPLES_PATH, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Locate the geography section specifically (don't touch other domains' samples).
    sections = list(re.finditer(r'\*\*Syllabus\*\*: (\w+)', content))
    geo_start = geo_end = None
    for i, m in enumerate(sections):
        if m.group(1) == TARGET_SYLLABUS:
            geo_start = m.end()
            geo_end = sections[i + 1].start() if i + 1 < len(sections) else len(content)
            break
    if geo_start is None:
        log("Could not find a geography section. Aborting.")
        return

    geo_section = content[geo_start:geo_end]

    sample_re = re.compile(
        r'(### Sample #(\d+)\n'
        r'- \*\*Question\*\*: "(?P<question>.*?)"\n'
        r'- \*\*Correct Answer\*\*: (?P<answer>.*?)\n'
        r'- \*\*Hint \(Hard\)\*\*: "(?P<hard>.*?)"\n'
        r'- \*\*Hint \(Medium\)\*\*: "(?P<medium>.*?)"\n'
        r'- \*\*Hint \(Easy\)\*\*: "(?P<easy>.*?)")\n',
        re.DOTALL,
    )

    fixed = 0
    for m in sample_re.finditer(geo_section):
        if BAD_MARKER not in m.group("easy").lower():
            continue
        sample_num = m.group(2)
        question = m.group("question").strip()
        answer = m.group("answer").strip()
        hard = m.group("hard").strip()
        medium = m.group("medium").strip()

        try:
            new_easy = regenerate_easy_hint_gemini(question, answer, hard, medium, api_key)
        except (GeminiRateLimitError, GeminiAPIError) as e:
            if is_quota_exhausted(e):
                log(f"Quota exhausted after fixing {fixed} sample(s) this run. Stopping cleanly; resume tomorrow.")
                break
            log(f"API error (non-quota) on sample #{sample_num}: {e}")
            continue
        except Exception as e:
            log(f"FAILED on sample #{sample_num} ({question[:50]}): {e}")
            continue

        old_easy_line = f'- **Hint (Easy)**: "{m.group("easy")}"'
        new_easy_line = f'- **Hint (Easy)**: "{new_easy}"'
        # Re-read + re-write the full file each time so we always patch the
        # freshest on-disk content (in case of concurrent edits) and never
        # lose progress if interrupted mid-run.
        with open(SAMPLES_PATH, "r", encoding="utf-8", errors="ignore") as f:
            current_content = f.read()
        if old_easy_line not in current_content:
            log(f"WARNING: could not locate original Easy line for sample #{sample_num}; skipping write.")
            continue
        current_content = current_content.replace(old_easy_line, new_easy_line, 1)
        with open(SAMPLES_PATH, "w", encoding="utf-8") as f:
            f.write(current_content)

        fixed += 1
        log(f"Fixed geography sample #{sample_num} ({question[:50]}): {new_easy[:70]}")

    log(f"Run complete. Fixed {fixed} geography Easy hints this run.")


if __name__ == "__main__":
    main()
