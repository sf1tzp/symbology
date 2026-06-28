import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// The companies index moved to /c for consistency with the /f (filings) and
// /s (synthesis) browse surfaces. Permanently redirect the old path.
export const load: PageLoad = () => {
	redirect(308, '/c');
};
