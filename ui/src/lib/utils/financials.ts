import type { FinancialComparisonResponse, FinancialLineItem } from '$lib/api-types';

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
