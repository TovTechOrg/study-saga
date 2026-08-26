# MVP Testing Plan

Context: last session (2026-07-22) fixed a set of frontend bugs (combat screen
display mode, quiz modal reopening guard, victory/defeat screen visibility,
`resetGame()` cleanup) and a hint-scrubber word-boundary bug in
`rag_pipeline.py`, all still uncommitted. `playwright_full_test.py` currently
covers one happy-path run: main menu -> deploy -> Biology -> chained attack
loop -> single/multi answer handling -> feedback close -> victory/defeat
detection -> CAP-out/Recharge fallback -> console error capture. This plan
lists what's still untested before calling the app MVP-ready, ordered by how
directly each item validates a fix already made vs. new coverage.

## New feature (2026-07-27): enemy "Resolve" mechanic

Added an internal-state AI for enemies (inspired by Demis Hassabis's
individual-agent design in *Theme Park*, where each visitor had its own
internal variables rather than the park following one global script). The
enemy's counterattack was previously a hardcoded flat 12 damage regardless of
which enemy it was or how the fight was going -- `config.json` already
defines a distinct `attack_power` per enemy (Golem 12, Confusion Sprite 12,
Knowledge Thief 18) but `app.py`'s `combat_action` never read it.

Now each enemy has its own `resolve` stat (0-100, starts at 50, session-local):
correct answers rattle it (-18), wrong answers embolden it (+14), and its
counter-damage scales 0.5x-1.5x its `attack_power` based on current resolve.
At very low resolve it can hesitate (skip its counter); at very high resolve
it can land an emboldened bonus hit. Surfaced in the enemy HUD card as a new
amber "Resolve" bar (repurposing what was a decorative, never-updated "CAP"
bar on the enemy card). Verified via direct API calls (resolve fell
50->32->14->0 across 3 correct answers, counter damage scaled 10->8->6
accordingly) and visually via Playwright screenshot.

**Not yet play-tested for balance** -- worth a manual playthrough to see how
it feels (does a long correct streak make the enemy so passive it trivializes
the fight? does a bad streak make it swing hard enough to feel unfair?).

## High priority — validates last session's actual fixes

1. **Replay after victory/defeat** — start a second game from the main menu
   after reaching an end screen. This is exactly what the `resetGame()`
   classList fix targeted (victory/defeat screens getting permanently stuck
   or failing to reappear). The current test only runs one playthrough.
2. **Force both outcomes** — the test only asserts whichever outcome the RNG
   happened to produce. Confirm a defeat screen has actually been seen
   rendering correctly (not just victory), since they use separate code
   paths.
3. **Rapid/double-click on Attack** — the quiz-modal "already active" guard
   removal was fixing a race with the feedback modal. Worth a deliberate
   double-click stress test, not just the normal chained flow.

## Medium priority — untested surface area

4. **All four subjects**, not just Biology — Math/Chemistry/Physics have
   different hint content and were touched by different repair scripts
   (`fix_glued_artifacts.py`, the core hints audit). Biology passing doesn't
   confirm the others render correctly.
5. **Hint tier switching** (hard/medium/easy) and answer-leak check — confirm
   the word-boundary scrubber fix actually stops both glued artifacts and
   real answer leakage in hints that haven't been regenerated recently.
6. **Mid-game page refresh** — does state recover or does it break silently?
7. **Visual check of the modal `overflow-y:auto` fix** — a screenshot with a
   long hint to confirm it scrolls instead of overflowing the screen.

## Lower priority / nice-to-have

8. Cross-browser (test likely only runs Chromium).
9. A fresh `audit_core_hints.py` pass to get current quality scores as a
   baseline before deciding anything about the Gemini-vs-Groq question.

## Next step

Extend `playwright_full_test.py` to cover items #1-3 (replay loop, forced
defeat, double-click), since those directly prove the bug fixes hold — which
matters more than broad coverage for calling this MVP-ready.

## Manual test log (2026-07-27)

