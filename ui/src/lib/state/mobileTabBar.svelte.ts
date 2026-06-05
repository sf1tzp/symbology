// Shared flag for temporarily hiding the bottom MobileTabBar (the mobile primary
// nav, rendered once in the root layout). A page sets `hidden = true` — e.g.
// while its search input is focused on mobile, so the on-screen keyboard area
// stays uncluttered — and back to false on blur/unmount. Reading it from
// MobileTabBar keeps the toggle decoupled from where it's triggered.
export const mobileTabBar = $state({ hidden: false });
