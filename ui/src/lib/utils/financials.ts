import type { FinancialComparisonResponse, FinancialLineItem, PeriodChange } from '$lib/api-types';

export function formatFinancialValue(value: number | null): string {
	if (value === null || value === undefined) return '-';
	const abs = Math.abs(value);
	if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
	if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
	if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
	return value.toFixed(2);
}

export function formatConceptName(name: string): string {
	return name
		.replace(/^us-gaap[_:]/, '')
		.replace(/([a-z])([A-Z])/g, '$1 $2')
		.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
}

export function formatPeriodDate(dateStr: string): string {
	try {
		const d = new Date(dateStr + 'T00:00:00');
		return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
	} catch {
		return dateStr;
	}
}

/**
 * Find a financial line item by keyword match on description or concept_name.
 * Optionally filter by statement type label.
 */
export function findConcept(
	items: FinancialLineItem[],
	keywords: string[],
	label?: string
): FinancialLineItem | null {
	const candidates = label ? items.filter((i) => i.labels.includes(label)) : items;
	for (const kw of keywords) {
		const lower = kw.toLowerCase();
		const match = candidates.find(
			(i) =>
				(i.description && i.description.toLowerCase().includes(lower)) ||
				i.concept_name.toLowerCase().includes(lower)
		);
		if (match) return match;
	}
	return null;
}

/**
 * Get the most recent non-null value from a financial line item.
 * Items are returned newest-first from the DB, so values[0] is typically the latest.
 */
export function getLatestValue(item: FinancialLineItem): { date: string; value: number } | null {
	for (const v of item.values) {
		if (v.value !== null) return { date: v.date, value: v.value };
	}
	return null;
}

// Statement types in the order we prefer to show them, matching the labels
// applied at ingestion (see server ingestion_helpers.py).
export const STATEMENT_TYPES = ['income_statement', 'balance_sheet', 'cash_flow'] as const;
export type StatementType = (typeof STATEMENT_TYPES)[number];

/** How many line items a company has under each statement type. */
export function statementItemCounts(
	data: FinancialComparisonResponse | null
): Record<string, number> {
	const counts: Record<string, number> = {};
	for (const item of data?.items ?? []) {
		for (const label of item.labels) counts[label] = (counts[label] ?? 0) + 1;
	}
	return counts;
}

/** The first statement type (in preferred order) that has any data, or null. */
export function firstNonEmptyStatement(
	data: FinancialComparisonResponse | null
): StatementType | null {
	const counts = statementItemCounts(data);
	return STATEMENT_TYPES.find((st) => (counts[st] ?? 0) > 0) ?? null;
}

export interface HeadlineStat {
	label: string;
	value: number;
	/** 'currency' → "$1.2B"; 'plain' → fixed-2 (per-share figures). */
	format: 'currency' | 'plain';
	change: PeriodChange | null;
}

// Prioritised ladder of headline metrics — the figures an analyst glances at
// first, universal → specific. Each entry resolves via findConcept (keyword +
// optional statement label). We walk this list and surface the first N that
// resolve to a value, so a company missing one statement (e.g. banks/REITs with
// no parseable income statement) still fills the strip from what it does report.
const HEADLINE_LADDER: {
	label: string;
	keywords: string[];
	statement?: StatementType;
	format?: 'currency' | 'plain';
}[] = [
	{
		label: 'Net Revenue',
		keywords: ['Revenue', 'Net Sales', 'Sales'],
		statement: 'income_statement'
	},
	{
		label: 'Net Income',
		keywords: ['NetIncome', 'Net Income', 'Net Earnings'],
		statement: 'income_statement'
	},
	{
		label: 'Operating Income',
		keywords: ['OperatingIncome', 'Operating Income'],
		statement: 'income_statement'
	},
	{ label: 'Total Assets', keywords: ['Assets'], statement: 'balance_sheet' },
	{
		label: 'Total Equity',
		keywords: ['StockholdersEquity', "Stockholders' Equity", 'Total Equity'],
		statement: 'balance_sheet'
	},
	{
		label: 'Cash & Equivalents',
		keywords: ['CashAndCashEquivalents', 'Cash and Cash Equivalents'],
		statement: 'balance_sheet'
	},
	{
		label: 'Total Liabilities',
		keywords: ['Liabilities'],
		statement: 'balance_sheet'
	},
	{
		label: 'Operating Cash Flow',
		keywords: ['NetCashProvidedByUsedInOperatingActivities', 'Operating Activities'],
		statement: 'cash_flow'
	},
	{
		label: 'EPS (Diluted)',
		keywords: ['EarningsPerShareDiluted', 'EarningsPerShare', 'Earnings Per Share'],
		format: 'plain'
	}
];

/**
 * Resolve the prioritised headline ladder against a company's reported concepts,
 * returning up to `n` stats that actually have a latest value. Each concept is
 * used at most once (a fuzzy keyword like "Assets" can match several rungs).
 */
export function pickHeadlineStats(data: FinancialComparisonResponse | null, n = 4): HeadlineStat[] {
	if (!data) return [];
	const out: HeadlineStat[] = [];
	const usedConcepts = new Set<string>();
	for (const rung of HEADLINE_LADDER) {
		if (out.length >= n) break;
		const item = findConcept(data.items, rung.keywords, rung.statement);
		if (!item || usedConcepts.has(item.concept_name)) continue;
		const latest = getLatestValue(item);
		if (!latest) continue;
		usedConcepts.add(item.concept_name);
		out.push({
			label: rung.label,
			value: latest.value,
			format: rung.format ?? 'currency',
			change: item.changes.find((c) => c.percent !== null) ?? null
		});
	}
	return out;
}

/** Render a headline stat's value with its display format. */
export function formatHeadlineStat(stat: HeadlineStat): string {
	return stat.format === 'plain'
		? `$${stat.value.toFixed(2)}`
		: `$${formatFinancialValue(stat.value)}`;
}

/**
 * Derive the date range string from financial comparison periods.
 */
export function getPeriodsRange(data: FinancialComparisonResponse): string | null {
	if (!data.periods.length) return null;
	const sorted = [...data.periods].sort();
	const first = formatPeriodDate(sorted[0]);
	const last = formatPeriodDate(sorted[sorted.length - 1]);
	return `${first} — ${last}`;
}
