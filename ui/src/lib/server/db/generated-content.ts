import { db } from '../db';
import type { Selectable } from 'kysely';
import type {
	DiffSourceSide,
	DocumentResponse,
	GeneratedContentResponse,
	GeneratedContentSummaryResponse,
	ModelConfigResponse,
	PromptResponse
} from '$lib/api-types';
import type { DiffOp } from './diffs';
import type { GeneratedContent } from './types';

export async function getAggregateSummariesByTicker(
	ticker: string,
	limit: number = 5
): Promise<GeneratedContentResponse[]> {
	const rows = await db
		.selectFrom('generated_content as gc')
		.innerJoin('companies as c', 'c.id', 'gc.company_id')
		.selectAll('gc')
		.where('c.ticker', '=', ticker.toUpperCase())
		.where((eb) =>
			eb.or([
				eb('gc.content_stage', '=', 'aggregate_summary'),
				eb('gc.description', 'like', '%aggregate_summary%')
			])
		)
		.orderBy('gc.created_at', 'desc')
		.limit(limit)
		.execute();

	return Promise.all(rows.map((row) => toGeneratedContentResponse(row)));
}

export async function getAllGeneratedContentByTicker(
	ticker: string,
	limit: number = 100
): Promise<GeneratedContentSummaryResponse[]> {
	const rows = await db
		.selectFrom('generated_content as gc')
		.innerJoin('companies as c', 'c.id', 'gc.company_id')
		.select([
			'gc.id',
			'gc.content_hash',
			'gc.description',
			'gc.document_type',
			'gc.form_type',
			'gc.content_stage',
			'gc.summary',
			'gc.created_at'
		])
		.where('c.ticker', '=', ticker.toUpperCase())
		.orderBy('gc.created_at', 'desc')
		.limit(limit)
		.execute();

	return rows.map((row) => ({
		id: row.id,
		content_hash: row.content_hash,
		short_hash: row.content_hash?.slice(0, 12) ?? null,
		description: row.description,
		document_type: row.document_type,
		form_type: row.form_type,
		content_stage: row.content_stage,
		summary: row.summary,
		created_at: toISOString(row.created_at)
	}));
}

async function toGeneratedContentResponse(
	row: Selectable<GeneratedContent>
): Promise<GeneratedContentResponse> {
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
		company_group_id: row.company_group_id,
		description: row.description,
		document_type: row.document_type,
		content_stage: row.content_stage,
		generation_depth: row.generation_depth,
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
}

// Look up a synthesis by its content-hash prefix alone. The hash is the single
// canonical identifier for any piece of generated content regardless of scope
// (company / group / filing / document), so /s/[sha] needn't carry a ticker.
export async function getGeneratedContentByHash(
	hash: string
): Promise<GeneratedContentResponse | null> {
	const row = await db
		.selectFrom('generated_content')
		.selectAll()
		.where('content_hash', 'like', `${hash}%`)
		.executeTakeFirst();

	if (!row) return null;

	return toGeneratedContentResponse(row);
}

// Where a synthesis "belongs" — its subject scope, used for the back-link and
// the page's display name. Resolved from the content's own FKs rather than the
// URL, so group- and (future) other-scoped content works without a ticker.
export interface ContentScope {
	label: string;
	href: string | null;
}

export async function resolveContentScope(
	content: GeneratedContentResponse
): Promise<ContentScope> {
	if (content.company_id) {
		const company = await db
			.selectFrom('companies')
			.select(['ticker', 'name', 'display_name'])
			.where('id', '=', content.company_id)
			.executeTakeFirst();
		if (company) {
			return {
				label: company.display_name || company.name || company.ticker,
				href: `/c/${company.ticker}`
			};
		}
	}

	if (content.company_group_id) {
		const group = await db
			.selectFrom('company_groups')
			.select(['slug', 'name'])
			.where('id', '=', content.company_group_id)
			.executeTakeFirst();
		if (group) {
			return { label: group.name, href: `/groups/${group.slug}` };
		}
	}

	return { label: 'Symbology', href: null };
}

export async function getGeneratedContentById(
	id: string
): Promise<GeneratedContentResponse | null> {
	const row = await db
		.selectFrom('generated_content')
		.selectAll()
		.where('id', '=', id)
		.executeTakeFirst();

	if (!row) return null;

	return toGeneratedContentResponse(row);
}

