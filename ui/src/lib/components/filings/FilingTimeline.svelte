<script lang="ts">
	import type { FilingTimelineResponse, CompanyResponse } from '$lib/api-types';
	import { Badge } from '$lib/components/ui/badge';
	import { formatFilingPeriod } from '$lib/utils/filings';
	import { ChevronLeft, ChevronRight } from '@lucide/svelte';

	interface Props {
		filings: FilingTimelineResponse[];
		company: CompanyResponse | null;
		selectedId: string;
		onselect: (filing: FilingTimelineResponse) => void;
	}

	let { filings, company, selectedId, onselect }: Props = $props();

	let scrollContainer = $state<HTMLDivElement | null>(null);

	function scrollLeft() {
		scrollContainer?.scrollBy({ left: -200, behavior: 'smooth' });
	}

	function scrollRight() {
		scrollContainer?.scrollBy({ left: 200, behavior: 'smooth' });
	}

	function isAnnual(form: string): boolean {
		return form.includes('10-K');
	}
</script>

<div class="relative flex items-center gap-2">
	<!-- Left scroll arrow -->
	{#if filings.length > 4}
		<button
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
			onclick={scrollLeft}
			aria-label="Scroll timeline left"
		>
			<ChevronLeft class="h-4 w-4" />
		</button>
	{/if}

	<!-- Timeline container -->
	<div class="scrollbar-thin flex-1 overflow-x-auto" bind:this={scrollContainer}>
		<div class="flex items-center gap-0 px-2 py-4" style="min-width: max-content;">
			{#each filings as filing, i (filing.id)}
				{@const isSelected = filing.id === selectedId}
				{@const annual = isAnnual(filing.form)}

				<!-- Connecting line (before node, except first) -->
				{#if i > 0}
					<div class="h-0.5 w-8 bg-border sm:w-12"></div>
				{/if}

				<!-- Filing node -->
				<button
					class="group flex flex-col items-center gap-1.5 rounded-lg px-3 py-2 transition-colors {isSelected
						? 'bg-accent'
						: 'hover:bg-muted/50'}"
					onclick={() => onselect(filing)}
					aria-label="Select {filing.form} filing for {formatFilingPeriod(filing, company)}"
					aria-pressed={isSelected}
				>
					<!-- Dot marker -->
					<div
						class="rounded-full transition-all {annual ? 'h-4 w-4' : 'h-3 w-3'} {isSelected
							? 'bg-primary ring-2 ring-primary/30'
							: 'border-2 border-muted-foreground/40 group-hover:border-primary/60'}"
					></div>

					<!-- Form badge -->
					<Badge
						variant={annual ? 'default' : 'secondary'}
						class="text-[10px] {isSelected ? 'ring-1 ring-primary/40' : ''}"
					>
						{filing.form}
					</Badge>

					<!-- Period label -->
					<span
						class="text-xs whitespace-nowrap {isSelected
							? 'font-semibold text-foreground'
							: 'text-muted-foreground'}"
					>
						{formatFilingPeriod(filing, company)}
					</span>
				</button>
			{/each}
		</div>
	</div>

	<!-- Right scroll arrow -->
	{#if filings.length > 4}
		<button
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
			onclick={scrollRight}
			aria-label="Scroll timeline right"
		>
			<ChevronRight class="h-4 w-4" />
		</button>
	{/if}
</div>
