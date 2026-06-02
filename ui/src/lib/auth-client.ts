import { createAuthClient } from 'better-auth/svelte';

/**
 * Browser-side Better Auth client. baseURL is omitted so it talks to the
 * same origin (the SvelteKit `/api/auth/*` routes served via hooks.server.ts).
 */
export const authClient = createAuthClient();

export const { signIn, signUp, signOut, useSession, updateUser, changePassword, deleteUser } =
	authClient;