### Item #1 (replay after victory) — in progress, passing so far
- Round 1 (Biology): played to Victory screen — rendered correctly.
- Clicked "Return to Main Menu": clean return, no leftover overlay, Deploy
  System clickable again.
- Round 2 (Biology) deployed: quiz modal renders normally, no stuck-modal
  issue. Still mid-playthrough — not yet reached a second end screen.
- Not yet done: confirm round 2 actually reaches Victory/Defeat and that
  screen renders correctly a second time; a third round for extra confidence;
  the forced-defeat path (#2) and double-click stress test (#3) haven't been
  attempted yet.
- 2026-07-28: that round 2 attempt's session was lost -- `GAME_SESSIONS` in
  `app.py` is an in-memory dict with no persistence, and it got wiped by a
  Flask dev-server reload (triggered by the `app.py` edits made during the
  Resolve-mechanic work) while the browser tab was left open overnight. The
  tab's stale `game_id` then hit `combat_action`'s 404 "Invalid game session"
  path, surfaced to the user as a raw, ungraceful `alert()` rather than an
  auto-reset to the main menu -- a minor UX gap, not yet fixed. Round 2 needs
  to be replayed from a fresh Deploy System click.
- Correction: the app actually already has a graceful auto-recovery path for
  this (`handleInvalidSession` in game-simple.js:74) -- confirmed via console
  log that it auto-simulates a Deploy System click and restarts cleanly with
  no user action needed. The raw-alert version seen earlier was from an older
  moment; current code (v=4) handles it well. This session also hit one
  separate, unresolved cosmetic issue: the page went fully black once
  (all screens hidden, no JS error logged, recovered cleanly via page
  refresh) -- root cause not confirmed, noted as an open low-priority item.
- 2026-07-28: Round 2 (after several in-session restarts caused by the above)
  reached the Victory screen successfully. This confirms the core thing item
  #1 was checking: Victory renders correctly on a subsequent, non-first
  playthrough, not just the very first one.
- 2026-07-29: **Item #3 (double-click stress test) CLOSED, PASS.** Ran via
  Playwright: answered a question, rapid-double-clicked the feedback modal's
  Close button. Result: feedback modal correctly deactivated, exactly one
  new quiz question opened (not duplicated/stuck), zero console/page errors.
  The old "quiz modal already active" guard removal (last session's fix)
  holds up under an actual rapid double-click, not just normal-speed play.
- 2026-07-29: **Item #8 (cross-browser) CLOSED, PASS.** Installed Firefox
  and WebKit via Playwright (only Chromium was present) and ran the same
  menu -> combat -> quiz -> answer -> feedback flow through both. Zero
  console errors, zero page errors in either engine; screenshots confirm
  pixel-identical rendering to Chromium (Resolve bar, HP/CAP bars, glow
  effects) with no layout differences.
- 2026-07-29: **Item #6 (mid-game page refresh) CLOSED, PASS.** Ran via
  Playwright: got into active combat, reloaded the page. Result: cleanly
  resets to main menu (no stuck modal/orphaned combat screen), zero console
  errors, and a fresh game starts normally immediately after. In-progress
  fight state isn't preserved across a refresh (expected -- no client-side
  persistence), but nothing breaks.
- 2026-07-28: **Item #1 CLOSED.** Clicked "Return to Main Menu" from the
  round-2 Victory screen -- clean return, no stuck overlay -- and successfully
  selected and started a new round from the main menu. Full loop (Victory ->
  clean reset -> new round playable) confirmed working. Still open: #2
  (forced defeat path -- only Victory has been directly observed so far, not
  Defeat, in this session) and #3 (deliberate double-click stress test on
  Attack) have not been specifically exercised.
- 2026-07-28: Third Victory screen reached this session (the round the user
  called "round #2" in their own numbering, played out fully alongside the
  hint-quality sampling). Further confirms the replay loop is solid across
  repeated rounds, not just a one-off pass.

### Hint quality — new finding, elevates item #5 from "check" to "confirmed problem"

