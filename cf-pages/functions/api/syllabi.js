import { jsonResponse, DATA } from '../_lib/game.js';

export async function onRequestGet() {
    const syllabi = (DATA.syllabus || []).map((entry) => {
        const name = entry.name || '';
        return {
            id: name.toLowerCase(),
            name: name.charAt(0).toUpperCase() + name.slice(1),
            description: `${name.charAt(0).toUpperCase() + name.slice(1)} realm`,
            question_count: (entry.questions || []).length,
        };
    });

    return jsonResponse({ status: 'success', syllabi });
}
