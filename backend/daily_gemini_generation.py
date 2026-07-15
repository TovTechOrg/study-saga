#!/usr/bin/env python3
"""
Single daily entry point for Gemini-quota-gated work. Intended to run once/day
via a scheduler, after the free-tier daily quota (20 requests/day on
gemini-3.5-flash) has reset.

Order of priority for today's ~20-request budget:
  1. Geography Easy-hint repair (small, ~8 samples total, finishes in one day)
  2. Core-subject (Physics/Chemistry) missing hints (176 questions, ~3 weeks)

Both sub-steps already stop cleanly on quota exhaustion and are safe to
re-run any time -- they always re-scan for remaining work rather than
tracking a fixed job list.
"""
import repair_geography_easy_hints
import generate_missing_core_hints

if __name__ == "__main__":
    repair_geography_easy_hints.main()
    generate_missing_core_hints.main()