While manually testing, 9 consecutive Hard-tier hints were scored by hand.
**9/9 scored <=3/10.** This is a distinct, confirmed problem, separate from
(and larger than) the glued-artifact regex bug already fixed last session.

| # | Question | Issue | Score |
|---|---|---|---|
| 1 | Mitochondria function | Literal `[concept]` placeholders | 2/10 |
| 2 | Vein vs. artery | Vague, doesn't rule out lymphatic vessel | 3/10 |
| 3 | Starfish symmetry | Inaccurate "gears" metaphor (hydraulics, not mechanical) | 3/10 |
| 4 | Photosynthesis products (multi-select) | Omits a correct answer ("Oxygen"), factually wrong | 2/10 |
| 5 | Carnivorous plant | Conflated sticky-trap + snap-trap mechanisms, grammar mismatch | 3/10 |
| 6 | Brain temperature regulation | Circular/tautological, no naming clue | 2/10 |
| 7 | Oxidative phosphorylation | Factory template, wrong mechanism (assembly-line vs. proton-gradient rotor) | 2/10 |
| 8 | Pituitary gland | Good analogy, ruined only by `[concept]` bug + wordiness | 2/10 |
| 9 | Rainforest ecosystem | Over-abstracted a trivially simple concept | 2/10 |
| 10 | Mitochondria (animal cells variant) | Scientifically accurate, good clue -- vocab pitched above question level | 7/10 |
| 11 | Biodiversity ecosystem services (multi-select) | 2nd multi-select coverage failure: covers only 1 of 3 answers | 2/10 |
| 12 | Plant tissues (multi-select) | 3rd multi-select coverage failure: covers only 1 of 3, doesn't flag the animal-tissue distractor | 1/10 |
| 13 | Species richness (biodiversity term) | "Purple prose" register (archaic/literary, not tech-jargon), doesn't help distinguish 5 similar-sounding options | 2/10 |
| 14 | Biomolecule forming enzymes | 3 clashing metaphors stacked in one sentence, circular (restates function not composition), ambiguous clue also fits 2 wrong answers | 1/10 |
| 15 | Prokaryotic cell characteristic | "Corporate tech-speak" register (distributed framework/central hub) -- same hint shown unscored at session start | 3/10 |
| 16 | Central nervous system parts (multi-select) | 4th multi-select issue, but via ambiguity ("mirrored"/"dual" reads as brain hemispheres, not brain+spinal cord) rather than outright omission | 1/10 |
| 17 | Kidney's structural/functional unit | Accurate, restrained metaphor -- but ignores the actual Nephron/Neuron near-miss distractor trap | 3/10 |
| 18 | Heart pumping blood (term recall) | Just restates the question's own definition in metaphor; vocabulary-recall question needs a word-recall clue, not a mechanism description | 2/10 |
| 19 | Cell as "building block of life" | Sound standard analogy (cell-as-city), but buried in dense vocabulary + a perspective mismatch (question frames bottom-up hierarchy, hint zooms into internal mechanics instead) | 4/10 |
| 20 | What is photosynthesis? | 2x literal `[concept]` placeholders -- same exact hint flagged in the original regex scope-scan as a worst offender, now confirmed live | 0/10 |
| 21 | Protein synthesis components (multi-select) | 1st multi-select hint (of 5 sampled) to actually cover all correct answers -- still capped by "creative writing riddle" over-abstraction and missing the DNA-polymerase distractor trap | 4/10 |
| 22 | Symbiotic relationship example | New category: underlying question is arguably flawed (single-select, but Mutualism/Commensalism/Parasitism are all technically symbiotic), and the hint reinforces the misconception that symbiosis = mutual benefit only. 3rd appearance of the "symphony/conductor" stock metaphor | 2/10 |
| 23 | RNA's role in protein synthesis | `[concept]` placeholder again, plus fails to address the transcription-vs-translation distractor trap the question is built around | 0/10 |
| 24 | Transpiration (water movement in plants) | Scored 2/5 (different rubric/reviewer). "Vital gaseous byproduct" actively misleads toward Photosynthesis/oxygen -- same active-misdirection category as #2 and #22. Accurate underlying content (Cohesion-Tension theory, xylem, stomata), wrong register for a quiz hint | ~4/10 |
| 25 | Transpiration, 2nd variant ("What is the process by which water moves...") | Near-duplicate of #24 -- different question phrasing, different option set (drops Osmosis/Diffusion, adds Evaporation), independently-generated hint reusing the same theme ("gaseous tribute" vs. "vital gaseous byproduct"). Confirmed: misleads toward "Evaporation" specifically here (vs. Photosynthesis/oxygen in #24) -- the vague "turns to gas and escapes" closing image misdirects toward whichever distractor happens to overlap with it, a structural weakness not a one-off wording accident | 2/5 (~4/10) |
| 26 | Evolution mechanism via reproductive isolation | CORRECTED (see note below): actual answer is Genetic Drift, not Speciation as the first reviewer assumed -- the hint's "random sampling of a subset" description is textbook-accurate for Genetic Drift (founder effect), so this is NOT a content mismatch. Real issues: 2x `[concept]` placeholders, and heavy metaphor style (infinite library of books) | ~3/10 (placeholder + style only) |
| 27 | Largest human organ (Skin) | Clean, concise, no bugs -- but new failure mode (opposite direction): "protective barrier around the body" is near-leakage for a Hard tier, since no other option is "around" the body. Difficulty-tier calibration is inconsistent in both directions, not just biased toward over-obscurity | 3.5/5 (~7/10) |
| 28 | NOT a stage of cellular respiration (Fermentation) | Genuine scientific error (oxygen mislabeled as a "catalyst," not the terminal electron acceptor), not just jargon. New structural gap: "NOT"/odd-one-out questions have no special prompt handling -- ambiguous whether the hint describes the correct (excluded) answer or the other four | 1/5 (~2/10) |
| 29 | Biodiversity hotspots (multi-select) | Cross-domain jargon extreme: borrows from mathematics (Mandelbrot set/fractals) for a biology question, not just factory/tech/literary registers. Circular like #6/#9/#18 -- "species richness and endemism" just restates the term being defined, giving no actual selection criterion for any of the 3 correct answers | 1/5 (~2/10) |
| 30 | Adaptation/Natural Selection term | 5th distinct metaphor domain seen (cosmic/cartography: "cosmic cartographer refining its map") -- confirms the defect is domain-agnostic, not a specific stylistic tic. Doesn't help separate the real distractor trap (Evolution vs. Natural Selection). Minor own-goal: "adaptive feedback loop" partially cues "Adaptation," a related-but-not-quite-correct concept (not itself an option) | 1/5 (~2/10) |

