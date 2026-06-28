/**
 * Human framing per generated-content stage. The /s viewer serves every kind of
 * synthesis (page intros, overviews, change syntheses, summaries), and the /s
 * browse index labels each row, so the mapping lives here for both to share.
 */
export const STAGE_LABELS: Record<string, { eyebrow: string; noun: string }> = {
	company_intro: { eyebrow: 'Company Introduction', noun: 'Introduction' },
	filing_intro: { eyebrow: 'Filing Introduction', noun: 'Introduction' },
	group_intro: { eyebrow: 'Group Introduction', noun: 'Introduction' },
	document_page_intro: { eyebrow: 'Document Introduction', noun: 'Introduction' },
	change_report_intro: { eyebrow: 'Change Report Introduction', noun: 'Introduction' },
	company_main_content: { eyebrow: 'Company Overview', noun: 'Overview' },
	filing_main_content: { eyebrow: 'Filing Overview', noun: 'Overview' },
	group_main_content: { eyebrow: 'Group Overview', noun: 'Overview' },
	change_report: { eyebrow: 'Change Report', noun: 'Change Report' },
	topic_diff_summary: { eyebrow: 'Change Synthesis', noun: 'Change Synthesis' },
	aggregate_summary: { eyebrow: 'Summary', noun: 'Summary' },
	single_summary: { eyebrow: 'Summary', noun: 'Summary' },
	frontpage_summary: { eyebrow: 'Summary', noun: 'Summary' },
	company_group_analysis: { eyebrow: 'Sector Analysis', noun: 'Analysis' },
	company_group_frontpage: { eyebrow: 'Sector Analysis', noun: 'Analysis' }
};

const FALLBACK = { eyebrow: 'Synthesis', noun: 'Synthesis' };

/** The {eyebrow, noun} framing for a content stage, falling back to "Synthesis". */
export function stageMeta(stage?: string | null): { eyebrow: string; noun: string } {
	return (stage && STAGE_LABELS[stage]) || FALLBACK;
}

/** The synthesis level (e.g. "L1", "L2") from a generation depth, or "" if none. */
export function synthesisLevel(depth?: number | null): string {
	return depth != null ? `L${depth}` : '';
}
