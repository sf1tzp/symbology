// Client-only preference for the occasional on-screen UI hints (e.g. the mobile
// "tap here to switch content types" nudge on the companies index). Persisted in
// localStorage rather than the account so it covers signed-out browsers too —
// the hints mostly target first-time visitors on public pages — and an inline
// dismiss works without a round-trip.
//
// The flag is read lazily via load() from a client effect (localStorage is
// undefined during SSR), and `loaded` gates rendering so a hint never flashes on
// the first paint before we know whether the viewer has dismissed it.
import { browser } from '$app/environment';

const KEY = 'symbology:hints-disabled';

let disabled = $state(false);
let loaded = $state(false);

export const hints = {
	/** Whether the viewer has turned hints off. */
	get disabled() {
		return disabled;
	},
	/** True once the stored value has been read on the client (gates rendering). */
	get loaded() {
		return loaded;
	},
	/** Read the persisted choice. Safe to call repeatedly; a no-op after the first. */
	load() {
		if (!browser || loaded) return;
		try {
			disabled = localStorage.getItem(KEY) === '1';
		} catch {
			// localStorage can throw (private mode / disabled) — treat as enabled.
		}
		loaded = true;
	},
	/** Persist whether hints are disabled. */
	set(value: boolean) {
		disabled = value;
		loaded = true;
		if (!browser) return;
		try {
			if (value) localStorage.setItem(KEY, '1');
			else localStorage.removeItem(KEY);
		} catch {
			// Ignore storage failures; the in-memory flag still applies this session.
		}
	}
};
