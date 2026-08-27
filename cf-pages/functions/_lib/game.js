import DATA from './data.json';
import CONFIG from './config.json';

export { DATA, CONFIG };

export function jsonResponse(obj, status = 200) {
    return new Response(JSON.stringify(obj), {
        status,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
    });
}

// Per-tier question timer (issue #29): Easy longer, Hard shorter, per #9's
// original ask. Exact values are a starting point, not tuned from playtest
// data -- easy to retune later since combat-action.js reads this one place.
export const QUESTION_TIME_LIMIT_MS = { easy: 30000, medium: 20000, hard: 12000 };

// A grace window added on top of the nominal time limit before the server
// treats an answer as late -- covers real network/render latency between the
// client's timer hitting zero and the request actually arriving, so a
// player who answered in time is never penalized for the network. The
// client-side countdown and auto-submit-on-expiry are the actual UX; this
// is a server-side backstop only, consistent with scoring being server-
// authoritative everywhere else in this codebase (issue #20).
export const QUESTION_TIME_GRACE_MS = 3000;

export function questionTimeLimitFor(difficultyTag) {
    return QUESTION_TIME_LIMIT_MS[difficultyTag] ?? QUESTION_TIME_LIMIT_MS.medium;
}

// effectiveStats (issue #23) is optional so every existing caller that
// doesn't know about upgrades yet (or has none purchased) keeps working
// unchanged with base config values.
export function freshPlayer(existingScore, effectiveStats) {
    const keeperCfg = CONFIG.players.default_kk;
    const maxHp = effectiveStats?.max_hp ?? keeperCfg.max_hp;
    const maxCap = effectiveStats?.max_cap ?? keeperCfg.max_cap;
    return {
        current_hp: maxHp,
        max_hp: maxHp,
        current_cap: maxCap,
        max_cap: maxCap,
        score: existingScore || 0,
    };
}

export function freshEnemy(enemyId) {
    const enemyCfg = CONFIG.enemies[enemyId] || CONFIG.enemies.misconception_golem;
    return {
        name: enemyCfg.name,
        current_hp: enemyCfg.max_hp,
        max_hp: enemyCfg.max_hp,
        attack_power: enemyCfg.attack_power || 12,
        resolve: 50,
        max_resolve: 100,
        score: 0,
    };
}

export function findSyllabus(syllabusId) {
    const target = String(syllabusId || '').toLowerCase();
    for (const entry of DATA.syllabus || []) {
        if ((entry.name || '').toLowerCase() === target) return entry;
    }
    return null;
}

