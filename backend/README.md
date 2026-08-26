# backend/

This directory holds the original Flask app (superseded in production by
`cf-pages/`, see the root [README.md](../README.md)) plus a large pile of
one-off scripts accumulated across content-generation and QA sessions. This
file indexes that pile so it's navigable without opening every script.

Scripts are documented in place rather than moved into subfolders, since many
of them assume `backend/` as their working directory (relative paths to
`data.json`, `*.json` intermediate files, etc.) and physically relocating them
risked breaking those assumptions without a full audit of each one.

## Core app

- `app.py` — Flask entry point (dev-only; production is `cf-pages/`)
- `models.py`, `services.py` — app data models and service layer
- `rag_pipeline.py` — hint generation pipeline (LLM calls, prompt-chaining, few-shot)
- `rag_helper.py`, `adaptive.py` — supporting helpers for the pipeline above

## Content generation

Scripts that produce questions/hints from an LLM: `generate_questions.py`,
`generate_tiered_questions.py`, `generate_automated_set.py`,
`generate_diagnostic_dataset.py`, `generate_missing_core_hints.py`,
`generate_all_gemini_800.py`, `daily_gemini_generation.py`,
`batch_generate_samples.py`, `regenerate_all_hints_gemini.py`,
`regenerate_final_corpus_gemini.py`, `regenerate_full_corpus.py`,
`regenerate_low_scores.py`, `regenerate_placeholder_hints.py`,
`regenerate_severe_hints.py`, `repair_geography_easy_hints.py`,
`repair_hints.py`, `proper_repair.py`.

## Judging / QA / scoring

Scripts that grade generated content (Gemini/Gemma/GPT judges, self-grading,
comparisons between providers): `judge_tiered_content.py`,
`judge_tiered_content_gemma.py`, `judge_before_corpus.py`,
`judge_claude_math_hints.py`, `judge_claude_syllabi_hints.py`,
`hint_judge.py`, `hint_kb_validator.py`, `hint_stats.py`,
`full_hint_stats.py`, `benchmark_hints_25.py`, `auto_score_hints.py`,
`score_hints_openai.py`, `audit_core_hints.py`, `audit_gemini_800.py`,
`compare_groq_vs_gemini.py`, `compare_providers.py`,
`groq_vs_gemma_judge_headtohead.py`, `finish_groq_vs_gemini_judged.py`,
`gemma_qa_full_corpus.py`, `claude_universal_test.py`.

## Bake-offs (generator/model comparisons)

`bcp_full_bakeoff.py`, `bcp_generator_bakeoff.py`, `math_full_bakeoff.py`,
`math_generator_bakeoff.py`, `test_gemini_35_flash_lite.py`.

## Corpus maintenance / migration

`merge_hints_into_data.py`, `merge_tiered_into_live_data.py`,
`migrate_difficulty_into_data.py`, `classify_question_difficulty.py`,
`check_hard_predicts_all_tiers.py`, `stress_test_hard_predicts_tiers.py`,
`deduplicate_kb.py`, `semantic_dedup.py`, `fix_glued_artifacts.py`,
`update_kb.py`, `count_questions.py`.

## Extraction / diagnostics

`extract_benchmarks.py`, `extract_biology_diagnostics.py`,
`extract_physics_full.py`, `extract_physics_samples.py`,
`generate_diagnostic_dataset.py` (also listed above — spans both),
`check_kb_debug.py`, `check_progress.py`, `check_gemini_quota.py`,
`check_groq_quota.py`.

## Playwright verification scripts (throwaway, not deliverables)

Browser-automation checks written to verify a specific bug fix or feature
against a locally running `wrangler pages dev` instance. Kept for reference
on how to drive the game via Playwright, not run on a schedule:
`test_hint_reveal.py`, `test_three_hint_buttons.py`,
`test_three_hint_buttons_prod.py`, `test_issue27_regression.py`,
`test_issue18_battlelog.py`, `test_issue19_alerts.py`,
`test_hint_logic.py`, `ui_fixes_verify.py`, `holo_card_verify.py`,
`holo_card_verify_edge_cases.py`, `verify_defeat_reset.py`,
`verify_victory_reset.py`, `verify_prompts.py`, `playwright_full_test.py`,
`mvp_deferred_tests.py`, `_show_game_live.py`.

## Generated data files (not source)

The many `_*.json`, `claude_*.json`, `*_results.json`, and similar files in
this directory are intermediate outputs from the scripts above (batches,
judge results, comparison pairs), not hand-authored source. `data.json` is
the one exception — see the root README for its relationship to
`cf-pages/functions/_lib/data.json`.
