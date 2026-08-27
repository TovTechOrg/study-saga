# Study Saga

A browser-based study game: players pick a syllabus (Math, Biology, Chemistry, or Physics) and battle enemies by answering quiz questions. Wrong answers cost HP, correct answers deal damage and earn hint credits, and an AI hint pipeline can explain any question on request.

**Live:** https://study-saga.pages.dev — 100% Cloudflare (Pages + Pages Functions + KV/Firestore), no Python/Flask involved.
**Landing page:** GitHub Pages, served from [`docs/`](docs/)

## Repo layout

This repo contains the production app plus an older prototype and a content-authoring pipeline:

```
study-saga/
├── cf-pages/          # ✅ Production app — deployed to Cloudflare Pages
│   ├── functions/     #    Pages Functions (serverless API routes)
│   │   ├── api/       #    start-game, start-combat, combat-action, get-hint,
│   │   │               #    reset-game, auth-resume, syllabi
│   │   └── _lib/       #    game.js (session/KV helpers), auth.js (Firebase
│   │                    #    token verification), profile.js (Firestore),
│   │                    #    data.json/config.json (question corpus)
│   └── public/         #    Static frontend — index.html, game-simple.js,
│                        #    holo-card.js/css, neural-bg.js, style-neural.css
├── backend/           # Original Flask prototype + content pipeline
│   ├── app.py         #    Local dev server (same game logic as cf-pages,
│   │                   #    used for iterating before porting to Functions)
│   ├── data.json       #    Master question corpus (mirrored into cf-pages)
│   ├── archive/        #    Retired standalone scripts, kept for reference
│   └── *.py, *.md      #    Hint-generation/audit/bakeoff scripts — indexed
│                        #    in backend/README.md, see below
├── frontend/          # Templates/static assets consumed by backend/app.py
└── docs/              # Static GitHub Pages landing page + archived history
    ├── history/        #    Superseded session-status/planning docs
    └── reports/         #    Benchmark/diagnostic report snapshots
```

