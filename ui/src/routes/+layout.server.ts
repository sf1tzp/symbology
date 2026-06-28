import type { LayoutServerLoad } from './$types';
import { getSupporterStatus } from '$lib/server/db/supporter';
import { coerceBadgeKey } from '$lib/supporter-plans';

/**
 * Expose the authenticated user (if any) and their supporter standing to every
 * page + the navbar. The supporter status drives the navbar pill and the
 * server-side content gating; it's a single indexed lookup per request.
 */
export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.user) {
		return { user: null, supporter: null, avatarBadge: null };
	}
	const supporter = await getSupporterStatus(locals.user.id);

	// Resolve the profile-icon badge: honour the user's choice (stored in the
	// `user.avatarBadge` custom field) only if they've actually earned that badge,
	// so a stale or tampered value silently falls back to initials.
	const chosenKey = coerceBadgeKey(locals.user.avatarBadge);
	const avatarBadge = chosenKey
		? (supporter.badges.find((b) => b.key === chosenKey) ?? null)
		: null;

	return {
		user: { id: locals.user.id, name: locals.user.name, email: locals.user.email },
		supporter: { active: supporter.active, daysLeft: supporter.daysLeft },
		avatarBadge
	};
};
