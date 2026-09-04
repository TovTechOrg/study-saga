import {
    jsonResponse,
    DATA,
    getSession,
    putSession,
    freshHints,
    hintsSummary,
    SIMPLE_HINT_MAX,
    HARD_HINT_MAX,
} from '../_lib/game.js';

function findPreGeneratedHint(question) {
    const target = question.trim().toLowerCase();
    for (const syllabus of DATA.syllabus || []) {
        for (const q of syllabus.questions || []) {
            const qText = (q.text || q.question || '').trim().toLowerCase();
            if (qText === target) {
                return { options: q.options || null, hints: q.hints || null };
            }
        }
    }
    return { options: null, hints: null };
}

// Answer-leak scrubber ported from rag_pipeline.get_safe_hint, masking-only
// (no LLM rephrase call) -- this fallback path is rarely hit since all 800
// bundled questions already have pre-generated, audited hints in data.json.
function maskLeakedAnswers(hint, answersStr) {
    let cleaned = hint.replace(/\[REDACTED\]/gi, 'these components');
    const hintLower = cleaned.toLowerCase();
    const leaked = new Set();
    const glueWords = new Set(['the', 'and', 'ion', 'cell', 'acid', 'base', 'gas', 'data']);

    for (let ans of answersStr.split(', ')) {
        ans = ans.trim().toLowerCase();
        if (!ans) continue;
        const isNumeric = /^\d+(\.\d+)?$/.test(ans);
        if (ans.length < 3 && !isNumeric) continue;
        if (hintLower.includes(ans)) leaked.add(ans);

        const words = (ans.match(/\w+/g) || []).filter((w) => w.length > 4 && !glueWords.has(w));
        for (const word of words) {
            let pattern;
            if (word.endsWith('ies') && word.length > 4) {
                const stem = word.slice(0, -3);
                pattern = new RegExp(`\\b${stem}(y|ies)\\b`, 'i');
            } else if (word.endsWith('s') && !word.endsWith('ss') && word.length > 4) {
                const stem = word.slice(0, -1);
                pattern = new RegExp(`\\b${stem}s?\\b`, 'i');
            } else {
                pattern = new RegExp(`\\b${word}s?\\b`, 'i');
            }
            if (pattern.test(hintLower)) leaked.add(word);
        }
    }

    if (leaked.size === 0) return cleaned;

    for (const term of leaked) {
        const pattern = new RegExp(`\\b${term}s?\\b`, 'gi');
        cleaned = cleaned.replace(pattern, '[concept]');
    }
    return cleaned;
}

async function callGroq(apiKey, messages, maxTokens, temperature) {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            model: 'llama-3.3-70b-versatile',
            messages,
            max_tokens: maxTokens,
            temperature,
            response_format: { type: 'json_object' },
        }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    try {
        return JSON.parse(data.choices[0].message.content);
    } catch (e) {
        return null;
    }
}

async function generateHintGroq(question, options, apiKey) {
    const answersList = [];
    for (const opt of options) {
        if (typeof opt === 'object' && opt !== null && (opt.is_answer || opt.isCorrect)) {
            answersList.push(opt.text);
        } else if (typeof opt === 'string' && answersList.length === 0) {
            answersList.push(opt);
        }
    }
    const targetAnswers = answersList.join(', ');

    const prompt = `You are a Trivia Game Master. Your goal is to guide the player to the Target Answers "${targetAnswers}" using hints appropriate to the question type.

### GUIDELINES:
- NO LEAKAGE: Never use the target words "${targetAnswers}" or their obvious roots.
- Use plain, precise language over elaborate metaphor. For conceptual/science answers, describe the real mechanism accurately. For numeric/computational answers, never use science metaphors -- use grounded physicality (balance scales, slicing, distance/time) instead, and never spell out the arithmetic steps.
- DIFFICULTY CALIBRATION: Hard should require real thought but not be a giveaway; Medium describes structure/prose; Easy is a Socratic question about the first step, never the final answer.

Question: ${question}

Return EXACTLY 3 hints as a JSON object. Each value must be a plain string.
{"hard": "...", "medium": "...", "easy": "..."}`;

    const hints = await callGroq(
        apiKey,
        [
            { role: 'system', content: 'You are a Trivia Game Master.' },
            { role: 'user', content: prompt },
        ],
        300,
        0.7
    );

    if (!hints) {
        return JSON.stringify({ hard: 'Connection failed', medium: 'AI API error', easy: 'No hint available' });
    }

    const sanitized = {};
    for (const [k, v] of Object.entries(hints)) {
        sanitized[k] = maskLeakedAnswers(typeof v === 'string' ? v : String(v), targetAnswers);
    }
    return JSON.stringify(sanitized);
}

