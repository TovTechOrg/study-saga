# Study Saga — Session Status (as of 2026-08-09)

Everything below is halted (laptop overheating). This is a handoff doc so work can resume cleanly. Nothing is currently running — no dev servers, no background scripts.

## 1. Cloudflare Deployment — ✅ DONE, live

- Live at **https://study-saga.pages.dev**
- Flask backend ported to Cloudflare Pages Functions (`cf-pages/functions/`), sessions moved from in-memory dict to Cloudflare KV (`GAME_SESSIONS` namespace).
- Hint-credit system shipped: 3 Simple hints + 1 Deep hint per game, credits earned from correct answers (+1) and victories (+2) unlock more of either.
- Per-level correct/incorrect results screen shipped (victory/defeat screens).
- Fixed a real data bug: "7 - (-2)" had the wrong `isCorrect` flag in `data.json` (fixed in both `backend/data.json` and `cf-pages/functions/_lib/data.json`).
- GitHub CLI (`gh`) and Cloudflare Wrangler CLI both installed and authenticated this session.

## 2. Git / Repo — ✅ DONE

- Repo moved to **https://github.com/TovTechOrg/study-saga** (`main` branch), now the project's main repo.
- Old repo (`8GSean/study-saga`) still exists but is no longer primary.
- Commit authorship on your 4 commits corrected to `Talia Kohen <Talia.Kohen@gmail.com>` (the 4 older commits by Avihay Baratz and Yonatan Perlin were left untouched — not yours to reattribute).
- Local git remotes: `origin` = `8GSean/study-saga`, `tovtech` = `TovTechOrg/study-saga`.
- **The UI/UX work below (section 3) is NOT committed or pushed yet.**

## 3. UI/UX Overhaul — 🔨 IN PROGRESS, code done, verified working, not yet redeployed

