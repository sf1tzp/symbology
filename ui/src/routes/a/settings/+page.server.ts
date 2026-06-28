import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getSupporterStatus } from '$lib/server/db/supporter';
import { coerceBadgeKey } from '$lib/supporter-plans';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		redirect(302, `/login?returnTo=${encodeURIComponent(url.pathname)}`);
	}
	return {
		account: {
			name: locals.user.name,
			email: locals.user.email
		},
		supporter: await getSupporterStatus(locals.user.id),
		// The currently-chosen profile-icon badge (null = initials).
		avatarBadgeKey: coerceBadgeKey(locals.user.avatarBadge)
	};
};
