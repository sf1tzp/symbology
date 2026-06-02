import type { LayoutServerLoad } from './$types';

/** Expose the authenticated user (if any) to every page + the navbar. */
export const load: LayoutServerLoad = async ({ locals }) => {
	return {
		user: locals.user
			? { id: locals.user.id, name: locals.user.name, email: locals.user.email }
			: null
	};
};