**Follow-up on #30 -- confirmed answer-key bug, not just an ambiguity.**
Checked `data.json` directly: there are 3 near-duplicate questions for this
concept, keyed inconsistently --
1. "...through genetic changes?" -> correctly keyed **Adaptation**.
2. "...process by which..." (options incl. Artificial selection/Gene flow,
   no Evolution) -> keyed **Natural selection**.
3. "...process by which..." (options incl. Evolution, Natural selection is
   ALSO offered -- this is #30's exact screen) -> keyed **Evolution**.

The game correctly used variant #3's answer key when it marked "Natural
selection" wrong -- not a scoring bug. But variant #3's key itself is
scientifically weak: the question asks what makes "an **organism**" (singular)
better suited to its environment. Individual organisms don't evolve --
populations evolve over generations; individuals are adapted/selected. So
"Evolution" is the looser, less correct answer of the two options on offer,
and it's inconsistent with variant #2's keying of the same underlying concept
in the same file. This is a content/answer-key bug, independent of hint
quality -- worth fixing (either reword variant #3's question to genuinely
match "Evolution," or re-key it to "Natural selection" to match variant #2
and the biology). A player who knows biology, follows the hint's logic, picks
Natural Selection, and gets told they're wrong is exactly the kind of
experience that reads as "this app is broken," not "I got this one wrong."

| 31 | Grassland ecosystem characteristics | Active misdirection: "waves"/"erosive currents"/"tectonic shifts" (geology/ocean imagery) would steer a guessing student toward Coral reef, not Grassland. Same category as #2/#22/#24/#25 (imagery points toward a specific wrong answer). Fits existing root cause #2 (macro-metaphor misapplication), not a new content-mismatch bug -- no alternate correct definition is being described here, just domain-mismatched imagery | 1/10 |

Note: finding #10 is a near-duplicate of #1 (same "mitochondria function"
concept, different question variant in `data.json`), and #25 is a
near-duplicate of #24 (same "transpiration" concept) -- same concept, wildly
different quality each time, confirming this is a reliability/consistency
problem, not "this concept is impossible to hint well."

