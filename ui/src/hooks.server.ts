import { building } from '$app/environment';
import { svelteKitHandler } from 'better-auth/svelte-kit';
import { auth } from '$lib/server/auth';
import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	// Populate locals.user / locals.session for all loads & actions.
	const session = await auth.api.getSession({ headers: event.request.headers });
	event.locals.user = session?.user ?? null;
	event.locals.session = session?.session ?? null;

	// Let Better Auth serve /api/auth/* ; otherwise continue the SvelteKit pipeline.
	return svelteKitHandler({ auth, event, resolve, building });
};
