import { createAuthClient } from 'better-auth/svelte';
import { inferAdditionalFields } from 'better-auth/client/plugins';

/**
 * Browser-side Better Auth client. baseURL is omitted so it talks to the
 * same origin (the SvelteKit `/api/auth/*` routes served via hooks.server.ts).
 *
 * The additionalFields shape is declared explicitly (rather than inferred from
 * the server `auth` instance) so this client module never imports server-only
 * code. It must mirror `user.additionalFields` in $lib/server/auth.ts — that's
 * what types `avatarBadge` on `updateUser` and the session user.
 */
export const authClient = createAuthClient({
	plugins: [
		inferAdditionalFields({
			user: { avatarBadge: { type: 'string', required: false } }
		})
	]
});

export const {
	signIn,
	signUp,
	signOut,
	useSession,
	updateUser,
	changePassword,
	deleteUser,
	sendVerificationEmail,
	requestPasswordReset,
	resetPassword
} = authClient;
