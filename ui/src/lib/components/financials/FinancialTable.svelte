<script lang="ts">
	import type { FinancialComparisonResponse, PeriodChange } from '$lib/api-types';
	import { formatFinancialValue, formatConceptName, formatPeriodDate } from '$lib/utils/financials';

	interface Props {
		financialData: FinancialComparisonResponse;
		statementType: string;
	}

	let { financialData, statementType }: Props = $props();

	let scrollContainer = $state<HTMLDivElement | null>(null);

	// Scroll to the right (newest periods) whenever filtered data changes
	$effect(() => {
		// Touch `filtered` to track it as a dependency
		const _items = filtered.items;
		if (scrollContainer) {
			// Use tick-like delay so the DOM has updated
			requestAnimationFrame(() => {
				if (scrollContainer) {
					scrollContainer.scrollLeft = scrollContainer.scrollWidth;
				}
			});
		}
	});

	// Filter items to the active statement type, sort periods old → new
	const filtered = $derived.by(() => {
		const items = financialData.items.filter((i) => i.labels.includes(statementType));
		const periods = [...financialData.periods].sort();

		// Rebuild values/changes in old→new order
		const sortedItems = items.map((item) => {
			const values = periods.map(
				(p) => item.values.find((v) => v.date === p) || { date: p, value: null }
			);

			const changes: PeriodChange[] = values.map((val, i) => {
				if (i === 0) {
					return { from_date: '', to_date: val.date, absolute: null, percent: null };
				}
				const prev = values[i - 1].value;
				const curr = val.value;
				if (curr !== null && prev !== null && prev !== 0) {
					const abs = curr - prev;
					const pct = (abs / Math.abs(prev)) * 100;
					return {
						from_date: values[i - 1].date,
						to_date: val.date,
						absolute: Math.round(abs * 100) / 100,
						percent: Math.round(pct * 100) / 100
					};
				}
				return {
					from_date: values[i - 1].date,
					to_date: val.date,
					absolute: null,
					percent: null
				};
			});

			return { ...item, values, changes };
		});

		return { periods, items: sortedItems };
	});
</script>

{#if filtered.items.length > 0}
	<div style="border: 1px solid var(--rule); border-radius: 8px; overflow: hidden;">
		<div style="overflow-x: auto;" bind:this={scrollContainer}>
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr style="border-bottom: 1px solid var(--rule);">
						<th class="sticky-col sticky-col-head"> $ millions </th>
						{#each filtered.periods as period, i (period)}
							<th
								style="text-align: right; padding: 1rem 1.75rem; font-size: 11px; font-family: var(--mono); letter-spacing: 0.08em; color: var(--ink-3); font-weight: 500; {i ===
								filtered.periods.length - 1
									? 'background: var(--sage-2);'
									: ''}"
							>
								{formatPeriodDate(period)}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each filtered.items as item, ri (item.concept_name)}
						<tr
							style="border-bottom: {ri < filtered.items.length - 1
								? '1px solid var(--rule)'
								: '0'};"
						>
							<td
								class="sticky-col"
								style="font-size: 14px; color: var(--ink-2);"
								title={item.concept_name}
							>
								{item.description || formatConceptName(item.concept_name)}
							</td>
							{#each item.values as pv, i (i)}
								<td
									style="padding: 0.875rem 1.75rem; font-size: 14px; font-family: var(--mono); text-align: right; color: var(--ink-2); {i ===
									item.values.length - 1
										? 'background: var(--sage-2);'
										: ''}"
								>
									{formatFinancialValue(pv.value)}
									{#if item.changes[i]?.percent !== null && item.changes[i]?.percent !== undefined}
										{@const pct = item.changes[i].percent!}
										<div
											style="font-size: 10px; color: {pct > 0
												? 'var(--teal-2)'
												: pct < 0
													? 'var(--danger)'
													: 'var(--ink-4)'};"
										>
											{pct > 0 ? '+' : ''}{pct.toFixed(1)}%
										</div>
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{:else}
	<p class="body-text" style="color: var(--ink-3); padding: 2rem 0; text-align: center;">
		No financial data available for this statement type.
	</p>
{/if}

<style>
	.sticky-col {
		position: sticky;
		left: 0;
		z-index: 1;
		background: var(--paper);
		padding: 0.875rem 1.75rem;
		box-shadow: 2px 0 4px -2px rgba(0, 0, 0, 0.06);
	}
	.sticky-col-head {
		z-index: 2;
		text-align: left;
		font-size: 11px;
		font-family: var(--mono);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--ink-3);
		font-weight: 500;
		padding: 1rem 1.75rem;
	}
</style>
