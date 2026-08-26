// Persistent per-user profile in Firestore, keyed by Firebase UID.
//
// Uses Firestore's REST API directly with the caller's own Firebase Auth ID
// token as the Bearer credential -- no service account/Admin SDK needed.
// Firestore's security rules (see FIRESTORE_RULES below) enforce that a
// token can only read/write the document matching its own uid.

const FIREBASE_PROJECT_ID = 'study-saga-live';
const FIRESTORE_BASE = `https://firestore.googleapis.com/v1/projects/${FIREBASE_PROJECT_ID}/databases/(default)/documents/user_profiles`;

export const RECENT_RUNS_MAX = 10;

// Realm records are keyed by realm name (issue #22) so #9's difficulty
// tiers can nest under them later -- e.g. realms.biology.hard.best_score --
// without a schema migration. Do not add the tier level yet; just leave the
// shape able to hold it.
export function freshRealmRecord() {
    return { best_score: 0, runs: 0, questions_correct: 0, questions_answered: 0, best_streak: 0 };
}

export function freshProfile(uid) {
    return {
        uid,
        active_game_id: null,
        lifetime_xp: 0,
        xp_balance: 0,
        totals: { runs: 0, questions_answered: 0, questions_correct: 0 },
        realms: {},
        recent_runs: [],
    };
}

// Applies one finished run to a profile object in place and returns it.
// `run` is { realm, score, accuracy, correct_count, total_questions,
// best_streak, xp_earned, outcome, finished_at }. Pure data manipulation, no
// I/O -- used identically for the Firestore-backed path here and mirrored in
// game-simple.js for the guest/localStorage path (there is no shared module
// system between Pages Functions and the unbundled static frontend, so the
// two copies must be kept in sync by hand; this is the source of truth,
// comment cross-references it from the other side).
export function applyRunToProfile(profile, run) {
    profile.lifetime_xp = (profile.lifetime_xp || 0) + (run.xp_earned || 0);
    profile.xp_balance = (profile.xp_balance || 0) + (run.xp_earned || 0);

    profile.totals = profile.totals || { runs: 0, questions_answered: 0, questions_correct: 0 };
    profile.totals.runs = (profile.totals.runs || 0) + 1;
    profile.totals.questions_answered = (profile.totals.questions_answered || 0) + (run.total_questions || 0);
    profile.totals.questions_correct = (profile.totals.questions_correct || 0) + (run.correct_count || 0);

    profile.realms = profile.realms || {};
    const realmKey = run.realm || 'unknown';
    const realm = profile.realms[realmKey] || freshRealmRecord();
    realm.best_score = Math.max(realm.best_score || 0, run.score || 0);
    realm.runs = (realm.runs || 0) + 1;
    realm.questions_correct = (realm.questions_correct || 0) + (run.correct_count || 0);
    realm.questions_answered = (realm.questions_answered || 0) + (run.total_questions || 0);
    realm.best_streak = Math.max(realm.best_streak || 0, run.best_streak || 0);
    profile.realms[realmKey] = realm;

    profile.recent_runs = [
        {
            realm: realmKey,
            score: run.score || 0,
            accuracy: run.accuracy || 0,
            xp_earned: run.xp_earned || 0,
            outcome: run.outcome,
            finished_at: run.finished_at,
        },
        ...(profile.recent_runs || []),
    ].slice(0, RECENT_RUNS_MAX);

    return profile;
}

