/**
 * Shared navigation model used by both the top {@link Navbar} (desktop) and the
 * {@link MobileTabBar} (mobile). Keeping the item list, account entry, and
 * active-path logic in one place guarantees the two navs handle user status
 * identically.
 */
export interface NavItem {
	href: string;
	label: string;
}

/** Minimal authenticated-user shape the navs need; `null` when signed out. */
export type NavUser = { id: string; name: string; email: string } | null;

/**
 * Primary destinations. The Watchlist entry only appears for signed-in users,
 * so both navs must be passed the current `user`.
 */
export function buildNavItems(user: NavUser): NavItem[] {
	return [
		{ href: '/', label: 'Home' },
		{ href: '/companies', label: 'Companies' },
		...(user ? [{ href: '/watchlist', label: 'Watchlist' }] : []),
		{ href: '/status', label: 'Status' },
		{ href: '/faq', label: 'FAQ' }
	];
}

/** Account destination when signed in, otherwise the sign-in link. */
export function accountNavItem(user: NavUser): NavItem {
	return user ? { href: '/account', label: 'Account' } : { href: '/login', label: 'Sign in' };
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