export async function getSession(env, gameId) {
    if (!gameId) return null;
    const raw = await env.GAME_SESSIONS.get(gameId);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

export async function putSession(env, gameId, session) {
    await env.GAME_SESSIONS.put(gameId, JSON.stringify(session));
}

export const SIMPLE_HINT_MAX = 3;
export const HARD_HINT_MAX = 1;

export function freshHints() {
    return { simple_used: 0, hard_used: 0, credits: 0 };
}

// effectiveStats (issue #23) overrides the per-run hint budget when the
// player has Extra/Deep Insight upgrades -- SIMPLE_HINT_MAX/HARD_HINT_MAX
// stay as the base-config fallback for sessions with no upgrades resolved.
export function hintsSummary(hints, effectiveStats) {
    const simpleMax = effectiveStats?.simple_hint_max ?? SIMPLE_HINT_MAX;
    const hardMax = effectiveStats?.hard_hint_max ?? HARD_HINT_MAX;
    return {
        simple_remaining: Math.max(0, simpleMax - hints.simple_used),
        hard_remaining: Math.max(0, hardMax - hints.hard_used),
        credits: hints.credits,
    };
}

// Single source of truth for action costs/effects (issue #15) -- combat-
// action.js enforces these numbers server-side, and every endpoint that
// returns combat state includes them via actionCosts() so the client never
// hardcodes a copy that could drift from the rules.
export const ACTIONS = {
    attack: { cost: 3, damage: 15, label: 'Strike' },
    ability: { cost: 5, damage: 25, label: 'Simplify' },
    recharge: { gain: 5, label: 'Recharge' },
};

// effectiveStats (issue #23) overrides damage/gain when the player has
// relevant upgrades -- CAP costs are never upgraded (only damage output and
// recharge amount are in the catalogue), so those always come from ACTIONS.
export function actionCosts(effectiveStats) {
    return {
        attack: { cost: ACTIONS.attack.cost, damage: effectiveStats?.attack_damage ?? ACTIONS.attack.damage },
        ability: { cost: ACTIONS.ability.cost, damage: ACTIONS.ability.damage },
        recharge: { gain: effectiveStats?.recharge_gain ?? ACTIONS.recharge.gain },
    };
}

// Permanent upgrade catalogue (issue #23) -- deterministic, no randomness:
// the cost and effect printed on a card is exactly what buying it gives.
// Keys are stored as purchased levels in profile.upgrades = { [key]: level }.
export const UPGRADE_CATALOG = {
    neural_capacity: { name: 'Neural Capacity', description: '+1 max CAP per level', stat: 'max_cap', perLevel: 1, maxLevel: 5, costs: [200, 400, 800, 1600, 3200] },
    resilience: { name: 'Resilience', description: '+10 max HP per level', stat: 'max_hp', perLevel: 10, maxLevel: 5, costs: [150, 300, 600, 1200, 2400] },
    efficient_recall: { name: 'Efficient Recall', description: 'Recharge restores +1 CAP per level', stat: 'recharge_gain', perLevel: 1, maxLevel: 3, costs: [300, 900, 2700] },
    extra_insight: { name: 'Extra Insight', description: '+1 Simple hint per run, per level', stat: 'simple_hint_max', perLevel: 1, maxLevel: 3, costs: [250, 750, 2250] },
    deep_insight: { name: 'Deep Insight', description: '+1 Deep hint per run, per level', stat: 'hard_hint_max', perLevel: 1, maxLevel: 2, costs: [1000, 3000] },
    focused_strike: { name: 'Focused Strike', description: '+2 Attack damage per level', stat: 'attack_damage', perLevel: 2, maxLevel: 5, costs: [200, 400, 800, 1600, 3200] },
};

// Balance target (issue #23): the catalogue's 6 upgrades sum to 23 possible
// levels; capping total *purchased* levels at 12 means a player can reach at
// most roughly half of any single upgrade's ceiling, and can never
// simultaneously max every category -- Medium should stay a real fight and
// Hard should stay losable rather than a fully-upgraded player trivializing
// every realm. This is a conservative placeholder tuned by inspection, not
// playtest data (#9's real per-tier enemy scaling doesn't exist yet, which
// is the other half of this issue's balance ask) -- revisit both once #9
// ships and real play data exists.
export const MAX_TOTAL_UPGRADE_LEVELS = 12;

export function totalUpgradeLevels(upgrades) {
    return Object.values(upgrades || {}).reduce((sum, lvl) => sum + (lvl || 0), 0);
}

// Null (not 0) when already maxed, so callers can distinguish "next level
// costs 0" (never true here) from "there is no next level."
export function costForNextLevel(upgradeKey, currentLevel) {
    const upgrade = UPGRADE_CATALOG[upgradeKey];
    if (!upgrade || currentLevel >= upgrade.maxLevel) return null;
    return upgrade.costs[currentLevel];
}

// Resolves a player's purchased upgrade levels into the actual numbers the
// session should use -- computed once at start-combat time and threaded
// through the session as session.effective_stats, rather than combat-
// action.js/get-hint.js reading module-level constants at each use site
// (the real architectural work this issue asks for: those tunables become
// per-session once upgrades exist).
export function effectiveStats(upgrades) {
    upgrades = upgrades || {};
    const base = CONFIG.players.default_kk;
    const levelOf = (key) => Math.min(upgrades[key] || 0, UPGRADE_CATALOG[key].maxLevel);
    return {
        max_hp: base.max_hp + levelOf('resilience') * UPGRADE_CATALOG.resilience.perLevel,
        max_cap: base.max_cap + levelOf('neural_capacity') * UPGRADE_CATALOG.neural_capacity.perLevel,
        recharge_gain: ACTIONS.recharge.gain + levelOf('efficient_recall') * UPGRADE_CATALOG.efficient_recall.perLevel,
        attack_damage: ACTIONS.attack.damage + levelOf('focused_strike') * UPGRADE_CATALOG.focused_strike.perLevel,
        simple_hint_max: SIMPLE_HINT_MAX + levelOf('extra_insight') * UPGRADE_CATALOG.extra_insight.perLevel,
        hard_hint_max: HARD_HINT_MAX + levelOf('deep_insight') * UPGRADE_CATALOG.deep_insight.perLevel,
    };
}

// Scoring (issue #20): server-authoritative so it can't be edited from the
// client, and factored here so the single/multiple-choice grading paths in
// combat-action.js -- which have already drifted once, see the battle-log
// bug in #11 -- share one implementation instead of two that could diverge.
export const VICTORY_BONUS = 250;

// Issue #9's per-tier score multiplier -- Easy 1x / Medium 1.5x / Hard 2x,
// exactly as specified. Questions with no difficulty tag are treated as
// medium everywhere else in the codebase (start-combat.js's pool filter,
// merge_tiered_into_live_data.py), so the same default applies here.
export const DIFFICULTY_MULTIPLIERS = { easy: 1, medium: 1.5, hard: 2 };

export function difficultyMultiplierFor(difficulty) {
    return DIFFICULTY_MULTIPLIERS[difficulty] ?? DIFFICULTY_MULTIPLIERS.medium;
}

// Issue #9's acceptance criterion "selecting a tier with insufficient
// questions is impossible" -- the ticket's own suggested floor.
export const MIN_TIER_QUESTIONS = 15;

export function scoreForAnswer({ isCorrect, priorStreak, hintUsed, difficultyMultiplier = 1 }) {
    if (!isCorrect) {
        return { points: 0, newStreak: 0 };
    }
    const newStreak = priorStreak + 1;
    // +25 per consecutive correct beyond the first, capped at +100 -- a 5+
    // streak (4 "beyond the first") hits the ceiling.
    const streakBonus = Math.min(100, (newStreak - 1) * 25);
    let points = (100 + streakBonus) * difficultyMultiplier;
    if (hintUsed) points *= 0.5;
    return { points: Math.round(points), newStreak };
}

export function hpRemainingBonus(currentHp) {
    return Math.max(0, currentHp);
}

export function shuffle(array) {
    const arr = array.slice();
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}