export async function getModelConfigById(id: string): Promise<ModelConfigResponse | null> {
	const row = await db
		.selectFrom('model_configs')
		.selectAll()
		.where('id', '=', id)
		.executeTakeFirst();

	if (!row) return null;

	const options = row.options_json ? JSON.parse(row.options_json) : null;

	return {
		id: row.id,
		model: row.model,
		created_at: toISOString(row.created_at),
		options,
		max_tokens: options?.max_tokens ?? null,
		temperature: options?.temperature ?? null,
		top_k: options?.top_k ?? null,
		top_p: options?.top_p ?? null
	};
}

export async function getDocumentById(id: string): Promise<DocumentResponse | null> {
	const doc = await db
		.selectFrom('documents')
		.innerJoin('companies', 'companies.id', 'documents.company_id')
		.select([
			'documents.id',
			'documents.filing_id',
			'documents.title',
			'documents.document_type',
			'documents.content',
			'documents.content_hash',
			'companies.ticker as company_ticker'
		])
		.where('documents.id', '=', id)
		.executeTakeFirst();

	if (!doc) return null;

	// Fetch filing info if available
	let filing = null;
	if (doc.filing_id) {
		const f = await db
			.selectFrom('filings')
			.selectAll()
			.where('id', '=', doc.filing_id)
			.executeTakeFirst();
		if (f) {
			filing = {
				id: f.id,
				company_id: f.company_id,
				accession_number: f.accession_number,
				form: f.form,
				filing_date: toDateString(f.filing_date),
				url: f.url,
				period_of_report: f.period_of_report ? toDateString(f.period_of_report) : null
			};
		}
	}

	return {
		id: doc.id,
		filing_id: doc.filing_id,
		company_ticker: doc.company_ticker,
		title: doc.title,
		document_type: doc.document_type ?? 'unknown',
		content: doc.content,
		content_hash: doc.content_hash,
		short_hash: doc.content_hash?.slice(0, 12) ?? null,
		filing
	};
}

export async function getPromptById(id: string): Promise<PromptResponse | null> {
	const row = await db
		.selectFrom('prompts')
		.select(['id', 'name', 'description', 'role', 'content', 'content_hash'])
		.where('id', '=', id)
		.executeTakeFirst();

	if (!row) return null;

	return {
		id: row.id,
		name: row.name,
		description: row.description,
		role: row.role,
		content: row.content,
		content_hash: row.content_hash,
		short_hash: row.content_hash?.slice(0, 12) ?? null
	};
}

// One side's filing reference for the side-by-side DiffView (prior = left,
// current = right). Mirrors DiffView's `FilingRef` prop shape.
export interface TopicDiffFilingRef {
	form: string;
	filingDate: string | null;
	periodOfReport: string | null;
	accessionNumber: string;
	/** Short content hash of this side's document, for the /d deep link. */
	documentHash: string | null;
}

// Everything the /s/ viewer needs to render a topic-diff summary's sources as a
// proper side-by-side diff (via DiffView) rather than two plain-text cards:
//   - `topic` carries the raw token ops + change kind, fed straight to DiffView;
//   - `leftFiling`/`rightFiling` are the prior/current filing refs;
//   - `sides` is the flattened prior/current text retained for the sources
//     sidebar (labels + deep links + the source count).
export interface TopicDiffView {
	topic: {
		sectionPath: string | null;
		heading: string | null;
		changeKind: string;
		ops: DiffOp[];
		truncated: boolean;
	};
	leftFiling: TopicDiffFilingRef | null;
	rightFiling: TopicDiffFilingRef | null;
	sides: DiffSourceSide[];
}

