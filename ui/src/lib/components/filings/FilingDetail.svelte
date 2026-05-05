<script lang="ts">
	import type { FilingResponse, CompanyResponse } from '$lib/api-types';
	import { Card, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ExternalLink } from '@lucide/svelte';

	interface Props {
		filing: FilingResponse;
		company?: CompanyResponse;
	}

	let { filing, company }: Props = $props();

	// Helper function to format dates
	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	// Helper function to get filing type label
	function getFilingTypeLabel(filingType: string): string {
		const labels: Record<string, string> = {
			'10-K': 'Annual Report',
			'10-Q': 'Quarterly Report',
			'8-K': 'Current Report',
			'DEF 14A': 'Proxy Statement',
			'S-1': 'Registration Statement',
			'20-F': 'Annual Report (Foreign)'
		};
		return labels[filingType] || filingType;
	}

	function formatYear(dateString: string): string {
		try {
			return new Date(dateString).getFullYear().toString();
		} catch {
			return dateString;
		}
	}

	// Prepare header display text
	const headerTitle = $derived(() => {
		const companyName = company?.display_name || company?.name || 'Company';
		const filingType = filing.form;
		const periodOfReport = filing.period_of_report;

		if (periodOfReport) {
			return `${format_filing_period(filing)}`;
		} else {
			return `${companyName} ${filingType}`;
		}
	});

	function format_filing_period(filing: FilingResponse) {
		let fye = company?.fiscal_year_end ? new Date(company.fiscal_year_end) : null;
		let reportDate = new Date(filing.period_of_report ?? filing.filing_date);

		try {
			const reportMonth = reportDate.getMonth() + 1; // getMonth returns 0-11
			const reportYear = reportDate.getFullYear();

			if (filing.form.includes('10-Q')) {
				// Determine quarter based on fiscal year end
				let quarter: number;
				let fiscalYear: number;

				if (fye) {
					// Parse fiscal year end (format like "1231" for Dec 31)
					const fyeMonth = fye.getMonth() + 1;
					const fyeDay = fye.getDay() + 1;

					// Calculate which fiscal year this report belongs to
					// If report date is after fiscal year end, it's the next fiscal year
					const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);
					const fyeLastYear = new Date(reportYear - 1, fyeMonth - 1, fyeDay);

					if (reportDate > fyeThisYear) {
						fiscalYear = reportYear + 1;
					} else if (reportDate > fyeLastYear) {
						fiscalYear = reportYear;
					} else {
						fiscalYear = reportYear - 1;
					}

					// Calculate quarter based on months from fiscal year end
					const monthsFromFYE = (reportMonth - fyeMonth + 12) % 12;
					if (monthsFromFYE >= 0 && monthsFromFYE < 3) {
						quarter = 1;
					} else if (monthsFromFYE < 6) {
						quarter = 2;
					} else if (monthsFromFYE < 9) {
						quarter = 3;
					} else {
						quarter = 4;
					}
				} else {
					// Fall back to calendar year quarters
					fiscalYear = reportYear;
					if (reportMonth <= 3) {
						quarter = 1;
					} else if (reportMonth <= 6) {
						quarter = 2;
					} else if (reportMonth <= 9) {
						quarter = 3;
					} else {
						quarter = 4;
					}
				}

				return `Fiscal Year ${fiscalYear} Q${quarter}`;
			}

			if (filing.form.includes('10-K')) {
				let fiscalYear = reportYear;

				// For 10-K, determine the fiscal year based on fiscal year end
				if (fye) {
					const fyeMonth = fye.getMonth() + 1;
					const fyeDay = fye.getDay();
					const fyeThisYear = new Date(reportYear, fyeMonth - 1, fyeDay);

					// If report date is close to fiscal year end, it's likely that fiscal year
					// Otherwise, it might be the previous fiscal year
					if (reportDate >= fyeThisYear) {
						fiscalYear = reportYear;
					} else {
						fiscalYear = reportYear;
					}
				}

				return `Fiscal Year ${fiscalYear}`;
			}
		} catch (error) {
			// If date parsing fails, fall back to original date string
			console.warn('Failed to parse filing date:', reportDate, error);
		}

		return reportDate;
	}
</script>

<div class="flex items-start justify-between">
	<div>
		<h1 class="text-xl font-bold">{headerTitle()}</h1>
		<div class="mt-2 flex flex-wrap items-center gap-2">
			<Badge variant="default">{company?.ticker}</Badge>
			<Badge variant="secondary">{filing.form}</Badge>
		</div>
	</div>
	{#if filing.url}
		<Button variant="outline" size="sm" href={filing.url} target="_blank">
			<ExternalLink class="mr-2 h-4 w-4" />
			View on sec.gov
		</Button>
	{/if}
</div>
