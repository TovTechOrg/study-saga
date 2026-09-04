import { jsonResponse, findSyllabus, getSession, putSession, shuffle, freshHints, hintsSummary, ACTIONS, actionCosts, scoreForAnswer, VICTORY_BONUS, hpRemainingBonus, difficultyMultiplierFor, questionTimeLimitFor, QUESTION_TIME_GRACE_MS } from '../_lib/game.js';
import { verifyFirebaseToken } from '../_lib/auth.js';
import { getProfile, putProfile, freshProfile, applyRunToProfile } from '../_lib/profile.js';

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
    session.best_streak = session.best_streak || 0;
    session.pending_q_hint_used = session.pending_q_hint_used || false;
    const messages = [];
    let outcome = null;
    let isCorrect = null;
    let canAfford = true;
    let scoreDelta = 0;

    if (action === 'attack' || action === 'ability') {
        const spec = ACTIONS[action];
        const cost = spec.cost;
        // Focused Strike (issue #23) only upgrades Attack's damage, per the
        // catalogue -- Ability's damage is never affected by any upgrade.
        const baseDamage = action === 'attack'
            ? (session.effective_stats?.attack_damage ?? spec.damage)
            : spec.damage;

        if ((player.current_cap || 0) < cost) {
            const combatState = { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(session.effective_stats), streak: session.streak };
            return jsonResponse({
                status: 'error',
                message: 'Not enough CAP -- Recharge to continue.',
                game_id: gameId,
                combat_state: combatState,
                hints: hintsSummary(session.hints, session.effective_stats),
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

            // Answer-position bias fix: the corpus has a severe skew toward
            // the correct option being stored at index 0 (~89% of single-
            // select questions) -- options are shuffled once per question at
            // serve time (below, where sanitizedOpts is built) and the
            // mapping stashed in session.pending_option_order, so payload
            // indices here are positions in the SHUFFLED order the client
            // actually saw. Translate back to original corpus indices before
            // comparing against the answer key, which is keyed to the
            // original, unshuffled question.options.
            const optionOrder = session.pending_option_order || (question.options || []).map((_, i) => i);

            if (questionType === 'multiple_choice_multiple') {
                let correctIndices = new Set(question.answer_indices || []);
                if (correctIndices.size === 0) {
                    (question.options || []).forEach((opt, i) => {
                        if (typeof opt === 'object' && opt !== null && opt.isCorrect) correctIndices.add(i);
                    });
                }
                const answerIndices = new Set((payload.answer_indices || []).map((i) => optionOrder[i]));
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
                const answerIndex = (payload.answer_index !== undefined && payload.answer_index !== null)
                    ? optionOrder[payload.answer_index]
                    : undefined;
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

            // Per-tier question timer (issue #29). Two separate signals here
            // on purpose: noAnswerGiven drives the MESSAGE (the client's
            // auto-submit-on-expiry sends an empty answer, which only ever
            // happens via that path -- a real click always carries a real
            // index), while timedOut is a grace-padded server-side SCORING
            // backstop for a late-but-real answer. Basing the message only on
            // timedOut would rarely show it at all: the client's own auto-
            // submit fires right at the deadline, which is normally still
            // inside the grace window meant to protect real near-the-wire
            // answers from network latency -- so a genuine timeout would
            // silently read as an ordinary wrong answer instead.
            const noAnswerGiven = questionType === 'multiple_choice_multiple'
                ? !(payload.answer_indices || []).length
                : (payload.answer_index === undefined || payload.answer_index === null);
            const timedOut = !!session.pending_q_deadline && Date.now() > session.pending_q_deadline + QUESTION_TIME_GRACE_MS;
            if (timedOut) isCorrect = false;

            player.current_cap = (player.current_cap || 0) - cost;
            const dealt = isCorrect ? baseDamage : 0;
            enemy.current_hp = Math.max(0, (enemy.current_hp || 0) - dealt);
            if (isCorrect) {
                messages.push(`Correct! You used ${spec.label} and dealt ${dealt} damage.`);
            } else if (timedOut || noAnswerGiven) {
                messages.push(`Time's up! ${spec.label} failed to deal damage. The correct answer was: ${correctAnswerText}`);
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
                // Issue #9: Easy 1x / Medium 1.5x / Hard 2x, keyed off the
                // difficulty locked in for this encounter at start-combat time.
                difficultyMultiplier: difficultyMultiplierFor(session.difficulty),
            });
            player.score = (player.score || 0) + scoreResult.points;
            session.streak = scoreResult.newStreak;
            session.best_streak = Math.max(session.best_streak || 0, session.streak);
            session.pending_q_hint_used = false;
            scoreDelta += scoreResult.points;

            if (!askedList.includes(qIndex)) {
                askedList = [...askedList, qIndex];
                session.asked_indices = askedList;
            }
            delete session.pending_q_index;
            qCursor += 1;
            session.q_cursor = qCursor;

            // correctAnswerText and the easy-tier hint are carried on each
            // result (issue #21's "review what you missed") so the run
            // summary can show them without a second request -- the client
            // only ever received the sanitized, answer-free question/options.
            session.level_results.push({
                text: question?.text || '',
                correct: isCorrect,
                correctAnswer: correctAnswerText,
                hint: question?.hints?.easy || '',
            });
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
                const nextOptionOrder = shuffle((nextQuestion.options || []).map((_, i) => i));
                session.pending_option_order = nextOptionOrder;
                const sanitizedOpts = nextOptionOrder.map((origIdx) => ({ text: optText(nextQuestion.options[origIdx]) }));
                const nextQuestionType = nextQuestion.type || 'multiple_choice_single';
                const nextTimeLimitMs = questionTimeLimitFor(nextQuestion.difficulty);
                session.pending_q_deadline = Date.now() + nextTimeLimitMs;
                await putSession(env, gameId, session);
                return jsonResponse({
                    status: 'question',
                    question: { text: nextQuestion.text || '', options: sanitizedOpts, type: nextQuestionType, time_limit_ms: nextTimeLimitMs },
                    game_id: gameId,
                    is_correct: isCorrect,
                    combat_state: { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(session.effective_stats), streak: session.streak },
                    hints: hintsSummary(session.hints, session.effective_stats),
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
            const optionOrder = shuffle((question.options || []).map((_, i) => i));
            session.pending_option_order = optionOrder;
            const sanitizedOpts = optionOrder.map((origIdx) => ({ text: optText(question.options[origIdx]) }));
            const questionType = question.type || 'multiple_choice_single';
            const timeLimitMs = questionTimeLimitFor(question.difficulty);
            session.pending_q_deadline = Date.now() + timeLimitMs;
            await putSession(env, gameId, session);
            return jsonResponse({
                status: 'question',
                question: { text: question.text || '', options: sanitizedOpts, type: questionType, time_limit_ms: timeLimitMs },
                game_id: gameId,
                combat_state: { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(session.effective_stats), streak: session.streak },
                hints: hintsSummary(session.hints, session.effective_stats),
                score: player.score || 0,
                score_delta: 0,
                streak: session.streak,
            }, 200);
        }
    } else if (action === 'recharge') {
        const gain = session.effective_stats?.recharge_gain ?? ACTIONS.recharge.gain;
        const before = player.current_cap || 0;
        const maxC = player.max_cap || 10;
        player.current_cap = Math.min(maxC, before + gain);
        messages.push(`You recharged +${player.current_cap - before} CAP.`);
    } else {
        return jsonResponse({ status: 'error', message: 'Unknown action' }, 400);
    }

    await putSession(env, gameId, session);

    const combatState = { player, enemy, syllabus_id: session.syllabus_id || null, difficulty: session.difficulty || 'medium', action_costs: actionCosts(session.effective_stats), streak: session.streak };

    // Run summary (issue #21): computed here, once, at the same point
    // level_results is already finalized -- extends the existing end-of-run
    // payload rather than requiring a second request for it.
    let runSummary;
    if (outcome) {
        const total = session.level_results.length;
        const correctCount = session.level_results.filter((r) => r.correct).length;
        runSummary = {
            score: player.score || 0,
            accuracy: total > 0 ? correctCount / total : 0,
            correct_count: correctCount,
            total_questions: total,
            best_streak: session.best_streak || 0,
            xp_earned: Math.floor((player.score || 0) / 10),
            hints_used: (session.hints.simple_used || 0) + (session.hints.hard_used || 0),
            hp_remaining: outcome === 'victory' ? (player.current_hp || 0) : 0,
            difficulty: session.difficulty || 'medium',
        };

        // Persistent profile (issue #22): written exactly once, here, at run
        // end -- not per answer, which would be a Firestore write per
        // question per player for no benefit. XP/score always come from
        // runSummary (this session's own server-computed state), never from
        // the request body, so a client can't post an arbitrary XP total.
        // Guests (no session.uid) accumulate the same data client-side in
        // localStorage instead -- see applyRunToProfile's mirror in
        // game-simple.js.
        if (session.uid && payload.id_token) {
            try {
                const auth = await verifyFirebaseToken(payload.id_token);
                if (auth && auth.uid === session.uid) {
                    const profile = (await getProfile(payload.id_token, auth.uid)) || freshProfile(auth.uid);
                    applyRunToProfile(profile, {
                        realm: session.syllabus_id || 'unknown',
                        difficulty: runSummary.difficulty,
                        score: runSummary.score,
                        accuracy: runSummary.accuracy,
                        correct_count: runSummary.correct_count,
                        total_questions: runSummary.total_questions,
                        best_streak: runSummary.best_streak,
                        xp_earned: runSummary.xp_earned,
                        outcome,
                        finished_at: new Date().toISOString(),
                    });
                    await putProfile(payload.id_token, auth.uid, profile);
                }
            } catch (e) {
                // A Firestore write failure must not break the run's own
                // response -- the player still sees their summary either way.
            }
        }
    }

    return jsonResponse({
        status: 'success',
        game_id: gameId,
        is_correct: isCorrect,
        combat_state: combatState,
        hints: hintsSummary(session.hints, session.effective_stats),
        messages,
        outcome,
        level_results: outcome ? session.level_results : undefined,
        run_summary: runSummary,
        score: player.score || 0,
        score_delta: scoreDelta,
        streak: session.streak,
    });
}
