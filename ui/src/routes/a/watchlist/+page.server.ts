import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { addToWatchlist, getWatchlist, removeFromWatchlist } from '$lib/server/db/watchlist';
import { getSupporterStatus } from '$lib/server/db/supporter';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		redirect(302, `/login?returnTo=${encodeURIComponent(url.pathname)}`);
	}
	const [watching, supporter] = await Promise.all([
		getWatchlist(locals.user.id),
		getSupporterStatus(locals.user.id)
	]);
	return {
		watching,
		badges: supporter.badges,
		firstName: locals.user.name.trim().split(/\s+/)[0] || locals.user.name
	};
};

export const actions: Actions = {
	add: async ({ request, locals }) => {
		if (!locals.user) return fail(401, { message: 'Not signed in' });
		const data = await request.formData();
		const companyId = String(data.get('companyId') ?? '');
		if (!companyId) return fail(400, { message: 'Missing company' });
		await addToWatchlist(locals.user.id, companyId);
		return { success: true };
	},
	remove: async ({ request, locals }) => {
		if (!locals.user) return fail(401, { message: 'Not signed in' });
		const data = await request.formData();
		const companyId = String(data.get('companyId') ?? '');
		if (!companyId) return fail(400, { message: 'Missing company' });
		await removeFromWatchlist(locals.user.id, companyId);
		return { success: true };
	}
};
