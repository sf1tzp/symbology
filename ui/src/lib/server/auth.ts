import { betterAuth } from 'better-auth';
import { sveltekitCookies } from 'better-auth/svelte-kit';
import { getRequestEvent } from '$app/server';
import pg from 'pg';
import { env } from '$env/dynamic/private';
import { getDatabaseUrl } from './db-config';
import { sendEmail } from './email/send';
import { notifySupport } from './email/notifySupport';
import { verifyEmail } from './email/templates/verifyEmail';
import { resetPassword } from './email/templates/resetPassword';
import { welcome } from './email/templates/welcome';

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
		// Block session creation until the email is verified, so accounts can't be
		// created against addresses the user doesn't control.
		requireEmailVerification: true,
		// Reset links are single-use and expire in 1 hour (security pattern).
		resetPasswordTokenExpiresIn: 60 * 60,
		sendResetPassword: async ({ user, url }) => {
			await sendEmail({ to: user.email, ...resetPassword({ url, name: user.name }) });
		}
	},
	emailVerification: {
		// Fire a verification email on sign-up, and log the user in automatically
		// once they click the link so verifying lands them straight in the app.
		sendOnSignUp: true,
		autoSignInAfterVerification: true,
		// Verification links expire in 24 hours.
		expiresIn: 60 * 60 * 24,
		sendVerificationEmail: async ({ user, url }) => {
			await sendEmail({ to: user.email, ...verifyEmail({ url, name: user.name }) });
		},
		// One-time welcome once the address is confirmed.
		afterEmailVerification: async (user) => {
			const appUrl = new URL('/a/watchlist', env.BETTER_AUTH_URL).toString();
			await sendEmail({ to: user.email, ...welcome({ name: user.name, appUrl }) });
		}
	},
	user: {
		// Allow self-service account deletion. No deletion-verification callback is
		// configured, so deletion happens immediately; the client passes the
		// current password so it works regardless of session freshness.
		deleteUser: { enabled: true },
		// Custom account-domain fields. `avatarBadge` holds the BadgeKey the user
		// picked for their profile icon (null/empty = initials). Added to auth.user
		// by `@better-auth/cli migrate`; it rides in the session, so the navbar
		// reads it with no extra query. The client mirrors this shape via
		// inferAdditionalFields in auth-client.ts.
		additionalFields: {
			avatarBadge: { type: 'string', required: false, input: true }
		}
	},
	databaseHooks: {
		user: {
			create: {
				// Notify the support inbox the moment an account row is created.
				// This fires on signup, before email verification, so it captures
				// every new account (including drop-offs that never verify).
				// notifySupport never throws, so it can't break account creation.
				after: async (user) => {
					await notifySupport({
						subject: `New account: ${user.email}`,
						lines: [
							'A new account was created.',
							`Email: ${user.email}`,
							`Name: ${user.name || '(none)'}`,
							`User ID: ${user.id}`
						]
					});
				}
			}
		}
	},
	// sveltekitCookies must be the last plugin so it can flush Set-Cookie
	// headers emitted by earlier hooks into SvelteKit's cookie jar.
	plugins: [sveltekitCookies(getRequestEvent)]
});

export type Session = typeof auth.$Infer.Session.session;
export type User = typeof auth.$Infer.Session.user;
