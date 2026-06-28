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
 * appear here.
 */
export function buildNavItems(): NavItem[] {
	return [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' },
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

/**
 * The full ordered tab list for the mobile bottom bar. The center slot is a quick
 * link back to the company while on a company-context route, otherwise the
 * Support CTA — which is omitted entirely while the support surface is gated off,
 * leaving a four-tab bar. The trailing slot is the account / sign-in entry.
 */
export function buildMobileTabItems(user: NavUser, ticker: string | null): NavItem[] {
	const items: NavItem[] = [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' }
	];
	if (ticker) {
		items.push(companyNavItem(ticker));
	} else if (supportEnabled) {
		items.push({ href: '/support', label: 'Support' });
	}
	items.push({ href: '/faq', label: 'FAQ' });
	items.push(accountNavItem(user));
	return items;
}

/**
 * "Back to company" destination shown in place of the center mobile tab while on
 * a company-context route (the company page itself, a filing, or a document).
 */
export function companyNavItem(ticker: string): NavItem {
	return { href: `/c/${ticker}`, label: ticker };
}

/**
 * The company ticker for the current page when on a company-context route
 * (`/c`, `/f`, `/d`), or `null` elsewhere. The company page carries it in the
 * route param; filing/document pages resolve it into `data.company`.
 */
export function companyContextTicker(
	pathname: string,
	data: { company?: { ticker?: string | null } | null } | null | undefined
): string | null {
	if (!/^\/(c|f|d)\//.test(pathname)) return null;
	return data?.company?.ticker ?? null;
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
