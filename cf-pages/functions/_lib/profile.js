// Persistent per-user profile in Firestore, keyed by Firebase UID.
// Deliberately minimal for now (just enough to resume a game on another
// device); the points/gacha/upgrades economy discussed separately this
// session is an intentionally deferred, larger feature, not part of this.
//
// Uses Firestore's REST API directly with the caller's own Firebase Auth ID
// token as the Bearer credential -- no service account/Admin SDK needed.
// Firestore's security rules (see FIRESTORE_RULES below) enforce that a
// token can only read/write the document matching its own uid.

const FIREBASE_PROJECT_ID = 'study-saga-live';
const FIRESTORE_BASE = `https://firestore.googleapis.com/v1/projects/${FIREBASE_PROJECT_ID}/databases/(default)/documents/user_profiles`;

export function freshProfile(uid) {
    return { uid, active_game_id: null };
}

// Firestore REST documents use typed field values, e.g. {stringValue: "x"}
// or {nullValue: null} -- these convert our plain JS profile object to/from
// that shape. Keep both directions in one file since the schema is tiny.
function toFirestoreFields(profile) {
    return {
        uid: { stringValue: profile.uid },
        active_game_id: profile.active_game_id
            ? { stringValue: profile.active_game_id }
            : { nullValue: null },
    };
}

function fromFirestoreFields(fields) {
    return {
        uid: fields.uid?.stringValue ?? null,
        active_game_id: fields.active_game_id?.stringValue ?? null,
    };
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
