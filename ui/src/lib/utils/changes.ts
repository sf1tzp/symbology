// Shared metadata for the diff / change views. Centralising the per-document-type
// and per-change-kind accent colours, labels, and the significance heuristic keeps
// the change cards (c/, f/, changes/ routes) and the side-by-side diff list visually
// consistent and stops the copies drifting apart.

// One accent per document type (theme palette). Used where cards are coloured by the
// section they belong to (company overview + filing pages).
const DOC_COLORS: Record<string, string> = {
	business_description: 'var(--teal-2)',
	risk_factors: 'var(--danger)',
	management_discussion: 'var(--blue)',
	controls_procedures: 'var(--gold)',
	market_risk: 'var(--plum)'
};
export const docColor = (t: string): string => DOC_COLORS[t] ?? 'var(--ink-3)';

// One accent per change kind (theme palette). Shared by the change cards and the
// side-by-side diff tags so a given change kind reads the same colour everywhere.
const CHANGE_KIND_COLORS: Record<string, string> = {
	new: 'var(--teal-2)',
	escalated: 'var(--warn)',
	de_emphasised: 'var(--blue)',
	reworded: 'var(--plum)',
	removed: 'var(--danger)'
};
export const changeKindColor = (k: string): string => CHANGE_KIND_COLORS[k] ?? 'var(--ink-3)';

const CHANGE_KIND_LABELS: Record<string, string> = {
	new: 'New disclosure',
	escalated: 'Escalated',
	de_emphasised: 'De-emphasised',
	reworded: 'Reworded',
	removed: 'Removed'
};
export const changeKindLabel = (k: string): string => CHANGE_KIND_LABELS[k] ?? k;

// Topic change kinds surfaced in on-page listings (cards + side-by-side): shifts in
// emphasis / wording of existing disclosures. New/removed topics are excluded.
export const VISIBLE_KINDS = new Set(['escalated', 'de_emphasised', 'reworded']);

// One diff op as stored on each topic. Mirrors SectionDiffView['ops'] /
// section_diffs.ops; redeclared here so this client-safe module needn't pull in
// server db types.
export interface DiffOp {
	op: 'equal' | 'insert' | 'delete';
	text: string;
}

// Numeric-noise thresholds: a change whose *edited* text is essentially just
// figures (year-over-year tables where only the numbers moved) clutters the
// change list, so on-page listings hide it.
const NUMERIC_NOISE_MIN_CHARS = 8; // ignore tiny edits; cosmetic ones are already not VISIBLE_KINDS
const NUMERIC_NOISE_MAX_ALPHA = 0.2; // max letter fraction among edited alphanumerics

/**
 * True when a diff's *changed* text — the insert/delete ops, not the stable
 * `equal` prose — is essentially just numbers (e.g. `$112,718` → `$91,650`,
 * `2023` → `2024`). Edits with no digits (pure prose rewordings) are never
 * numeric noise, and edits below a few characters are left alone.
 */
export function isNumericNoise(ops: DiffOp[] | null | undefined): boolean {
	if (!ops) return false;
	const changed = ops
		.filter((o) => o.op !== 'equal')
		.map((o) => o.text)
		.join('');
	const letters = (changed.match(/\p{L}/gu) ?? []).length;
	const digits = (changed.match(/\p{Nd}/gu) ?? []).length;
	if (digits === 0 || letters + digits < NUMERIC_NOISE_MIN_CHARS) return false;
	return letters / (letters + digits) < NUMERIC_NOISE_MAX_ALPHA;
}

/**
 * The single gate for topics shown in on-page listings (cards + side-by-side):
 * an emphasis/wording shift (VISIBLE_KINDS) whose change is more than just
 * figures. Shared by the filing page and the per-section change report so they
 * hide the same rows.
 */
export const isVisibleTopic = (t: { changeKind: string; ops?: DiffOp[] | null }): boolean =>
	VISIBLE_KINDS.has(t.changeKind) && !isNumericNoise(t.ops);

// Significance heuristic — mirrors scoreSectionDiff in server/db/diffs.ts (kept
// client-side to avoid pulling server-only code into the bundle).
const KIND_WEIGHT: Record<string, number> = {
	new: 1000,
	removed: 900,
	escalated: 600,
	de_emphasised: 500,
	reworded: 200,
	unchanged: 0
};
export interface ScorableTopic {
	changeKind: string;
	tokensAdded?: number | null;
	tokensRemoved?: number | null;
	lengthDelta?: number | null;
}
export const scoreTopic = (t: ScorableTopic): number =>
	(KIND_WEIGHT[t.changeKind] ?? 100) +
	(t.tokensAdded ?? 0) +
	(t.tokensRemoved ?? 0) +
	Math.abs(t.lengthDelta ?? 0) * 0.1;

/**
 * The top-N "what's new" change cards from a set of topics: the displayed-kind,
 * non-figures-only shifts (isVisibleTopic), ranked by significance. One definition
 * shared by every surface that shows headline cards (c/, f/, d/, changes/) so they
 * select and order identically.
 */
export const topChangeCards = <T extends ScorableTopic & { ops?: DiffOp[] | null }>(
	topics: T[],
	limit = 6
): T[] =>
	[...topics]
		.filter(isVisibleTopic)
		.sort((a, b) => scoreTopic(b) - scoreTopic(a))
		.slice(0, limit);
