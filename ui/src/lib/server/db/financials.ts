import { db } from '../db';
import type { FinancialComparisonResponse } from '$lib/api-types';

export async function getFinancialComparison(
	ticker: string,
	statementType?: string,
	periods: number = 5
): Promise<FinancialComparisonResponse | null> {
	const company = await db
		.selectFrom('companies')
		.select('id')
		.where('ticker', '=', ticker.toUpperCase())
		.executeTakeFirst();

	if (!company) return null;

	// Get distinct value_date periods, newest first
	const periodRows = await db
		.selectFrom('financial_values')
		.select('value_date')
		.distinct()
		.where('company_id', '=', company.id)
		.orderBy('value_date', 'desc')
		.limit(periods)
		.execute();

	if (periodRows.length === 0) return { periods: [], items: [] };

	const periodDates = periodRows.map((r) => toDateString(r.value_date));
	const periodValues = periodRows.map((r) => r.value_date);

	// Query values joined with concepts for those periods
	let query = db
		.selectFrom('financial_values as fv')
		.innerJoin('financial_concepts as fc', 'fc.id', 'fv.concept_id')
		.select([
			'fc.name as concept_name',
			'fc.description',
			'fc.labels',
			'fv.value_date',
			'fv.value'
		])
		.where('fv.company_id', '=', company.id)
		.where('fv.value_date', 'in', periodValues);

	// TODO: statementType filter would require array containment operator
	// For now this matches the Python behavior when no filter is applied

	const results = await query.execute();

	// Group by concept
	const conceptData = new Map<
		string,
		{ description: string | null; labels: string[]; values: Map<string, number> }
	>();

	for (const row of results) {
		if (!conceptData.has(row.concept_name)) {
			conceptData.set(row.concept_name, {
				description: row.description,
				labels: row.labels ?? [],
				values: new Map()
			});
		}
		const dateStr = toDateString(row.value_date);
		conceptData.get(row.concept_name)!.values.set(dateStr, Number(row.value));
	}

	// Build items with period-over-period changes
	const items = Array.from(conceptData.entries()).map(([conceptName, data]) => {
		const values = periodDates.map((d) => ({
			date: d,
			value: data.values.get(d) ?? null
		}));

		const changes = [];
		for (let i = 0; i < periodDates.length - 1; i++) {
			const current = data.values.get(periodDates[i]);
			const prev = data.values.get(periodDates[i + 1]);
			if (current != null && prev != null && prev !== 0) {
				const abs = current - prev;
				const pct = (abs / Math.abs(prev)) * 100;
				changes.push({
					from_date: periodDates[i + 1],
					to_date: periodDates[i],
					absolute: Math.round(abs * 100) / 100,
					percent: Math.round(pct * 100) / 100
				});
			} else {
				changes.push({
					from_date: periodDates[i + 1],
					to_date: periodDates[i],
					absolute: null,
					percent: null
				});
			}
		}

		return { concept_name: conceptName, description: data.description, labels: data.labels, values, changes };
	});

	return { periods: periodDates, items };
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
