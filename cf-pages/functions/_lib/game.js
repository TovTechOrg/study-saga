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

export function shuffle(array) {
    const arr = array.slice();
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}
