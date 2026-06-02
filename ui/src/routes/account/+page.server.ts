import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		redirect(302, `/login?returnTo=${encodeURIComponent(url.pathname)}`);
	}
	return {
		account: {
			name: locals.user.name,
			email: locals.user.email
		}
	};
};