// Guest-to-account merge on first sign-in (issue #22): sums totals, takes
// the max of bests, and merges recent_runs by recency rather than the
// account overwriting a week of guest play. `remote` may be null (brand new
// account); `local` may be null (nothing to merge, e.g. every sign-in after
// the first).
export function mergeProfiles(remote, local) {
    if (!local) return remote;
    if (!remote) return local;

    const merged = {
        uid: remote.uid,
        active_game_id: remote.active_game_id,
        lifetime_xp: (remote.lifetime_xp || 0) + (local.lifetime_xp || 0),
        xp_balance: (remote.xp_balance || 0) + (local.xp_balance || 0),
        totals: {
            runs: (remote.totals?.runs || 0) + (local.totals?.runs || 0),
            questions_answered: (remote.totals?.questions_answered || 0) + (local.totals?.questions_answered || 0),
            questions_correct: (remote.totals?.questions_correct || 0) + (local.totals?.questions_correct || 0),
        },
        realms: {},
        recent_runs: [...(local.recent_runs || []), ...(remote.recent_runs || [])]
            .sort((a, b) => String(b.finished_at || '').localeCompare(String(a.finished_at || '')))
            .slice(0, RECENT_RUNS_MAX),
    };

    const realmKeys = new Set([...Object.keys(remote.realms || {}), ...Object.keys(local.realms || {})]);
    for (const key of realmKeys) {
        const r = remote.realms?.[key] || freshRealmRecord();
        const l = local.realms?.[key] || freshRealmRecord();
        merged.realms[key] = {
            best_score: Math.max(r.best_score || 0, l.best_score || 0),
            runs: (r.runs || 0) + (l.runs || 0),
            questions_correct: (r.questions_correct || 0) + (l.questions_correct || 0),
            questions_answered: (r.questions_answered || 0) + (l.questions_answered || 0),
            best_streak: Math.max(r.best_streak || 0, l.best_streak || 0),
        };
    }

    return merged;
}

// Firestore REST documents use typed field values, e.g. {stringValue: "x"}
// or {mapValue: {fields: {...}}}. Generic/recursive rather than hand-mapping
// each field -- the profile schema nests objects (totals, realms, each
// realm's record) and arrays (recent_runs), and a generic converter means
// #9's difficulty tiers (or any future nesting) round-trips correctly
// without touching this file again.
function toFirestoreValue(value) {
    if (value === null || value === undefined) return { nullValue: null };
    if (typeof value === 'string') return { stringValue: value };
    if (typeof value === 'boolean') return { booleanValue: value };
    if (typeof value === 'number') {
        return Number.isInteger(value) ? { integerValue: String(value) } : { doubleValue: value };
    }
    if (Array.isArray(value)) {
        return { arrayValue: { values: value.map(toFirestoreValue) } };
    }
    if (typeof value === 'object') {
        return { mapValue: { fields: toFirestoreFields(value) } };
    }
    return { nullValue: null };
}

function toFirestoreFields(obj) {
    const fields = {};
    for (const [key, value] of Object.entries(obj || {})) {
        fields[key] = toFirestoreValue(value);
    }
    return fields;
}

function fromFirestoreValue(value) {
    if (!value) return null;
    if ('stringValue' in value) return value.stringValue;
    if ('integerValue' in value) return parseInt(value.integerValue, 10);
    if ('doubleValue' in value) return value.doubleValue;
    if ('booleanValue' in value) return value.booleanValue;
    if ('nullValue' in value) return null;
    if ('arrayValue' in value) return (value.arrayValue.values || []).map(fromFirestoreValue);
    if ('mapValue' in value) return fromFirestoreFields(value.mapValue.fields || {});
    return null;
}

function fromFirestoreFields(fields) {
    const obj = {};
    for (const [key, value] of Object.entries(fields || {})) {
        obj[key] = fromFirestoreValue(value);
    }
    return obj;
}

export async function getProfile(idToken, uid) {
    if (!idToken || !uid) return null;
    const res = await fetch(`${FIRESTORE_BASE}/${uid}`, {
        headers: { Authorization: `Bearer ${idToken}` },
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    const doc = await res.json();
    if (!doc.fields) return null;
    return fromFirestoreFields(doc.fields);
}

export async function putProfile(idToken, uid, profile) {
    if (!idToken || !uid) return;
    await fetch(`${FIRESTORE_BASE}/${uid}`, {
        method: 'PATCH',
        headers: {
            Authorization: `Bearer ${idToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fields: toFirestoreFields(profile) }),
    });
}

// Paste this into the Firebase Console -> Firestore Database -> Rules tab.
// Restricts each user's profile document to only that user's own verified
// token -- nobody can read or write another user's progress.
//
// This also means a determined player can edit their own XP/profile fields
// directly through the Firebase SDK, bypassing the server entirely -- a
// deliberate accepted tradeoff for a single-player study game with no
// leaderboards or social comparison (issue #22). The server-side write path
// (combat-action.js) still only ever derives XP from its own session state,
// never from the request body, so the *game* can't be cheated through the
// normal client -- only a player's own private stat display could be, which
// only harms their own record-keeping. Revisit this before shipping any
// feature that compares one player's stats to another's.
export const FIRESTORE_RULES = `
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /user_profiles/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
`;