Fixing 7 GitHub issues Sean filed against the live deploy (`TovTechOrg/study-saga` issues #1-7): viewport overflow, inconsistent button styling, oversized typography, quiz layout/math rendering/accessibility, low-contrast character art, missing navigation. Full audit + plan saved at `C:\Users\talia\.claude\plans\structured-stargazing-whisper.md`.

**All code changes are done:**
- `cf-pages/public/static/css/style-neural.css` — fully rewritten: responsive breakpoints, `clamp()` typography, focus-visible states, `.answer-btn`/checkbox styling, sprite glow, `.game-nav` styles, dead duplicate CSS block removed.
- `cf-pages/public/index.html` — nav bar markup, ARIA (`role="dialog"`, `aria-modal`, `aria-labelledby`) on both modals, KaTeX CDN tags, dead `script.js` reference removed, cache-bust bumped to `?v=5`.
- `cf-pages/public/static/js/game-simple.js` — duplicate realm-name bug fixed (eyebrow now says "Realm" instead of repeating the name), keyboard-accessible syllabus cards (`tabindex`, Enter/Space), focus trap + `closeQuizModal()`/`deactivateModal()` wired into both modals, `#close-quiz-btn`/Escape working, math normalizer + KaTeX render wired into question/answer text, nav bar wired (shows on syllabus-select/combat, hides on main menu, shows realm name in combat).
- Deleted confirmed-dead files: `cf-pages/public/static/css/style.css`, `cf-pages/public/static/js/script.js`.

**A real bug was found and fixed during verification — worth knowing if anything similar breaks later:** the focus trap's initial `.focus()` call was being silently ignored by the browser. Root cause: `getComputedStyle()` on the quiz modal still reported `visibility: hidden` even a full animation frame after adding the `.active` class, because the modal's opacity/visibility change goes through a CSS transition (`transition: opacity 0.4s ease, visibility 0.4s ease`) that hadn't resolved yet — calling `.focus()` while the browser still considers the element non-focusable is a no-op, not an error. Fixed by waiting for the actual `transitionend` event (with a 450ms `setTimeout` fallback in case it never fires) instead of guessing at frame timing.

**Verified working via a Playwright test script** (`backend/ui_fixes_verify.py`, kept in the repo, uses `backend/.venv` which already has Playwright installed):
- ✅ No horizontal scroll at mobile (390×844), tablet (768×1024), or desktop (1920×1080) on main-menu, syllabus-select, or combat screens.
- ✅ Nav bar visible on syllabus-select/combat, shows realm name (e.g. "BIOLOGY") in combat.
- ✅ Answer buttons are properly styled (neon dark theme, confirmed via computed `background-color`, not native gray).
- ✅ Focus trap holds correctly — 12+ Tab presses cycle only within the modal, wrapping at both boundaries.
- ✅ Escape closes the quiz modal correctly.
- ⚠️ **Realm-name-appears-twice check reported a false positive** — that was a flaw in the *test script* (naive substring counting; "Biology" legitimately appears in both the `<h3>` and the "Biology realm" description text), not a real bug. The actual fix (eyebrow no longer repeating the name) is confirmed working by inspection.
- ❓ **Math/KaTeX rendering not actually confirmed yet** — the test script's "hunt for a math question" loop has a bug: after pressing Escape to skip a non-math question and reopen with a new `#attack-btn` click, the quiz modal doesn't advance to a new question, causing later `page.click("#attack-btn")` calls to time out (the modal's already open, click hits the modal backdrop instead). This is a test-script issue, not necessarily a game bug — but it means KaTeX rendering is still **unverified**, and should be checked before considering this fully done.

**Not started:**
- Fix the math-rendering test loop (or just manually check a math question in a browser) to confirm KaTeX actually renders.
- Redeploy via `wrangler pages deploy public --project-name study-saga --branch main`.
- Commit + push to `TovTechOrg/study-saga`.

## 4. Firebase Accounts/Gacha Feature — ⏸ PAUSED, blocked

Plan for this feature (auth, cross-device saves, points economy, gacha upgrades, potions/attack-power) is no longer saved anywhere as a plan file (the plan-mode file was overwritten by the UI/UX plan) — would need to be re-derived from this conversation's history if picked back up, or re-planned fresh.

- Firebase CLI installed, logged in as `taliakohen@tovtech.org`.
- **Blocked on:** `firebase projects:create` kept failing on "Callers must accept Terms of Service" — root cause turned out to be Google Cloud requiring 2-Step Verification (2SV/MFA) on the account, not actually a ToS issue (misleading error).
- You clicked "Enable MFA"/"Turn on 2SV" but we never confirmed whether it completed.
- **Next step when resuming:** confirm 2SV is active, then retry `firebase projects:create study-saga-game --display-name "Study Saga"`.

## 5. LLM Bakeoff / Generator-Judge Architecture — 🔨 IN PROGRESS

**Decided, strongly confirmed: Gemini as content-generation model.** At 94.3% coverage of the BCP (biology/chemistry/physics) full bakeoff:

| Subject | Avg score | n | Below 7/10 floor |
|---|---|---|---|
| Biology | 9.56 | 200/200 (complete) | 3.0% |
| Chemistry | 8.87 | 200/200 (complete) | **14.5%** (the one open thread) |
| Physics | 9.52 | 166/200 | 4.8% |
| **Overall** | **9.31** | 566/600 | 7.6% |

- Math syllabus bakeoff: 200/200, complete, separately.
- **BCP bakeoff progress since last full check:** grew from 431→492→566/600 across several unattended runs (auto-resumes through Gemini quota walls). Last known state: not currently running; 34 physics questions remain. Re-run `backend/bcp_full_bakeoff.py` to continue whenever convenient — it's resumable and picks up where it left off.
- Physics turned out to NOT be the weak subject (an earlier prediction that didn't hold up) — it's now essentially tied with biology for best-performing. **Chemistry's 14.5% below-floor rate remains the one real open question** — consistently worse than the other two subjects across the whole sample, unexplained.

**Still open: Groq vs. Gemma as judge — no real verdict yet.** Confirmed the main bakeoff data structurally can't answer this (`hint_judge.py`'s fallback function only ever calls Gemma when Groq fails, never both). Reliability-wise, the split has evened out to **~50/50 (152 Groq / 155 Gemma** of 307 tracked calls) — Groq's earlier rate-limiting looks transient, not fundamental. But reliability ≠ quality. Two scripts exist to actually answer the quality question, both still unfinished:

- `backend/finish_groq_vs_gemini_judged.py` — scores the existing unscored 100-question Groq-vs-Gemini generator comparison. **7/100 done**, resumable.
- `backend/groq_vs_gemma_judge_headtohead.py` — the actual Groq-vs-Gemma judge quality test (30 sampled hints, judged independently by both). **Never run at all.**

Both need `GROQ_API_KEY`/`GEMINI_API_KEY` (already in `backend/.env`) and may hit the same Gemini quota wall as the main bakeoff.

## Quick resume checklist

1. **UI/UX (closest to done):** manually verify KaTeX math rendering in a browser (or fix the test script's loop bug), then `wrangler pages deploy public --project-name study-saga --branch main`, then commit + push to `TovTechOrg/study-saga`.
2. Re-run `bcp_full_bakeoff.py` to finish the last 34 physics questions, then run the two judge-comparison scripts to finally settle Groq vs. Gemma.
3. Confirm 2SV status on `taliakohen@tovtech.org`, resume Firebase project creation for the accounts feature.
