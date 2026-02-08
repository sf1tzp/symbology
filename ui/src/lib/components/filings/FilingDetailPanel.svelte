<script lang="ts">
	import type {
		FilingTimelineResponse,
		CompanyResponse,
		FinancialComparisonResponse
	} from '$lib/api-types';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ExternalLink, FileText, Sparkles } from '@lucide/svelte';
	import { formatFilingPeriodLong, formatDate, getAnalysisTypeDisplay } from '$lib/utils/filings';
	import { getFinancialComparison } from '$lib/api';
	import { goto } from '$app/navigation';

	interface Props {
		filing: FilingTimelineResponse;
		company: CompanyResponse | null;
		financialComparison: FinancialComparisonResponse | null;
	}

	let { filing, company, financialComparison }: Props = $props();

	let localFinancials = $state<FinancialComparisonResponse | null>(financialComparison);
	let activeStatementType = $state('balance_sheet');
	let loadingFinancials = $state(false);

	// Reset financials when parent prop changes
	$effect(() => {
		localFinancials = financialComparison;
		activeStatementType = 'balance_sheet';
	});

	const statementTypes = [
		{ key: 'balance_sheet', label: 'Balance Sheet' },
		{ key: 'income_statement', label: 'Income Statement' },
		{ key: 'cash_flow', label: 'Cash Flow' }
	];

	async function switchStatementType(type: string) {
		if (type === activeStatementType || !company) return;
		activeStatementType = type;
		loadingFinancials = true;
		try {
			localFinancials = await getFinancialComparison(company.ticker, type);
		} catch {
			localFinancials = null;
		} finally {
			loadingFinancials = false;
		}
	}

	function formatFinancialValue(value: number | null): string {
		if (value === null || value === undefined) return '-';
		const abs = Math.abs(value);
		if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
		if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
		if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
		return value.toFixed(2);
	}

	function formatConceptName(name: string): string {
		return name
			.replace(/^us-gaap[_:]/, '')
			.replace(/([a-z])([A-Z])/g, '$1 $2')
			.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
	}

	function formatPeriodDate(dateStr: string): string {
		try {
			const d = new Date(dateStr + 'T00:00:00');
			return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
		} catch {
			return dateStr;
		}
	}

	const ticker = $derived(company?.ticker ?? '');
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div>
			<h2 class="text-xl font-semibold">
				{formatFilingPeriodLong(filing, company)}
			</h2>
			<div class="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
				<Badge variant="secondary">{filing.form}</Badge>
				<span>Filed {formatDate(filing.filing_date)}</span>
			</div>
		</div>
		{#if filing.url}
			<Button variant="outline" size="sm" href={filing.url} target="_blank">
				<ExternalLink class="mr-2 h-4 w-4" />
				View on SEC.gov
			</Button>
		{/if}
	</div>

	<!-- Two-column layout -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- Left: Financial Snapshot -->
		<Card>
			<CardHeader>
				<CardTitle class="text-base">Financial Snapshot</CardTitle>
			</CardHeader>
			<CardContent>
				{#if localFinancials && localFinancials.items.length > 0}
					<!-- Statement type tabs -->
					<div class="mb-4 flex space-x-1 rounded-lg bg-muted p-1">
						{#each statementTypes as st}
							<button
								class="flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors {activeStatementType ===
								st.key
									? 'bg-background text-foreground shadow-sm'
									: 'text-muted-foreground hover:text-foreground'}"
								onclick={() => switchStatementType(st.key)}
							>
								{st.label}
							</button>
						{/each}
					</div>

					{#if loadingFinancials}
						<div class="py-8 text-center text-sm text-muted-foreground">
							Loading financial data...
						</div>
					{:else}
						<div class="overflow-x-auto">
							<table class="w-full text-sm">
								<thead>
									<tr class="border-b">
										<th class="py-2 pr-4 text-left text-xs font-medium text-muted-foreground"
											>Concept</th
										>
										{#each localFinancials.periods as period}
											<th class="px-2 py-2 text-right text-xs font-medium text-muted-foreground"
												>{formatPeriodDate(period)}</th
											>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each localFinancials.items as item}
										<tr class="border-b border-border/50 hover:bg-muted/30">
											<td class="py-1.5 pr-4 text-xs" title={item.concept_name}>
												{item.description || formatConceptName(item.concept_name)}
											</td>
											{#each item.values as pv, i}
												<td class="px-2 py-1.5 text-right text-xs tabular-nums">
													{formatFinancialValue(pv.value)}
													{#if i < item.changes.length && item.changes[i].percent !== null}
														{@const pct = item.changes[i].percent}
														<div
															class="text-[10px] {pct !== null && pct > 0
																? 'text-green-600'
																: pct !== null && pct < 0
																	? 'text-red-600'
																	: 'text-muted-foreground'}"
														>
															{#if pct !== null}
																{pct > 0 ? '+' : ''}{pct.toFixed(1)}%
															{/if}
														</div>
													{/if}
												</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				{:else}
					<p class="py-4 text-center text-sm text-muted-foreground">
						No financial data available for this period.
					</p>
				{/if}
			</CardContent>
		</Card>

		<!-- Right: Documents & Analysis -->
		<Card>
			<CardHeader>
				<CardTitle class="text-base">Documents & Analysis</CardTitle>
			</CardHeader>
			<CardContent>
				{#if filing.documents.length > 0}
					<div class="space-y-3">
						{#each filing.documents as doc (doc.id)}
							{@const hasAnalysis = doc.generated_content.length > 0}

							<div class="rounded-lg border p-3 transition-colors hover:bg-muted/50">
								<div class="flex items-start justify-between gap-2">
									<div class="flex items-start gap-2">
										<FileText class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
										<div>
											<button
												class="text-left text-sm font-medium hover:underline"
												onclick={() => goto(`/d/${filing.accession_number}/${doc.short_hash}`)}
											>
												{getAnalysisTypeDisplay(doc.document_type || doc.title)}
											</button>
											{#if doc.short_hash}
												<div class="font-mono text-[10px] text-muted-foreground">
													{doc.short_hash}
												</div>
											{/if}
										</div>
									</div>
								</div>

								{#if hasAnalysis}
									<div class="mt-2 space-y-1 pl-6">
										{#each doc.generated_content as gc}
											<button
												class="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-primary transition-colors hover:bg-primary/10"
												onclick={() => goto(`/g/${ticker}/${gc.short_hash}`)}
											>
												<Sparkles class="h-3 w-3" />
												AI Analysis available
											</button>
										{/each}
									</div>
								{:else}
									<div class="mt-1 pl-6 text-xs text-muted-foreground">No analysis yet</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="py-4 text-center text-sm text-muted-foreground">
						No documents found in this filing.
					</p>
				{/if}
			</CardContent>
		</Card>
	</div>
</div>
