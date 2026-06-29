/**
 * Shared navigation model used by both the top {@link Navbar} (desktop) and the
 * {@link MobileTabBar} (mobile). Keeping the item list, account entry, and
 * active-path logic in one place guarantees the two navs handle user status
 * identically.
 */
import { supportEnabled } from '$lib/features';

export interface NavItem {
	href: string;
	label: string;
}

/** Minimal authenticated-user shape the navs need; `null` when signed out. */
export type NavUser = { id: string; name: string; email: string } | null;

/**
 * Primary destinations shown as inline links in the desktop top-nav. The account
 * hub (/a/watchlist) is reached via the profile icon, Status via the icon button
 * by the dark-mode toggle, and Support via its own affordance — so none of those
 * appear here. Home is omitted entirely; the brand mark already returns there.
 */
export function buildNavItems(): NavItem[] {
	return [
		{ href: '/c', label: 'Companies' },
		{ href: '/f', label: 'Filings' },
		{ href: '/s', label: 'Synthesis' },
		{ href: '/faq', label: 'FAQ' }
	];
}

/**
 * Account destination when signed in (the /a/watchlist hub), otherwise the
 * sign-in link.
 */
export function accountNavItem(user: NavUser): NavItem {
	return user ? { href: '/a/watchlist', label: 'Account' } : { href: '/login', label: 'Sign in' };
}

/** The three browse surfaces — companies, filings, and syntheses. */
export type BrowseSection = 'companies' | 'filings' | 'synthesis';

/** A browse surface's index destination, tagged with its section key. */
export interface BrowseDestination extends NavItem {
	key: BrowseSection;
}

/**
 * The browse surfaces — companies, filings, and syntheses — each a searchable,
 * paginated index. The first mobile tab reflects the current section and opens a
 * flyout onto the siblings while the viewer is on that section's index page.
 */
export const BROWSE_DESTINATIONS: BrowseDestination[] = [
	{ key: 'companies', href: '/c', label: 'Companies' },
	{ key: 'filings', href: '/f', label: 'Filings' },
	{ key: 'synthesis', href: '/s', label: 'Synthesis' }
];

/**
 * The browse section a route genuinely belongs to, or `null` for pages that sit
 * outside the three browse surfaces (FAQ, Support, Account, …). `/s` and `/f`
 * map to synthesis and filings; `/c` and `/d` (a company and its documents) map
 * to companies. Unlike {@link currentSection} this does *not* fall back to
 * companies, so callers can tell "on companies" apart from "on no section" and
 * keep showing the last visited section on those off-surface pages.
 */
export function routeSection(pathname: string): BrowseSection | null {
	if (/^\/s(\/|$)/.test(pathname)) return 'synthesis';
	if (/^\/f(\/|$)/.test(pathname)) return 'filings';
	if (/^\/[cd](\/|$)/.test(pathname)) return 'companies';
	return null;
}

/**
 * The browse section the current route belongs to, defaulting to companies (the
 * browse entry point) for any page outside the three surfaces. Use
 * {@link routeSection} when the off-surface case must be distinguished.
 */
export function currentSection(pathname: string): BrowseSection {
	return routeSection(pathname) ?? 'companies';
}

/** The index destination for a browse section. */
export function browseDestination(section: BrowseSection): BrowseDestination {
	return BROWSE_DESTINATIONS.find((d) => d.key === section) ?? BROWSE_DESTINATIONS[0];
}

/** The browse sections other than `section` — the flyout's jump targets. */
export function siblingSections(section: BrowseSection): BrowseDestination[] {
	return BROWSE_DESTINATIONS.filter((d) => d.key !== section);
}

/** Whether `pathname` is one of the browse index pages (not a detail route). */
export function isBrowseIndex(pathname: string): boolean {
	return pathname === '/c' || pathname === '/f' || pathname === '/s';
}

/**
 * The full ordered tab list for the mobile bottom bar. The leading slot is the
 * current browse section (which doubles as the flyout trigger). The second slot
 * is a context link back to the current resource (company / filing / synthesis)
 * while on one of those routes, otherwise FAQ. Support sits in its own always-on
 * slot (when the support surface is enabled), and the trailing slot is the
 * account / sign-in entry.
 */
export function buildMobileTabItems(
	user: NavUser,
	context: ContextNavItem | null,
	browse: BrowseDestination
): NavItem[] {
	const items: NavItem[] = [browse];
	if (context) {
		items.push(context);
	} else {
		items.push({ href: '/faq', label: 'FAQ' });
	}
	if (supportEnabled) {
		items.push({ href: '/support', label: 'Support' });
	}
	items.push(accountNavItem(user));
	return items;
}

/** The kind of resource a context route is anchored to, used to pick its icon. */
export type ContextKind = 'company' | 'filing' | 'synthesis';

/** A context nav item carries its resource kind so the bar can icon it. */
export interface ContextNavItem extends NavItem {
	kind: ContextKind;
}

/** Loosely-typed slice of `page.data` the context resolver reads from. */
type ContextData =
	| {
			company?: { ticker?: string | null } | null;
			filing?: { form?: string | null; accession_number?: string | null } | null;
			accession_number?: string | null;
			content?: {
				short_hash?: string | null;
				content_hash?: string | null;
				generation_depth?: number | null;
			} | null;
			sha?: string | null;
	  }
	| null
	| undefined;

/**
 * The context-slot nav item for the current page when on a resource route:
 * - `/f` (a filing): a document chip labelled with the form type (e.g. 10-K),
 * - `/s` (a synthesis): a sparkle chip labelled with the synthesis level (Ln),
 * - `/c` or `/d` (a company / its documents): a chip labelled with the ticker.
 *
 * Returns `null` on every other route, where the bar falls back to the Support
 * CTA. The link points back at the resource itself; the data is pulled from the
 * route's loaded `page.data`.
 */
export function buildContextNavItem(pathname: string, data: ContextData): ContextNavItem | null {
	if (/^\/f\//.test(pathname)) {
		const form = data?.filing?.form;
		const accession = data?.filing?.accession_number ?? data?.accession_number;
		if (form && accession) return { kind: 'filing', href: `/f/${accession}`, label: form };
		return null;
	}
	if (/^\/s\//.test(pathname)) {
		const content = data?.content;
		const hash = content?.short_hash ?? content?.content_hash?.slice(0, 12) ?? data?.sha;
		if (hash) {
			const depth = content?.generation_depth;
			return {
				kind: 'synthesis',
				href: `/s/${hash}`,
				label: depth != null ? `L${depth}` : 'Synthesis'
			};
		}
		return null;
	}
	if (/^\/(c|d)\//.test(pathname)) {
		const ticker = data?.company?.ticker;
		if (ticker) return { kind: 'company', href: `/c/${ticker}`, label: ticker };
	}
	return null;
}

/** Whether `href` is the active destination for the current `pathname`. */
export function isCurrentPath(pathname: string, href: string): boolean {
	if (href === '/') return pathname === '/';
	return pathname.startsWith(href);
}

/** Two-letter avatar initials derived from a display name. */
export function initials(name: string): string {
	const parts = name.trim().split(/\s+/).filter(Boolean);
	if (parts.length === 0) return '?';
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
	return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
