import { jsonResponse, freshPlayer, freshEnemy, freshHints, putSession } from '../_lib/game.js';

export async function onRequestPost({ env }) {
    const gameId = crypto.randomUUID();

    const session = {
        player: freshPlayer(),
        enemy_id: 'misconception_golem',
        enemy: freshEnemy('misconception_golem'),
        hints: freshHints(),
        level_results: [],
    };

    await putSession(env, gameId, session);

    return jsonResponse({ status: 'success', game_id: gameId });
}
