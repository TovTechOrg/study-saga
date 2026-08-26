import { jsonResponse, findSyllabus, getSession, putSession, shuffle, freshHints, hintsSummary, ACTIONS, actionCosts, scoreForAnswer, VICTORY_BONUS, hpRemainingBonus } from '../_lib/game.js';

function optText(opt) {
    return typeof opt === 'object' && opt !== null ? opt.text : String(opt);
}

export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const gameId = payload.game_id;
    const action = payload.action;

    if (!gameId) {
        return jsonResponse({ status: 'error', message: 'Missing game_id' }, 400);
    }

    const session = await getSession(env, gameId);
    if (!session) {
        return jsonResponse({ status: 'error', message: 'Invalid game session' }, 404);
    }

    const player = session.player || {};
    const enemy = session.enemy || {};
    session.hints = session.hints || freshHints();
    session.level_results = session.level_results || [];
    // Streak and per-question hint usage live on the session (issue #20), not
    // the client -- a client-computed score is a client-editable score.
    session.streak = session.streak || 0;
    session.pending_q_hint_used = session.pending_q_hint_used || false;
    const messages = [];
    let outcome = null;
    let isCorrect = null;
    let canAfford = true;
    let scoreDelta = 0;

    if (action === 'attack' || action === 'ability') {
        const spec = ACTIONS[action];
        const cost = spec.cost;
        const baseDamage = spec.damage;

        if ((player.current_cap || 0) < cost) {
            const combatState = { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(), streak: session.streak };
            return jsonResponse({
                status: 'error',
                message: 'Not enough CAP -- Recharge to continue.',
                game_id: gameId,
                combat_state: combatState,
                hints: hintsSummary(session.hints),
                score: player.score || 0,
                score_delta: 0,
                streak: session.streak,
            }, 200);
        }

        const syllabusEntry = findSyllabus(session.syllabus_id);
        const questions = syllabusEntry?.questions || [];
        let questionOrder = session.question_order || Array.from({ length: questions.length }, (_, i) => i);
        let qCursor = session.q_cursor || 0;
        let askedList = session.asked_indices || [];
        const answerSubmitted = ('answer_index' in payload) || ('answer_indices' in payload);

        let returnedEarly = false;

        if (session.pending_q_index !== undefined && session.pending_q_index !== null && answerSubmitted) {
            const qIndex = session.pending_q_index;
            const question = questions[qIndex];
            const questionType = question?.type || 'multiple_choice_single';
            let correctAnswerText = '';
            let selectedFeedback = '';

            if (questionType === 'multiple_choice_multiple') {
                let correctIndices = new Set(question.answer_indices || []);
                if (correctIndices.size === 0) {
                    (question.options || []).forEach((opt, i) => {
                        if (typeof opt === 'object' && opt !== null && opt.isCorrect) correctIndices.add(i);
                    });
                }
                const answerIndices = new Set(payload.answer_indices || []);
                isCorrect = answerIndices.size === correctIndices.size &&
                    [...answerIndices].every((i) => correctIndices.has(i));
                const opts = question.options || [];
                correctAnswerText = opts
                    .map((opt, i) => (correctIndices.has(i) ? optText(opt) : null))
                    .filter((t) => t !== null)
                    .join(', ');
            } else {
                let correctIdx = question?.answer_index;
                if (correctIdx === undefined || correctIdx === null) {
                    correctIdx = null;
                    (question.options || []).forEach((opt, i) => {
                        if (correctIdx === null && typeof opt === 'object' && opt !== null && opt.isCorrect) correctIdx = i;
                    });
                    if (correctIdx === null) correctIdx = 0;
                }
                const answerIndex = payload.answer_index;
                isCorrect = answerIndex === correctIdx;
                const opts = question.options || [];
                if (correctIdx < opts.length) {
                    correctAnswerText = optText(opts[correctIdx]);
                }
                if (answerIndex !== undefined && answerIndex !== null && answerIndex < opts.length) {
                    const selOpt = opts[answerIndex];
                    selectedFeedback = (typeof selOpt === 'object' && selOpt !== null) ? (selOpt.feedback || '') : '';
                }
            }

            player.current_cap = (player.current_cap || 0) - cost;
            const dealt = isCorrect ? baseDamage : 0;
            enemy.current_hp = Math.max(0, (enemy.current_hp || 0) - dealt);
            if (isCorrect) {
                messages.push(`Correct! You used ${spec.label} and dealt ${dealt} damage.`);
            } else {
                messages.push(`Incorrect. ${spec.label} failed to deal damage. The correct answer was: ${correctAnswerText}`);
            }
            if (selectedFeedback) messages.push(selectedFeedback);

            // Scoring (issue #20): +100 for a correct answer, a streak bonus
            // capped at +100, halved if a hint was used on this question.
            // Computed here -- the one place both single- and multi-select
            // answers already share for grading -- so the two paths can't
            // drift the way the pre-#11 battle log did.
            const hintUsedThisQuestion = session.pending_q_hint_used;
            const scoreResult = scoreForAnswer({
                isCorrect,
                priorStreak: session.streak,
                hintUsed: hintUsedThisQuestion,
            });
            player.score = (player.score || 0) + scoreResult.points;
            session.streak = scoreResult.newStreak;
            session.pending_q_hint_used = false;
            scoreDelta += scoreResult.points;

            if (!askedList.includes(qIndex)) {
                askedList = [...askedList, qIndex];
                session.asked_indices = askedList;
            }
            delete session.pending_q_index;
            qCursor += 1;
            session.q_cursor = qCursor;

            session.level_results.push({ text: question?.text || '', correct: isCorrect });
            if (isCorrect) session.hints.credits += 1;

            if (enemy.current_hp <= 0) {
                outcome = 'victory';
                session.hints.credits += 2;
                const victoryBonus = VICTORY_BONUS + hpRemainingBonus(player.current_hp);
                player.score += victoryBonus;
                scoreDelta += victoryBonus;
            } else {
                const maxResolve = enemy.max_resolve || 100;
                let resolve = enemy.resolve ?? 50;
                resolve = isCorrect ? Math.max(0, resolve - 18) : Math.min(maxResolve, resolve + 14);
                enemy.resolve = resolve;

                const enemyName = enemy.name || 'Enemy';
                const baseAttack = enemy.attack_power || 12;
                if (resolve <= 15 && Math.random() < 0.35) {
                    messages.push(`${enemyName} hesitates, rattled by your streak -- no counterattack!`);
                } else {
                    const multiplier = 0.5 + resolve / maxResolve;
                    let counter = Math.max(1, Math.round(baseAttack * multiplier));
                    if (resolve >= 85 && Math.random() < 0.35) {
                        counter = Math.round(counter * 1.4);
                        messages.push(`${enemyName} grows emboldened and strikes back hard for ${counter} damage!`);
                    } else {
                        messages.push(`${enemyName} countered for ${counter} damage.`);
                    }
                    player.current_hp = Math.max(0, (player.current_hp || 0) - counter);
                    if (player.current_hp <= 0) outcome = 'defeat';
                }
            }

            if (qCursor >= questionOrder.length) {
                questionOrder = shuffle(questionOrder);
                session.question_order = questionOrder;
                qCursor = 0;
                session.q_cursor = qCursor;
            }

            if (outcome === null && (session.pending_q_index === undefined || session.pending_q_index === null)) {
                const recheckCost = ACTIONS[action].cost;
                if ((player.current_cap || 0) < recheckCost) {
                    canAfford = false;
                    messages.push(`Not enough CAP for ${action} -- Recharge to continue.`);
                }
            }

            if (outcome === null && canAfford) {
                const nextQIndex = questionOrder[qCursor];
                session.pending_q_index = nextQIndex;
                const nextQuestion = questions[nextQIndex];
                const sanitizedOpts = (nextQuestion.options || []).map((opt) => ({ text: optText(opt) }));
                const nextQuestionType = nextQuestion.type || 'multiple_choice_single';
                await putSession(env, gameId, session);
                return jsonResponse({
                    status: 'question',
                    question: { text: nextQuestion.text || '', options: sanitizedOpts, type: nextQuestionType },
                    game_id: gameId,
                    is_correct: isCorrect,
                    combat_state: { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(), streak: session.streak },
                    hints: hintsSummary(session.hints),
                    messages,
                    outcome,
                    score: player.score,
                    score_delta: scoreDelta,
                    streak: session.streak,
                }, 200);
            }
        } else {
            if (qCursor >= questionOrder.length) {
                questionOrder = shuffle(questionOrder);
                session.question_order = questionOrder;
                qCursor = 0;
                session.q_cursor = qCursor;
            }
            const qIndex = questionOrder[qCursor];
            session.pending_q_index = qIndex;
            const question = questions[qIndex];
            const sanitizedOpts = (question.options || []).map((opt) => ({ text: optText(opt) }));
            const questionType = question.type || 'multiple_choice_single';
            await putSession(env, gameId, session);
            return jsonResponse({
                status: 'question',
                question: { text: question.text || '', options: sanitizedOpts, type: questionType },
                game_id: gameId,
                combat_state: { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(), streak: session.streak },
                hints: hintsSummary(session.hints),
                score: player.score || 0,
                score_delta: 0,
                streak: session.streak,
            }, 200);
        }
    } else if (action === 'recharge') {
        const gain = ACTIONS.recharge.gain;
        const before = player.current_cap || 0;
        const maxC = player.max_cap || 10;
        player.current_cap = Math.min(maxC, before + gain);
        messages.push(`You recharged +${player.current_cap - before} CAP.`);
    } else {
        return jsonResponse({ status: 'error', message: 'Unknown action' }, 400);
    }

    await putSession(env, gameId, session);

    const combatState = { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(), streak: session.streak };

    return jsonResponse({
        status: 'success',
        game_id: gameId,
        is_correct: isCorrect,
        combat_state: combatState,
        hints: hintsSummary(session.hints),
        messages,
        outcome,
        level_results: outcome ? session.level_results : undefined,
        score: player.score || 0,
        score_delta: scoreDelta,
        streak: session.streak,
    });
}
