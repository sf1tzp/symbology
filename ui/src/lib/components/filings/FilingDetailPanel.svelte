<script lang="ts">
	import type {
		FilingTimelineResponse,
		CompanyResponse,
		FinancialComparisonResponse,
		PeriodChange
	} from '$lib/api-types';
	import { ExternalLink, Sparkles } from '@lucide/svelte';
	import { formatFilingPeriodLong, formatDate, getAnalysisTypeDisplay } from '$lib/utils/filings';
	async function getFinancialComparison(
		ticker: string,
		statementType?: string
	): Promise<FinancialComparisonResponse | null> {
		const query = statementType ? `?statement_type=${encodeURIComponent(statementType)}` : '';
		const res = await fetch(`/api/financials/${encodeURIComponent(ticker)}${query}`);
		if (!res.ok) return null;
		return res.json();
	}
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

	// Derive filtered financials: old->new order, capped at selected filing's period
	const filteredFinancials = $derived.by(() => {
		if (!localFinancials) return null;

		const cutoff = filing.period_of_report;

		// Filter periods to only those <= selected filing's period, sort ascending (old -> new)
		const filteredPeriods = localFinancials.periods.filter((p) => !cutoff || p <= cutoff).sort();

		if (filteredPeriods.length === 0) return null;

		const filteredItems = localFinancials.items.map((item) => {
			// Build values array in old->new order
			const filteredValues = filteredPeriods.map(
				(period) => item.values.find((v) => v.date === period) || { date: period, value: null }
			);

			// Compute period-over-period changes for old->new order
			const changes: PeriodChange[] = filteredValues.map((val, i) => {
				if (i === 0) {
					return { from_date: '', to_date: val.date, absolute: null, percent: null };
				}
				const prev = filteredValues[i - 1].value;
				const curr = val.value;
				if (curr !== null && prev !== null && prev !== 0) {
					const abs = curr - prev;
					const pct = (abs / Math.abs(prev)) * 100;
					return {
						from_date: filteredValues[i - 1].date,
						to_date: val.date,
						absolute: Math.round(abs * 100) / 100,
						percent: Math.round(pct * 100) / 100
					};
				}
				return {
					from_date: filteredValues[i - 1].date,
					to_date: val.date,
					absolute: null,
					percent: null
				};
			});

			return { ...item, values: filteredValues, changes };
		});

		return { periods: filteredPeriods, items: filteredItems };
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

<div style="display: flex; flex-direction: column; gap: 1.5rem;">
	<!-- Header -->
	<div class="flex-between" style="align-items: flex-start;">
		<div>
			<h3 class="section-heading" style="font-size: 1.5rem;">
				{formatFilingPeriodLong(filing, company)}
			</h3>
			<div style="margin-top: 0.5rem; display: flex; align-items: center; gap: 0.75rem;">
				<span class="tag">{filing.form}</span>
				<span class="meta" style="color: var(--ink-3);">Filed {formatDate(filing.filing_date)}</span>
			</div>
		</div>
		{#if filing.url}
			<a
				href={filing.url}
				target="_blank"
				rel="noopener noreferrer"
				class="meta flex items-center gap-1.5 text-ink-3 no-underline transition-colors hover:text-ink"
			>
				<ExternalLink class="h-3.5 w-3.5" />
				View on SEC.gov
			</a>
		{/if}
	</div>

	<!-- Two-column layout -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- Left: Financial Snapshot -->
		<div style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
			<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1rem;">Financial Snapshot</h4>
				<!-- Statement type tabs (always show when financial data exists) -->
				{#if localFinancials}
					<div class="mb-4 flex space-x-1 rounded-lg bg-muted p-1">
						{#each statementTypes as st (st.key)}
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
				{/if}

				{#if loadingFinancials}
					<div class="py-8 text-center text-sm text-muted-foreground">
						Loading financial data...
					</div>
				{:else if filteredFinancials && filteredFinancials.items.length > 0}
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b">
									<th class="py-2 pr-4 text-left text-xs font-medium text-muted-foreground"
										>Concept</th
									>
									{#each filteredFinancials.periods as period (period)}
										<th class="px-2 py-2 text-right text-xs font-medium text-muted-foreground"
											>{formatPeriodDate(period)}</th
										>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each filteredFinancials.items as item (item.concept_name)}
									<tr class="border-b border-border/50 hover:bg-muted/30">
										<td class="py-1.5 pr-4 text-xs" title={item.concept_name}>
											{item.description || formatConceptName(item.concept_name)}
										</td>
										{#each item.values as pv, i (i)}
											<td class="px-2 py-1.5 text-right text-xs tabular-nums">
												{formatFinancialValue(pv.value)}
												{#if item.changes[i]?.percent !== null}
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
				{:else}
					<p class="py-4 text-center text-sm text-muted-foreground">
						No financial data available for this period.
					</p>
				{/if}
		</div>

		<!-- Right: Documents & Analysis -->
		<div style="border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem;">
			<h4 class="sub" style="font-size: 12px; color: var(--ink-2); margin-bottom: 1rem;">Documents & Analysis</h4>
			{#if filing.documents.length > 0}
				<div>
					{#each filing.documents as doc (doc.id)}
						{@const hasAnalysis = doc.generated_content.length > 0}
						<div class="docrow">
							<div>
								<button
									class="text-left text-sm font-medium transition-colors hover:text-teal-2"
									style="cursor: pointer; background: none; border: none; padding: 0; font-family: var(--sans);"
									onclick={() => goto(`/d/${filing.accession_number}/${doc.short_hash}`)}
								>
									{getAnalysisTypeDisplay(doc.document_type || doc.title)}
								</button>
								{#if doc.short_hash}
									<div class="meta" style="margin-top: 2px; color: var(--ink-4);">
										{doc.short_hash}
									</div>
								{/if}
							</div>
							<div>
								{#if hasAnalysis}
									{#each doc.generated_content as gc (gc.id)}
										<button
											class="tag-new tag"
											style="cursor: pointer; font-size: 10px; gap: 4px;"
											onclick={() => goto(`/g/${ticker}/${gc.short_hash}`)}
										>
											<Sparkles class="h-2.5 w-2.5" />
											Analysis
										</button>
									{/each}
								{:else}
									<span class="meta" style="color: var(--ink-4);">No analysis</span>
								{/if}
							</div>
							<div>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--ink-4);">
									<path d="m9 6 6 6-6 6"/>
								</svg>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
					No documents found in this filing.
				</p>
			{/if}
		</div>
	</div>
</div>
