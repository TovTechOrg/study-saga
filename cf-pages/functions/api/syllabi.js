import { jsonResponse, DATA, MIN_TIER_QUESTIONS } from '../_lib/game.js';

export async function onRequestGet() {
    const syllabi = (DATA.syllabus || []).map((entry) => {
        const name = entry.name || '';
        const questions = entry.questions || [];
        // Issue #9: per-tier counts so the client can grey out a tier that
        // doesn't meet the floor instead of silently substituting the full
        // pool (start-combat.js's existing fallback) once a player has
        // already committed to a tier.
        const tierCounts = { easy: 0, medium: 0, hard: 0 };
        questions.forEach((q) => {
            const tier = ['easy', 'medium', 'hard'].includes(q.difficulty) ? q.difficulty : 'medium';
            tierCounts[tier] += 1;
        });
        return {
            id: name.toLowerCase(),
            name: name.charAt(0).toUpperCase() + name.slice(1),
            description: `${name.charAt(0).toUpperCase() + name.slice(1)} realm`,
            question_count: questions.length,
            tier_counts: tierCounts,
            min_tier_questions: MIN_TIER_QUESTIONS,
        };
    });

    return jsonResponse({ status: 'success', syllabi });
}
