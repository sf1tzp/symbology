import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// The synthesis viewer moved from /g/[ticker]/[sha] to /s/[sha] (s = synthesis;
// the content hash alone identifies any synthesis). Permanently redirect old
// deep links (shared URLs, status-page links), dropping the ticker.
export const load: PageLoad = ({ params }) => {
	redirect(308, `/s/${params.sha}`);
};
