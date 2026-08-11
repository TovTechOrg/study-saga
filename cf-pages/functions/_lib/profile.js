// Persistent per-user profile in the USER_PROFILES KV namespace, keyed by
// Firebase UID -- mirrors the getSession/putSession pattern in game.js.
// Deliberately minimal for now (just enough to resume a game on another
// device); the points/gacha/upgrades economy discussed separately this
// session is an intentionally deferred, larger feature, not part of this.

export function freshProfile(uid) {
    return { uid, active_game_id: null };
}

export async function getProfile(env, uid) {
    if (!uid) return null;
    const raw = await env.USER_PROFILES.get(uid);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

export async function putProfile(env, uid, profile) {
    await env.USER_PROFILES.put(uid, JSON.stringify(profile));
}