**Flagged scoping detail:** `data.json` contains multiple redundant question
variants per underlying concept (at least mitochondria x4, transpiration x2+
observed so far), each with an independently-generated hint. This means the
~10% placeholder-bug rate and the metaphor-accuracy problems found in this
investigation are concentrated over a somewhat smaller set of true underlying
concepts than "800 distinct questions" suggests -- worth knowing before
estimating how much unique-content work any fix actually requires.

**Multi-select: 4 of 5 sampled failed coverage** (#4, #11, #12, #16 each
covered only one of the multiple correct answers; #21 finally covered all
three). Still the tightest, most reproducible pattern found -- and #21 proves
the model *can* comply with the prompt's explicit multi-answer-coverage rule
(see root cause #3 below), confirming this is an enforcement/reliability gap,
not a capability gap. Worth prioritizing if only one fix gets made.

**Scope check (data.json regex scan, not just these 9 samples):** 249/2400
hint fields (~10.4%) contain a literal `[concept]` token — biology 12.2%,
physics 13.7%, chemistry 11.5%, math 4.2%. 69 of those have 2+ occurrences in
a single hint field (worst: a photosynthesis hint with 6 `[concept]` tokens
in one sentence).

**Root cause (found in `rag_pipeline.py`'s `generate_hint_groq` prompt,
~line 240-273) — three separable problems, not one:**

1. **`[concept]` placeholder bug** — a post-processing bug, not a prompt bug.
   The generation prompt only forbids the model from outputting the literal
   string `"[REDACTED]"`; a separate downstream function (`get_safe_hint()`)
   independently detects leaked answer-words and masks them with the literal
   string `[concept]`, visible to the end user. The two aren't in sync.
2. **No accuracy verification for analogies** — the prompt instructs
   "macro-level concepts -> physical machinery/architectural framework
   metaphors," which is the literal source of the pervasive
   factory/assembly-line/gears/conveyor-belt motif (findings #3, #5, #7, and
   the "new Biology game" oxidative-phosphorylation hint). The model applies
   this even to micro/molecular concepts that should get cellular/biochemical
   metaphors instead, and nothing checks whether the chosen metaphor's
   mechanism is actually correct (finding #3: gears for a hydraulic system;
   finding #7: assembly-line for a proton-gradient rotary motor). This is a
   one-shot creative-writing call with no fact-check pass.
3. **Multi-answer coverage instruction exists but isn't reliably followed** —
   the prompt already has an explicit rule (this is not a missing-instruction
   gap) that every tier must give a way to identify ALL correct answers for
   multi-select questions. Finding #4 shows the model doesn't reliably comply
   — an enforcement/verification gap, not a prompt-design gap.
4. **Missing prompt branch for named-entity answers** — there's a
   "DEFINITION AVOIDANCE" rule for when the answer literally defines a term
   named in the question (e.g. "What is photosynthesis?"), but no equivalent
   rule for questions where the answer is a *named entity* (a gland, an
   ecosystem type) and the question already states its function/definition.
   Nothing tells the model to pivot to a *different* identifying fact instead
   of re-describing the given function — this produced the circular
   hypothalamus hint (#6) and the over-abstracted rainforest hint (#9, where
   the question already gives away the answer and the hint should just
   confirm it plainly instead of dressing it up).
5. **No handling for "NOT"/odd-one-out questions (new, found at sample #28)**
   — the prompt has no branch for negated question phrasing ("Which of the
   following is NOT..."), so the hint's dense description doesn't make clear
   whether it's characterizing the correct (excluded) answer or the other
   four options. Only one instance seen so far; scope unknown.

**Decision needed (not yet made):** which of the fixes above to prioritize.
Placeholder-masking is the cheapest and would likely flip some hints (e.g.
#8) straight from broken to fine; the analogy-accuracy problem is the largest
in scope but requires either prompt redesign or an added verification/
self-check step, which is a bigger lift.

**Retracted:** sample #26 was briefly logged as a new "content mismatch"
root cause (hint describing Genetic Drift for a question assumed to want
Speciation). Corrected -- the actual marked answer is Genetic Drift, and the
hint's description was textbook-accurate for it (founder effect). Not a
mismatch; the first reviewer's assumption about the intended answer was
wrong. #26's real issues are just the `[concept]` placeholder bug and heavy
metaphor style, same as the rest of the corpus. No 5th root cause exists.

## Full corpus regeneration + cleanup (2026-07-29 to 2026-08-01)

Ran `regenerate_full_corpus.py` (marker-based, resumable) across all 800
questions using the fixed pipeline, then 4 cleanup rounds re-targeting
whatever was still broken after each pass (mostly caused by Groq's daily
token quota staying exhausted for most of this multi-day stretch, degrading
even the rephrase-based leak-fix fallback). Also fixed two bugs found
mid-run: a script crash from a Windows console Unicode-encoding issue, and a
validation gap that was silently accepting failed API calls ("Connection
failed" etc.) as if they were real hints -- both fixed in
`regenerate_full_corpus.py`.

**Mechanical bug rate over the 4 cleanup rounds:**
| Round | Clean | Placeholder bug | Fake-failure |
|---|---|---|---|
| After main run | 77.6% | 19.5% | 2.9% |
| Round 1 | 87.4% | 9.5% | 0.0% |
| Round 2 | 91.5% | 6.9% | 0.0% |
| Round 3 | 98.6% | 1.0% | 0.0% |
| Round 4 (final) | **100.0%** | **0.0%** | **0.0%** |

**Result: 100% of the 800-question corpus is now mechanically clean** -- zero
`[concept]` placeholder occurrences, zero fake-API-failure content anywhere.

**This does NOT mean 100% of hints are semantically good.** Manual spot-reads
across multiple rounds (see samples #1-31 above, plus later spot-checks)
found recurring problems that no mechanical scan can catch:
- ~7% of "clean" hints had a genuine factual/accuracy error (e.g. enzymes
  described as converting energy like ATP; activation energy conflated with
  needing a catalyst)
- Multi-select coverage is still failing at a meaningfully high rate even
  with the verification+retry step built for it (3 of 4 sampled multi-select
  questions in one batch had a coverage gap) -- the existing single-model
  verify-and-retry isn't robust enough, especially under the same rate-limit
  pressure that caused everything else this stretch
- Some hints are vague/circular even when factually fine (e.g. a numeric
  hint that never actually scaffolds toward the calculation)

**Decision made:** build a proper accuracy-verification pass (critique-and-
revise loop, judge model separate from the generator per Google AI Studio's
architecture advice) rather than trust further blind regeneration attempts
to fix the semantic layer. Plan: use Gemini as the judge (avoids compounding
Groq's rate-limit problem, and Gemini infra already exists in
`rag_pipeline.py`), test on ~50 questions before running across the full
corpus. Separately, user wants to run a full Groq-vs-Gemini 3.5 Flash Lite
comparison first to decide which model should be primary vs. judge --
`generate_hint_gemini`'s prompt needs to be brought to parity with the
improved Groq prompt first, or the comparison is biased against Gemini by
default.
