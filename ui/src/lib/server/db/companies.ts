import { db } from '../db';
import type { CompanyResponse } from '$lib/api-types';

export async function getCompanyByTicker(ticker: string): Promise<CompanyResponse | null> {
	const company = await db
		.selectFrom('companies')
		.selectAll()
		.where('ticker', '=', ticker.toUpperCase())
		.executeTakeFirst();

	if (!company) return null;

	const summary = await getFrontpageSummaryByTicker(ticker);

	return {
		id: company.id,
		name: company.name,
		display_name: company.display_name,
		ticker: company.ticker,
		exchanges: company.exchanges ?? [],
		sic: company.sic,
		sic_description: company.sic_description,
		fiscal_year_end: company.fiscal_year_end
			? new Date(company.fiscal_year_end as unknown as string).toISOString().split('T')[0]
			: null,
		former_names: (company.former_names as Array<{ name: string; date_changed: string }>) ?? [],
		summary
	};
}

async function getFrontpageSummaryByTicker(ticker: string): Promise<string | null> {
	const result = await db
		.selectFrom('generated_content')
		.innerJoin('companies', 'companies.id', 'generated_content.company_id')
		.select('generated_content.content')
		.where('companies.ticker', '=', ticker.toUpperCase())
		.where((eb) =>
			eb.or([
				eb.and([
					eb('generated_content.content_stage', '=', 'frontpage_summary'),
					eb('generated_content.document_type', '=', 'business_description')
				]),
				eb('generated_content.description', '=', 'business_description_frontpage_summary')
			])
		)
		.orderBy('generated_content.created_at', 'desc')
		.limit(1)
		.executeTakeFirst();

	return result?.content ?? null;
}
