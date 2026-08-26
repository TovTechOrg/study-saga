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
    actionCosts,
} from '../_lib/game.js';

export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const incomingGameId = payload.game_id;
    const syllabusId = payload.syllabus_id;
    const enemyId = payload.enemy_id || 'misconception_golem';
    // Chosen once per realm-entry, locked for the whole battle (not a
    // per-turn toggle). Questions with no difficulty tag are the original,
    // pre-tiered content -- treated as "medium" so they stay reachable
    // rather than becoming permanently unreachable once this filter exists.
    const difficulty = ['easy', 'medium', 'hard'].includes(payload.difficulty) ? payload.difficulty : 'medium';

    const gameId = incomingGameId || crypto.randomUUID();
    let session = await getSession(env, gameId);
    if (!session) {
        session = { player: freshPlayer() };
    }

    // Score (issue #20) is deliberately carried forward across encounters
    // within a session -- it's a running session score, not a per-battle
    // one -- via freshPlayer(existingScore). Streak is the opposite choice:
    // it resets with every new encounter, same as HP/CAP/enemy state, since
    // a "streak" is meant to reflect this battle's run of correct answers,
    // not one inherited from a fight that already ended.
    session.player = freshPlayer(session.player?.score);
    session.streak = 0;
    session.best_streak = 0;
    session.pending_q_hint_used = false;
    session.enemy_id = enemyId;
    session.enemy = freshEnemy(enemyId);
    session.syllabus_id = syllabusId;
    session.difficulty = difficulty;
    session.hints = session.hints || freshHints();
    session.level_results = [];

    const syllabusEntry = findSyllabus(syllabusId);
    const allQuestions = syllabusEntry?.questions || [];
    const matchingIndices = allQuestions
        .map((q, i) => ((q.difficulty || 'medium') === difficulty ? i : null))
        .filter((i) => i !== null);
    // Safety net: a subject/difficulty combo with zero matches (shouldn't
    // happen post-merge, but don't leave a player with no questions at all
    // if it ever does) falls back to the full, unfiltered pool.
    const poolIndices = matchingIndices.length > 0 ? matchingIndices : Array.from({ length: allQuestions.length }, (_, i) => i);
    const questionOrder = shuffle(poolIndices);
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
            difficulty,
            action_costs: actionCosts(),
            streak: session.streak,
        },
        hints: hintsSummary(session.hints),
        score: session.player.score || 0,
        score_delta: 0,
        streak: session.streak,
    });
}
