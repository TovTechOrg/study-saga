import { jsonResponse, freshPlayer, freshEnemy, freshHints, putSession } from '../_lib/game.js';
import { verifyFirebaseToken } from '../_lib/auth.js';
import { getProfile, putProfile, freshProfile } from '../_lib/profile.js';

export async function onRequestPost({ request, env }) {
    const gameId = crypto.randomUUID();
    const payload = await request.json().catch(() => ({}));

    const session = {
        player: freshPlayer(),
        enemy_id: 'misconception_golem',
        enemy: freshEnemy('misconception_golem'),
        hints: freshHints(),
        level_results: [],
    };

    // Signing in is optional -- guests (no/invalid token) get exactly
    // today's behavior. A verified token links this new game to the
    // player's account so it can be resumed on another device.
    const auth = await verifyFirebaseToken(payload.id_token);
    if (auth) {
        session.uid = auth.uid;
        const profile = (await getProfile(env, auth.uid)) || freshProfile(auth.uid);
        profile.active_game_id = gameId;
        await putProfile(env, auth.uid, profile);
    }

    await putSession(env, gameId, session);

    return jsonResponse({ status: 'success', game_id: gameId });
}
