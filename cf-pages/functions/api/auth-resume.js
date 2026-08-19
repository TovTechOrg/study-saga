import { jsonResponse, getSession, hintsSummary } from '../_lib/game.js';
import { verifyFirebaseToken } from '../_lib/auth.js';
import { getProfile } from '../_lib/profile.js';

// Given a verified sign-in, looks up the player's last active game (if any)
// and returns its live state so the frontend can resume directly on a new
// device instead of starting fresh.
export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const auth = await verifyFirebaseToken(payload.id_token);
    if (!auth) {
        return jsonResponse({ status: 'error', message: 'Invalid or missing sign-in' }, 401);
    }

    const profile = await getProfile(payload.id_token, auth.uid);
    if (!profile || !profile.active_game_id) {
        return jsonResponse({ status: 'no_active_game' });
    }

    const session = await getSession(env, profile.active_game_id);
    if (!session) {
        return jsonResponse({ status: 'no_active_game' });
    }

    return jsonResponse({
        status: 'resumed',
        game_id: profile.active_game_id,
        combat_state: {
            player: session.player,
            enemy: session.enemy,
            syllabus_id: session.syllabus_id || null,
        },
        hints: hintsSummary(session.hints),
    });
}
