import { jsonResponse, UPGRADE_CATALOG, MAX_TOTAL_UPGRADE_LEVELS, costForNextLevel, totalUpgradeLevels } from '../_lib/game.js';
import { verifyFirebaseToken } from '../_lib/auth.js';
import { getProfile, putProfile, freshProfile } from '../_lib/profile.js';

// Server-validated upgrade purchase (issue #23) for signed-in players --
// guests spend against their own localStorage balance client-side (there's
// no server-side account to validate against for a guest; consistent with
// the existing guest-profile trust model). Cost, current level, and the
// total-level cap are all re-read from the player's own stored profile here,
// never trusted from the request, so a client can't grant itself an upgrade
// or spend XP it doesn't have.
export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const auth = await verifyFirebaseToken(payload.id_token);
    if (!auth) {
        return jsonResponse({ status: 'error', message: 'Invalid or missing sign-in' }, 401);
    }

    const upgradeKey = payload.upgrade_key;
    if (!UPGRADE_CATALOG[upgradeKey]) {
        return jsonResponse({ status: 'error', message: 'Unknown upgrade' }, 400);
    }

    const profile = (await getProfile(payload.id_token, auth.uid)) || freshProfile(auth.uid);
    profile.upgrades = profile.upgrades || {};
    const currentLevel = profile.upgrades[upgradeKey] || 0;
    const cost = costForNextLevel(upgradeKey, currentLevel);

    if (cost === null) {
        return jsonResponse({ status: 'error', message: 'This upgrade is already at its max level.' }, 400);
    }
    if (totalUpgradeLevels(profile.upgrades) >= MAX_TOTAL_UPGRADE_LEVELS) {
        return jsonResponse({ status: 'error', message: `Total upgrade levels are capped at ${MAX_TOTAL_UPGRADE_LEVELS} for now.` }, 400);
    }
    if ((profile.xp_balance || 0) < cost) {
        return jsonResponse({ status: 'error', message: 'Not enough XP for this upgrade.' }, 400);
    }

    // Both halves of the purchase are applied to the same in-memory object
    // before the one PATCH write below -- a failed write leaves the old,
    // untouched profile in Firestore (never XP spent without the level
    // gained, or vice versa); a successful write commits both together.
    profile.xp_balance -= cost;
    profile.upgrades[upgradeKey] = currentLevel + 1;

    try {
        await putProfile(payload.id_token, auth.uid, profile);
    } catch (e) {
        return jsonResponse({ status: 'error', message: 'Could not save your purchase. Please try again.' }, 502);
    }

    return jsonResponse({ status: 'success', profile });
}
