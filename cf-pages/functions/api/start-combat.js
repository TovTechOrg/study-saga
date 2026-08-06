import {
    jsonResponse,
    CONFIG,
    freshPlayer,
    freshEnemy,
    freshHints,
    hintsSummary,
    findSyllabus,
    getSession,
    putSession,
    shuffle,
} from '../_lib/game.js';

export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const incomingGameId = payload.game_id;
    const syllabusId = payload.syllabus_id;
    const enemyId = payload.enemy_id || 'misconception_golem';

    const gameId = incomingGameId || crypto.randomUUID();
    let session = await getSession(env, gameId);
    if (!session) {
        session = { player: freshPlayer() };
    }

    session.player = freshPlayer(session.player?.score);
    session.enemy_id = enemyId;
    session.enemy = freshEnemy(enemyId);
    session.syllabus_id = syllabusId;
    session.hints = session.hints || freshHints();
    session.level_results = [];

    const syllabusEntry = findSyllabus(syllabusId);
    const totalQuestions = (syllabusEntry?.questions || []).length;
    const questionOrder = shuffle(Array.from({ length: totalQuestions }, (_, i) => i));
    session.question_order = questionOrder;
    session.q_cursor = 0;
    session.asked_indices = [];

    await putSession(env, gameId, session);

    return jsonResponse({
        status: 'success',
        game_id: gameId,
        combat_state: {
            player: session.player,
            enemy: session.enemy,
            syllabus_id: syllabusId,
        },
        hints: hintsSummary(session.hints),
    });
}
