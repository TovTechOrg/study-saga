import { jwtVerify, createRemoteJWKSet } from 'jose';

const FIREBASE_PROJECT_ID = 'study-saga-live';
const ISSUER = `https://securetoken.google.com/${FIREBASE_PROJECT_ID}`;
const JWKS_URL = 'https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com';

// Cached across requests within the same Worker isolate -- avoids refetching
// Google's public keys on every call.
const JWKS = createRemoteJWKSet(new URL(JWKS_URL));

// Verifies a Firebase Auth ID token without the (Node-only) Firebase Admin
// SDK -- Workers can't run that. Returns { uid } on success, null on any
// failure (expired, wrong project, malformed, etc.) so callers can treat
// auth as optional and fail open to guest behavior.
export async function verifyFirebaseToken(idToken) {
    if (!idToken) return null;
    try {
        const { payload } = await jwtVerify(idToken, JWKS, {
            issuer: ISSUER,
            audience: FIREBASE_PROJECT_ID,
        });
        if (!payload.sub) return null;
        return { uid: payload.sub };
    } catch (e) {
        return null;
    }
}
