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

export function freshPlayer(existingScore) {
    const keeperCfg = CONFIG.players.default_kk;
    return {
        current_hp: keeperCfg.max_hp,
        max_hp: keeperCfg.max_hp,
        current_cap: keeperCfg.max_cap,
        max_cap: keeperCfg.max_cap,
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

export function hintsSummary(hints) {
    return {
        simple_remaining: Math.max(0, SIMPLE_HINT_MAX - hints.simple_used),
        hard_remaining: Math.max(0, HARD_HINT_MAX - hints.hard_used),
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

export function actionCosts() {
    return {
        attack: { cost: ACTIONS.attack.cost, damage: ACTIONS.attack.damage },
        ability: { cost: ACTIONS.ability.cost, damage: ACTIONS.ability.damage },
        recharge: { gain: ACTIONS.recharge.gain },
    };
}

// Scoring (issue #20): server-authoritative so it can't be edited from the
// client, and factored here so the single/multiple-choice grading paths in
// combat-action.js -- which have already drifted once, see the battle-log
// bug in #11 -- share one implementation instead of two that could diverge.
export const VICTORY_BONUS = 250;

// difficultyMultiplier is a hook for issue #9's Easy/Medium/Hard score
// multipliers (1x/1.5x/2x) -- #9 hasn't wired a value in yet, so it stays a
// constant 1 until it does, rather than combat-action.js reimplementing
// scoring when that lands.
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
