import { db } from '../db';
import type { Selectable } from 'kysely';
import type {
	CompanyGroupResponse,
	CompanyResponse,
	GeneratedContentResponse
} from '$lib/api-types';
import type { CompanyGroups } from './types';

export async function getCompanyGroups(limit: number = 50): Promise<CompanyGroupResponse[]> {
	const groups = await db
		.selectFrom('company_groups')
		.selectAll()
		.orderBy('name', 'asc')
		.limit(limit)
		.execute();

	return Promise.all(groups.map((g) => toGroupResponse(g, false)));
}

export async function getCompanyGroupBySlug(slug: string): Promise<CompanyGroupResponse | null> {
	const group = await db
		.selectFrom('company_groups')
		.selectAll()
		.where('slug', '=', slug)
		.executeTakeFirst();

	if (!group) return null;

	return toGroupResponse(group, true);
}

export async function getGroupFrontpageSummary(slug: string): Promise<string | null> {
	const group = await db
		.selectFrom('company_groups')
		.select('id')
		.where('slug', '=', slug)
		.executeTakeFirst();

	if (!group) return null;

	const row = await db
		.selectFrom('generated_content')
		.select('content')
		.where('company_group_id', '=', group.id)
		.where('content_stage', '=', 'company_group_frontpage')
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();

	return row?.content ?? null;
}

export async function getGroupAnalysis(
	slug: string,
	limit: number = 5
): Promise<GeneratedContentResponse[]> {
	const group = await db
		.selectFrom('company_groups')
		.select('id')
		.where('slug', '=', slug)
		.executeTakeFirst();

	if (!group) return [];

	const rows = await db
		.selectFrom('generated_content')
		.selectAll()
		.where('company_group_id', '=', group.id)
		.where('content_stage', '=', 'company_group_analysis')
		.orderBy('created_at', 'desc')
		.limit(limit)
		.execute();

	return Promise.all(
		rows.map(async (row) => {
			const [docIds, contentIds] = await Promise.all([
				db
					.selectFrom('generated_content_document_association')
					.select('document_id')
					.where('generated_content_id', '=', row.id)
					.execute(),
				db
					.selectFrom('generated_content_source_association')
					.select('source_content_id')
					.where('parent_content_id', '=', row.id)
					.execute()
			]);

			return {
				id: row.id,
				content_hash: row.content_hash,
				short_hash: row.content_hash?.slice(0, 12) ?? null,
				company_id: row.company_id,
				description: row.description,
				document_type: row.description,
				form_type: row.form_type,
				source_type: row.source_type,
				created_at: toISOString(row.created_at),
				total_duration: row.total_duration,
				input_tokens: row.input_tokens,
				output_tokens: row.output_tokens,
				warning: row.warning,
				content: row.content,
				summary: row.summary,
				model_config_id: row.model_config_id,
				system_prompt_id: row.system_prompt_id,
				user_prompt_id: row.user_prompt_id,
				source_document_ids: docIds.map((r) => r.document_id),
				source_content_ids: contentIds.map((r) => r.source_content_id)
			};
		})
	);
}

export async function getGroupsForCompany(companyId: string): Promise<CompanyGroupResponse[]> {
	const memberships = await db
		.selectFrom('company_group_membership')
		.select('company_group_id')
		.where('company_id', '=', companyId)
		.execute();

	if (memberships.length === 0) return [];

	const groupIds = memberships.map((m) => m.company_group_id);
	const groups = await db
		.selectFrom('company_groups')
		.selectAll()
		.where('id', 'in', groupIds)
		.execute();

	return Promise.all(groups.map((g) => toGroupResponse(g, true)));
}

async function toGroupResponse(
	group: Selectable<CompanyGroups>,
	includeCompanies: boolean
): Promise<CompanyGroupResponse> {
	// Get member count
	const members = await db
		.selectFrom('company_group_membership')
		.select('company_id')
		.where('company_group_id', '=', group.id)
		.execute();

	let companies: CompanyResponse[] | null = null;
	if (includeCompanies && members.length > 0) {
		const companyIds = members.map((m) => m.company_id);
		const companyRows = await db
			.selectFrom('companies')
			.selectAll()
			.where('id', 'in', companyIds)
			.execute();

		companies = companyRows.map((c) => ({
			id: c.id,
			name: c.name,
			display_name: c.display_name,
			ticker: c.ticker,
			exchanges: c.exchanges ?? [],
			sic: c.sic,
			sic_description: c.sic_description,
			fiscal_year_end: c.fiscal_year_end
				? new Date(c.fiscal_year_end as unknown as string).toISOString().split('T')[0]
				: null,
			former_names: (c.former_names as Array<{ name: string; date_changed: string }>) ?? [],
			summary: null
		}));
	}

	// Get latest analysis summary
	let latestAnalysisSummary: string | null = null;
	const frontpage = await db
		.selectFrom('generated_content')
		.select('content')
		.where('company_group_id', '=', group.id)
		.where('content_stage', '=', 'company_group_frontpage')
		.orderBy('created_at', 'desc')
		.limit(1)
		.executeTakeFirst();

	if (frontpage?.content) {
		latestAnalysisSummary = frontpage.content;
	} else {
		const analysis = await db
			.selectFrom('generated_content')
			.select('content')
			.where('company_group_id', '=', group.id)
			.where('content_stage', '=', 'company_group_analysis')
			.orderBy('created_at', 'desc')
			.limit(1)
			.executeTakeFirst();
		if (analysis?.content) {
			latestAnalysisSummary = analysis.content.slice(0, 500);
		}
	}

	return {
		id: group.id,
		name: group.name,
		slug: group.slug,
		description: group.description,
		sic_codes: group.sic_codes ?? [],
		member_count: members.length,
		created_at: toISOString(group.created_at),
		updated_at: toISOString(group.updated_at),
		companies,
		latest_analysis_summary: latestAnalysisSummary
	};
}

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	if (val == null) return '';
	return String(val);
}
