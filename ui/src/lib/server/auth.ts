import { betterAuth } from 'better-auth';
import { sveltekitCookies } from 'better-auth/svelte-kit';
import { getRequestEvent } from '$app/server';
import pg from 'pg';
import { env } from '$env/dynamic/private';
import { getDatabaseUrl } from './db-config';

const { Pool } = pg;

/**
 * Dedicated pool for Better Auth. Same database as the app's Kysely pool, but
 * `search_path=auth` so Better Auth's tables (user/session/account/
 * verification) live in the `auth` schema. The `auth` schema is created by the
 * Alembic migration `r7b8c9d0e1f2`; the tables inside are created by
 * `@better-auth/cli migrate`. Alembic owns `public` and never touches `auth`.
 */
const authPool = new Pool({
	connectionString: getDatabaseUrl(),
	options: '-c search_path=auth',
	max: 5
});

export const auth = betterAuth({
	database: authPool,
	secret: env.BETTER_AUTH_SECRET,
	baseURL: env.BETTER_AUTH_URL,
	emailAndPassword: {
		enabled: true,
		// Email verification + password reset need an SMTP sender; wire that as
		// a follow-up. Until then accounts are usable immediately.
		requireEmailVerification: false
	},
	user: {
		// Allow self-service account deletion. No email-verification callback is
		// configured, so deletion happens immediately; the client passes the
		// current password so it works regardless of session freshness.
		deleteUser: { enabled: true }
	},
	// sveltekitCookies must be the last plugin so it can flush Set-Cookie
	// headers emitted by earlier hooks into SvelteKit's cookie jar.
	plugins: [sveltekitCookies(getRequestEvent)]
});

export type Session = typeof auth.$Infer.Session.session;
export type User = typeof auth.$Infer.Session.user;
