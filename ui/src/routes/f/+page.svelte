<script lang="ts">
	import { ChevronRight, Sparkles } from '@lucide/svelte';
	import { titleCase } from 'title-case';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import BrowseList from '$lib/components/BrowseList.svelte';
	import { formatDate } from '$lib/utils/filings';
	import type { FilingListItem, FilingListResponse } from '$lib/api-types';

	async function fetchPage(skip: number, limit: number, search: string) {
		const params = new SvelteURLSearchParams({ skip: String(skip), limit: String(limit) });
		if (search) params.set('search', search);
		const res = await fetch(`/api/filings?${params}`);
		if (!res.ok) throw new Error('Failed to fetch filings');
		const data: FilingListResponse = await res.json();
		return { items: data.filings, total: data.total };
	}
</script>

<svelte:head>
	<title>Filings - Symbology</title>
	<meta name="description" content="Browse SEC filings synthesized by Symbology" />
</svelte:head>

{#snippet skeleton()}
	<div
		class="docrow grid grid-cols-[58px_1fr_24px] items-center sm:grid-cols-[80px_1fr_auto_24px]"
		aria-hidden="true"
	>
		<div><span class="block h-[18px] w-10 animate-pulse rounded bg-paper-2"></span></div>
		<div>
			<span class="block h-3.5 w-1/2 animate-pulse rounded bg-paper-2"></span>
			<span class="mt-1.5 block h-2.5 w-1/3 animate-pulse rounded bg-paper-2"></span>
		</div>
		<div class="hidden sm:block">
			<span class="block h-5 w-24 animate-pulse rounded bg-paper-2"></span>
		</div>
		<span class="block h-3.5 w-3.5 animate-pulse rounded bg-paper-2"></span>
	</div>
{/snippet}

{#snippet row(f: FilingListItem)}
	<a
		href="/f/{f.accession_number}"
		class="docrow grid grid-cols-[58px_1fr_24px] items-center text-inherit no-underline sm:grid-cols-[80px_1fr_auto_24px]"
	>
		<div><span class="tag">{f.form}</span></div>
		<div>
			<div class="text-sm font-medium text-ink">
				{titleCase((f.company_display_name || f.company_name).toLowerCase())}
			</div>
			<div class="mt-0.5 font-mono text-xs text-ink-4">
				{f.company_ticker}{#if f.filing_date}&nbsp;&middot;&nbsp;{formatDate(f.filing_date)}{/if}
			</div>
		</div>
		<div class="hidden sm:flex sm:justify-end">
			{#if f.has_analysis}
				<span
					class="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[11px] leading-none font-medium whitespace-nowrap text-teal-2"
					style="background: color-mix(in srgb, var(--teal-2) 12%, transparent); border: 1px solid color-mix(in srgb, var(--teal-2) 32%, transparent);"
				>
					<Sparkles size={11} strokeWidth={2} />
					Synthesis
				</span>
			{/if}
		</div>
		<ChevronRight class="h-3.5 w-3.5 text-ink-4" />
	</a>
{/snippet}

<BrowseList
	{fetchPage}
	{row}
	{skeleton}
	allLabel="All filings"
	searchPlaceholder="Company name, ticker, or form..."
	emptyLabel="No filings found."
/>
