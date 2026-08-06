import { jsonResponse, freshPlayer, freshEnemy, freshHints, getSession, putSession } from '../_lib/game.js';

export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const incomingGameId = payload.game_id;

    let gameId = incomingGameId;
    let session = incomingGameId ? await getSession(env, incomingGameId) : null;

    if (!session) {
        gameId = crypto.randomUUID();
        session = {};
    }

    session.player = freshPlayer();
    session.enemy_id = 'misconception_golem';
    session.enemy = freshEnemy('misconception_golem');

    delete session.syllabus_id;
    delete session.question_order;
    delete session.q_cursor;
    delete session.asked_indices;
    delete session.pending_q_index;

    session.hints = freshHints();
    session.level_results = [];

    await putSession(env, gameId, session);

    return jsonResponse({
        status: 'success',
        game_id: gameId,
        combat_state: {
            player: session.player,
            enemy: session.enemy,
            syllabus_id: session.syllabus_id || null,
        },
    });
}