export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const question = payload.question || '';
    const options = Array.isArray(payload.options) ? payload.options : [];
    const gameId = payload.game_id;
    const tier = payload.tier === 'hard' ? 'hard' : 'simple';

    if (!question || !Array.isArray(options)) {
        return jsonResponse({ status: 'error', message: 'Missing question or options' }, 400);
    }

    // Per-game hint budget: 3 simple (easy-tier) + 1 hard (full tier) reveal by
    // default; earned credits (from correct answers / victories) unlock more
    // of either. Only enforced when a game_id resolves to a real session --
    // legacy/no-session calls fall back to ungated behavior.
    let session = null;
    if (gameId) {
        session = await getSession(env, gameId);
        if (session) {
            session.hints = session.hints || freshHints();
            const h = session.hints;
            const usedKey = tier === 'hard' ? 'hard_used' : 'simple_used';
            // Issue #23: Extra/Deep Insight upgrades raise these per-run
            // budgets -- session.effective_stats (resolved once at
            // start-combat time from the player's purchased levels) takes
            // priority over the base-config module constants.
            const maxAllowed = tier === 'hard'
                ? (session.effective_stats?.hard_hint_max ?? HARD_HINT_MAX)
                : (session.effective_stats?.simple_hint_max ?? SIMPLE_HINT_MAX);

            if (h[usedKey] < maxAllowed) {
                h[usedKey] += 1;
            } else if (h.credits > 0) {
                h.credits -= 1;
            } else {
                // Marked below (session.pending_q_hint_used) only on the
                // paths that actually grant a hint -- this blocked path
                // must not halve a question's score for a hint the player
                // never received.
                await putSession(env, gameId, session);
                return jsonResponse({
                    status: 'blocked',
                    message: tier === 'hard'
                        ? 'No deep hints left this game. Answer questions correctly to earn credits.'
                        : 'No simple hints left this game. Answer questions correctly to earn credits.',
                    hints: hintsSummary(h, session.effective_stats),
                });
            }
            // Issue #20: a hint actually granted on the currently pending
            // question halves that question's score once it's graded in
            // combat-action.js. Reset back to false there after grading, so
            // this only ever reflects the question in progress right now.
            session.pending_q_hint_used = true;
            await putSession(env, gameId, session);
        }
    }

    const { options: dbOptions, hints: dbHints } = findPreGeneratedHint(question);
    const optionsToPass = dbOptions || options;

    let hintObj;
    if (dbHints) {
        hintObj = dbHints;
    } else {
        const groqKey = env.GROQ_API_KEY;
        if (!groqKey) {
            hintObj = { hard: 'No hint available (backend error).', medium: '', easy: 'No hint available (backend error).' };
        } else {
            try {
                hintObj = JSON.parse(await generateHintGroq(question, optionsToPass, groqKey));
            } catch (e) {
                hintObj = { hard: 'No hint available (backend error).', medium: '', easy: 'No hint available (backend error).' };
            }
        }
    }

    const scopedHint = tier === 'hard'
        ? { hard: hintObj.hard, medium: hintObj.medium, easy: hintObj.easy }
        : { easy: hintObj.easy };

    return jsonResponse({
        status: 'success',
        hint: scopedHint,
        hints: session ? hintsSummary(session.hints, session.effective_stats) : undefined,
    });
}
