import { jsonResponse } from '../_lib/game.js';
import { verifyFirebaseToken } from '../_lib/auth.js';
import { getProfile, putProfile, freshProfile, mergeProfiles } from '../_lib/profile.js';

// Two jobs behind one endpoint (issue #22):
//  1. Fetch the signed-in player's profile -- used when opening the profile
//     panel, and to confirm the same lifetime totals show up on a second
//     device.
//  2. Merge a guest's localStorage profile into it, once, right after
//     sign-in -- pass local_profile to trigger this. Sums totals and takes
//     the max of bests (mergeProfiles in profile.js) rather than the
//     account overwriting a week of guest play.
export async function onRequestPost({ request, env }) {
    const payload = await request.json().catch(() => ({}));
    const auth = await verifyFirebaseToken(payload.id_token);
    if (!auth) {
        return jsonResponse({ status: 'error', message: 'Invalid or missing sign-in' }, 401);
    }

    let profile = (await getProfile(payload.id_token, auth.uid)) || freshProfile(auth.uid);

    if (payload.local_profile) {
        profile = mergeProfiles(profile, payload.local_profile);
        try {
            await putProfile(payload.id_token, auth.uid, profile);
        } catch (e) {
            // A failed write here shouldn't lose the guest data client-side --
            // the caller only clears its local profile after a 'success'
            // response, so an error leaves it intact to retry later.
            return jsonResponse({ status: 'error', message: 'Could not save merged profile' }, 502);
        }
    }

    return jsonResponse({ status: 'success', profile });
}