// A topic-diff summary's true sources are the two texts it compared: the prior
// and current period versions of one disclosure topic. They aren't stored as
// association rows — they live as the token ops on the section_diff that points
// at this content. Return the raw ops (so the page can render them through the
// shared DiffView) alongside each side's filing ref, plus the flattened text
// halves the sources sidebar still uses. Returns null when this content isn't a
// topic-diff summary.
export async function getTopicDiffViewByContentId(
	contentId: string
): Promise<TopicDiffView | null> {
	const sd = await db
		.selectFrom('section_diffs as sd')
		.innerJoin('diff_sets as ds', 'ds.id', 'sd.diff_set_id')
		.select([
			'sd.ops',
			'sd.section_path',
			'sd.heading',
			'sd.change_kind',
			'sd.truncated',
			'ds.left_filing_id',
			'ds.right_filing_id',
			'ds.document_type'
		])
		.where('sd.summary_content_id', '=', contentId)
		.executeTakeFirst();

	if (!sd) return null;

	const ops = (sd.ops ?? []) as unknown as DiffOp[];
	const priorText = ops
		.filter((o) => o.op === 'equal' || o.op === 'delete')
		.map((o) => o.text)
		.join('');
	const currentText = ops
		.filter((o) => o.op === 'equal' || o.op === 'insert')
		.map((o) => o.text)
		.join('');

	// Resolve each filing's document of the diff's type for deep links + labels.
	const filingIds = [sd.left_filing_id, sd.right_filing_id].filter((x): x is string => !!x);
	const meta = new Map<string, TopicDiffFilingRef & { date: string | null }>();
	if (filingIds.length > 0) {
		const [filings, docs] = await Promise.all([
			db
				.selectFrom('filings')
				.select(['id', 'accession_number', 'form', 'filing_date', 'period_of_report'])
				.where('id', 'in', filingIds)
				.execute(),
			db
				.selectFrom('documents')
				.select(['filing_id', 'content_hash'])
				.where('filing_id', 'in', filingIds)
				.where('document_type', '=', sd.document_type)
				.execute()
		]);
		const hashByFiling = new Map<string, string>();
		for (const d of docs) {
			if (d.filing_id && d.content_hash && !hashByFiling.has(d.filing_id)) {
				hashByFiling.set(d.filing_id, d.content_hash.slice(0, 12));
			}
		}
		for (const f of filings) {
			meta.set(f.id, {
				accessionNumber: f.accession_number,
				documentHash: hashByFiling.get(f.id) ?? null,
				form: f.form,
				filingDate: f.filing_date ? toDateString(f.filing_date) : null,
				periodOfReport: f.period_of_report ? toDateString(f.period_of_report) : null,
				date: f.filing_date ? toDateString(f.filing_date) : null
			});
		}
	}

	const priorMeta = sd.left_filing_id ? (meta.get(sd.left_filing_id) ?? null) : null;
	const currentMeta = sd.right_filing_id ? (meta.get(sd.right_filing_id) ?? null) : null;

	const filingRef = (m: TopicDiffFilingRef | null): TopicDiffFilingRef | null =>
		m
			? {
					form: m.form,
					filingDate: m.filingDate,
					periodOfReport: m.periodOfReport,
					accessionNumber: m.accessionNumber,
					documentHash: m.documentHash
				}
			: null;

	const sideHref = (m: TopicDiffFilingRef | null): string | null =>
		m?.accessionNumber && m.documentHash ? `/d/${m.accessionNumber}/${m.documentHash}` : null;

	const sides: DiffSourceSide[] = [
		{
			label: 'Prior period',
			period: 'prior',
			text: priorText || '(not present in the prior filing)',
			href: sideHref(priorMeta),
			filingForm: priorMeta?.form ?? null,
			filingDate: priorMeta?.filingDate ?? null
		},
		{
			label: 'Current period',
			period: 'current',
			text: currentText || '(removed — not present in the current filing)',
			href: sideHref(currentMeta),
			filingForm: currentMeta?.form ?? null,
			filingDate: currentMeta?.filingDate ?? null
		}
	];

	return {
		topic: {
			sectionPath: sd.section_path,
			heading: sd.heading,
			changeKind: sd.change_kind,
			ops,
			truncated: sd.truncated
		},
		leftFiling: filingRef(priorMeta),
		rightFiling: filingRef(currentMeta),
		sides
	};
}

function toISOString(val: unknown): string {
	if (val instanceof Date) return val.toISOString();
	return String(val);
}

function toDateString(val: unknown): string {
	if (val instanceof Date) return val.toISOString().split('T')[0];
	return String(val).split('T')[0];
}
