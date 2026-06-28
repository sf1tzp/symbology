/**
 * A filing reduced to the fields the period formatters read. `period_of_report`
 * is optional (`?`) so it accepts objects from the generated API types, where it
 * may be absent; the formatters treat absent / null / empty alike (fall back to
 * the form label).
 */
export type FilingPeriod = { form: string; period_of_report?: string | null };

/** A company reduced to the field the period formatters read. */
export type CompanyFiscalYearEnd = { fiscal_year_end?: string | null };

/**
 * Format a filing's period into a human-readable fiscal period label.
 * Handles both 10-K (annual) and 10-Q (quarterly) filings.
 */
export function formatFilingPeriod(
	filing: FilingPeriod,
	company: CompanyFiscalYearEnd | null
): string {
	if (!filing.period_of_report) return filing.form;

	const fye = company?.fiscal_year_end ? new Date(company.fiscal_year_end) : null;
	const reportDate = new Date(filing.period_of_report);

	try {
		const reportMonth = reportDate.getMonth() + 1;
		const reportYear = reportDate.getFullYear();

		if (filing.form.includes('10-Q')) {
			let quarter: number;
			let fiscalYear: number;

			if (fye) {
				const fyeMonth = fye.getMonth() + 1;
				const fyeDay = fye.getDate();

				const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);
				const fyeLastYear = new Date(reportYear - 1, fyeMonth - 1, fyeDay);

				if (reportDate > fyeThisYear) {
					fiscalYear = reportYear + 1;
				} else if (reportDate > fyeLastYear) {
					fiscalYear = reportYear;
				} else {
					fiscalYear = reportYear - 1;
				}

				const monthsFromFYE = (reportMonth - fyeMonth + 12) % 12;
				if (monthsFromFYE < 3) {
					quarter = 1;
				} else if (monthsFromFYE < 6) {
					quarter = 2;
				} else if (monthsFromFYE < 9) {
					quarter = 3;
				} else {
					quarter = 4;
				}
			} else {
				fiscalYear = reportYear;
				if (reportMonth <= 3) quarter = 1;
				else if (reportMonth <= 6) quarter = 2;
				else if (reportMonth <= 9) quarter = 3;
				else quarter = 4;
			}

			return `FY ${fiscalYear} Q${quarter}`;
		}

		if (filing.form.includes('10-K')) {
			return `FY ${reportYear}`;
		}
	} catch (error) {
		console.warn('Failed to parse filing date:', filing.period_of_report, error);
	}

	return reportDate.toLocaleDateString();
}

/**
 * Format a filing period as a longer label (e.g. "Fiscal Year 2024 Q1")
 */
export function formatFilingPeriodLong(
	filing: FilingPeriod,
	company: CompanyFiscalYearEnd | null
): string {
	if (!filing.period_of_report) return filing.form;

	const fye = company?.fiscal_year_end ? new Date(company.fiscal_year_end) : null;
	const reportDate = new Date(filing.period_of_report);

	try {
		const reportMonth = reportDate.getMonth() + 1;
		const reportYear = reportDate.getFullYear();

		if (filing.form.includes('10-Q')) {
			let quarter: number;
			let fiscalYear: number;

			if (fye) {
				const fyeMonth = fye.getMonth() + 1;
				const fyeDay = fye.getDate();

				const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);
				const fyeLastYear = new Date(reportYear - 1, fyeMonth - 1, fyeDay);

				if (reportDate > fyeThisYear) {
					fiscalYear = reportYear + 1;
				} else if (reportDate > fyeLastYear) {
					fiscalYear = reportYear;
				} else {
					fiscalYear = reportYear - 1;
				}

				const monthsFromFYE = (reportMonth - fyeMonth + 12) % 12;
				if (monthsFromFYE < 3) quarter = 1;
				else if (monthsFromFYE < 6) quarter = 2;
				else if (monthsFromFYE < 9) quarter = 3;
				else quarter = 4;
			} else {
				fiscalYear = reportYear;
				if (reportMonth <= 3) quarter = 1;
				else if (reportMonth <= 6) quarter = 2;
				else if (reportMonth <= 9) quarter = 3;
				else quarter = 4;
			}

			return `Fiscal Year ${fiscalYear} Q${quarter}`;
		}

		if (filing.form.includes('10-K')) {
			return `Fiscal Year ${reportYear}`;
		}
	} catch (error) {
		console.warn('Failed to parse filing date:', filing.period_of_report, error);
	}

	return reportDate.toLocaleDateString();
}

/**
 * Get human-readable display name for a document/analysis type.
 */
export function getAnalysisTypeDisplay(documentType: string): string {
	const type = documentType?.toLowerCase() ?? '';

	if (type.includes('management_discussion')) return 'Management Discussion';
	if (type.includes('risk_factors')) return 'Risk Factors';
	if (type.includes('business_description')) return 'Business Description';
	if (type.includes('controls_procedures')) return 'Controls & Procedures';
	if (type.includes('legal_proceedings')) return 'Legal Proceedings';
	if (type.includes('market_risk')) return 'Market Risk';
	if (type.includes('executive_compensation')) return 'Executive Compensation';
	if (type.includes('directors_officers')) return 'Directors & Officers';
	if (type.includes('aggregate_summary')) return 'Change Synthesis';

	return documentType;
}

/**
 * Strip a provider prefix from a model identifier, returning only the part
 * after the last '/'. Models without a prefix (e.g. "claude-sonnet") are
 * returned unchanged.
 */
export function shortModelName(model: string): string {
	return model.split('/').pop() || model;
}

/**
 * Format an ISO date string for display.
 */
export function formatDate(dateString: string): string {
	try {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	} catch {
		return dateString;
	}
}

/**
 * Clean content by removing <think> tags and internal reasoning patterns.
 */
export function cleanContent(content: string | undefined): string | undefined {
	if (!content) return undefined;

	let cleaned = content.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

	cleaned = cleaned.replace(
		/^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
		''
	);

	cleaned = cleaned.trim();
	return cleaned || undefined;
}