The **cf-pages/** app is what's actually live at study-saga.pages.dev — it's the entire production stack, and it's JavaScript end to end (Pages Functions + vanilla JS frontend), not Python. **`backend/app.py`** is a Flask app kept around only as a local mirror for faster iteration on game logic before porting changes to Functions — it is never deployed. The rest of `backend/` is a large collection of one-off scripts used to build and QA the question/hint corpus — see [`backend/README.md`](backend/README.md) for an index, and [Content pipeline](#content-pipeline) below for the broader picture.

## Gameplay

- **Syllabus select → combat.** Each syllabus is a series of enemy encounters; each question is one "turn."
- **Hint economy.** Every game starts with 3 Simple hints (reveals the easy-tier explanation) and 1 Deep hint (full multi-tier breakdown). Correct answers earn +1 credit, defeating an enemy earns +2; credits buy extra hints once the free budget runs out.
- **Per-level results.** Victory/defeat screens show which questions were answered correctly vs. missed for that encounter.
- **Holographic cards.** Player/opponent combat cards have a pointer-tracked holo-foil effect (`mix-blend-mode: color-dodge`), with device-tilt on mobile, reduced-motion support, and a low-effects toggle.
- **Optional Google Sign-In.** Signing in links your active game to your Firebase account; signing in on another device offers to resume that in-progress combat. Guests are unaffected — auth is entirely opt-in.
- **Accessible, responsive UI.** No horizontal overflow at mobile/tablet/desktop breakpoints, keyboard-navigable syllabus cards, a real focus trap + Escape-to-close on modals, and KaTeX-rendered math notation.

## Running locally

### Production app (`cf-pages/`)

```bash
cd cf-pages
npm install
npx wrangler pages dev public
```

Required bindings/secrets are listed under [Deployment](#deployment) below.

### Flask prototype (`backend/`)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`. Live hint generation needs `GEMINI_API_KEY`/`GROQ_API_KEY` in `backend/.env`; without them, only pre-generated hints from `data.json`/`final_corpus_gemini_hints.json` are served. This is a local-only dev mirror — it is never deployed anywhere.

## Deployment

The `study-saga` Cloudflare Pages project has **no Git integration** — it does not auto-build from this (or any) GitHub repo. Every deploy is a manual push of the built directory straight to Cloudflare's edge from a local machine:

```bash
cd cf-pages
npx wrangler pages deploy public --project-name study-saga --branch main
```

Build settings (there is no build step — `public/` is served as-is):

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(none)* |
| Build output directory | `public` |
| Functions directory | `functions` (auto-detected, Pages Functions) |
| Root directory | `cf-pages` |
| Git integration | None — CLI-only deploys via `wrangler pages deploy` |

### Google Sign-In domain allow-list

Firebase Auth (project `study-saga-live`) only allows sign-in from domains it's explicitly told about. **Whenever the deploy target changes** (new custom domain, new preview subdomain, moving to a different Cloudflare Pages project), two separate allow-lists need updating or Google Sign-In fails with `auth/unauthorized-domain`:

1. **Firebase Console → Authentication → Settings → Authorized domains** — add the new domain (e.g. `study-saga.pages.dev`). Note: Cloudflare Pages preview deploys use `*.study-saga.pages.dev` subdomains, which the apex entry does not cover — add specific preview domains as needed, or accept that sign-in only works on the production URL.
2. **Google Cloud Console → APIs & Services → Credentials**, on the OAuth 2.0 Web client Firebase uses — add the domain to **Authorized JavaScript origins** (e.g. `https://study-saga.pages.dev`) and confirm **Authorized redirect URIs** includes `https://study-saga-live.firebaseapp.com/__/auth/handler`.

Both of these are console-only settings — there is nothing in this repo that can add a domain for you, and no CLI currently authenticated in this environment can either (`firebase login` credentials here are expired). Whoever has access to the `study-saga-live` Firebase/GCP project needs to make these two changes by hand.

Required bindings/secrets (set in the Cloudflare Pages dashboard or `wrangler.toml`):
- KV namespace `GAME_SESSIONS` — active game sessions
- A Firebase project (`study-saga-live`) with Google Sign-In enabled, for optional auth
- Firestore in that Firebase project, with security rules restricting each `user_profiles/{uid}` doc to its own token (rules are inlined as a comment in `functions/_lib/profile.js`)

Because deploys aren't tied to `git push`, the state of this repo's `main` branch on GitHub can lag behind what's actually live — check `npx wrangler pages deployment list --project-name study-saga` for the real deployment history rather than assuming the latest commit is what's served.

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every PR to `main` and every push to `main`:

| Check | Blocking? |
|---|---|
| Corpus validation (`backend/validate_corpus.py` — schema, exactly-one-correct-answer for single-select, all 3 hint tiers present) | Yes |
| JS syntax check (`cf-pages/check-js-syntax.sh` — `node --check` over every frontend script and Functions module) | Yes |
| Python lint (`ruff` over `backend/`) | No — report-only, given ~75 inherited scripts never linted before |
| README link check (`check-readme-links.py`) | Yes |

**CI does not deploy anything and does not replace the manual deploy step above** — a merged, green PR still requires the `npx wrangler pages deploy` command to actually ship. A corpus-drift check (verifying `backend/data.json` and `cf-pages/functions/_lib/data.json` haven't diverged) is intentionally not included yet — the two files have already diverged and which one should be authoritative is an open question (issue #24); adding the check before that's resolved would just fail on every PR.

### Difficulty tier guidelines (issue #9)

Every question in the corpus carries a `difficulty` field of `"easy"`, `"medium"`, or `"hard"` (untagged questions default to `medium`). Question authors — human or LLM-prompted — should write to these definitions so tiers stay meaningfully different in practice, not just in name:

| Tier | Reasoning | Score multiplier |
|---|---|---|
| Easy | Recall and definitions. Answerable by directly remembering a single fact, term, or definition. Single-step reasoning only. | 1x |
| Medium | Applying a concept. Uses a definition/concept in a new context, or two-step reasoning (combining two related facts, or a two-operation calculation). | 1.5x |
| Hard | Multi-step problems, distractor-heavy options. At least three reasoning steps or calculation stages, or a non-trivial scenario requiring synthesis. | 2x |

A realm's tier is unselectable in the UI until it has at least **15 questions** at that difficulty (`MIN_TIER_QUESTIONS` in `cf-pages/functions/_lib/game.js`) — a tier under that floor is disabled rather than silently falling back to the full question pool.

## Content pipeline

`backend/` doubles as the workspace for building and grading the question/hint corpus — generator bake-offs (Gemini vs. Groq vs. Gemma across Math/Biology/Chemistry/Physics), an LLM-judge comparison harness, difficulty classification, and audit scripts that catch things like glued-together text artifacts or mismatched answer keys. Results and intermediate corpora are checked in as `*_results.json`/`*_report.json` next to the scripts that produced them. This is R&D scaffolding, not part of the served app — treat scripts here as a lab notebook rather than a stable API.

## Known gaps / roadmap

- **Points/gacha economy** (spend earned credits on upgrades — potions, attack-power boosts) is scoped but deferred; the hint-credit system above is the first slice of it.
- **Chemistry hint quality** trails Biology/Physics in bake-off scoring (~14.5% of sampled hints score below the quality floor, vs. ~3-5% for the other two subjects) — root cause still open.

## License

This project is open source and available under the MIT License.
