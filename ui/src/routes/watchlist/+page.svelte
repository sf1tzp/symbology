<script lang="ts">
	import { enhance } from '$app/forms';
	import { resolve } from '$app/paths';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';

	let { data } = $props();

	const watchedIds = $derived(new Set(data.watching.map((c) => c.company_id)));

	// ── Add-company search ──
	type SearchResult = { id: string; ticker: string; name: string; display_name: string | null };
	let adding = $state(false);
	let query = $state('');
	let results = $state<SearchResult[]>([]);
	let searching = $state(false);
	let searchToken = 0;

	async function runSearch() {
		const q = query.trim();
		if (q.length < 1) {
			results = [];
			return;
		}
		const token = ++searchToken;
		searching = true;
		try {
			const res = await fetch(`/api/companies?search=${encodeURIComponent(q)}&limit=8`);
			const body = res.ok ? await res.json() : { companies: [] };
			if (token === searchToken) results = body.companies ?? [];
		} finally {
			if (token === searchToken) searching = false;
		}
	}

	let debounce: ReturnType<typeof setTimeout> | undefined;
	function onInput() {
		clearTimeout(debounce);
		debounce = setTimeout(runSearch, 200);
	}

	function closeAdd() {
		adding = false;
		query = '';
		results = [];
	}
</script>

<svelte:head><title>Watchlist · Symbology</title></svelte:head>

<div class="page">
	<!-- Header -->
	<section class="grid items-end gap-12 md:grid-cols-2">
		<div>
			<div class="eyebrow mb-3.5">
				● &nbsp;Your watchlist · {data.watching.length}
				{data.watching.length === 1 ? 'company' : 'companies'}
			</div>
			<h1 class="display mb-5" style="font-size: 3.5rem;">
				Good morning,<br /><em>{data.firstName}.</em>
			</h1>
			<p class="lede text-ink-2">
				{#if data.watching.length === 0}
					Your watchlist is empty. Add a company to start tracking its filings and analysis.
				{:else}
					Here's what you're tracking. The change feed and filing calendar are coming soon.
				{/if}
			</p>
		</div>
		<div class="grid grid-cols-3 gap-4">
			<div class="stat">
				<div class="stat-label">Watching</div>
				<div class="stat-value">{data.watching.length}</div>
				<div class="meta text-ink-4">Active</div>
			</div>
			<div class="stat">
				<div class="stat-label">New filings</div>
				<div class="stat-value text-ink-4">—</div>
				<div class="meta text-ink-4">Coming soon</div>
			</div>
			<div class="stat">
				<div class="stat-label">Material changes</div>
				<div class="stat-value text-ink-4">—</div>
				<div class="meta text-ink-4">Coming soon</div>
			</div>
		</div>
	</section>

	<!-- Feed + Watching -->
	<section class="hairline-section">
		<div class="grid items-start gap-12 md:grid-cols-2">
			<!-- What changed (placeholder) -->
			<div>
				<h3 class="sub mb-5 text-ink-3">What changed</h3>
				<div class="rounded-lg border border-dashed border-rule p-8 text-center">
					<p class="text-sm text-ink-3">
						A feed of new filings and material changes across your watchlist will appear here.
					</p>
					<p class="meta mt-2 text-ink-4">Coming soon</p>
				</div>
			</div>

			<!-- Watching list -->
			<div>
				<div class="flex-between mb-5">
					<h3 class="sub text-ink-3">Watching</h3>
					{#if adding}
						<Button variant="ghost" size="sm" onclick={closeAdd}>
							<X class="h-3.5 w-3.5" /> Close
						</Button>
					{:else}
						<Button variant="ghost" size="sm" onclick={() => (adding = true)}>
							<Plus class="h-3.5 w-3.5" /> Add company
						</Button>
					{/if}
				</div>

				{#if adding}
					<div class="mb-4">
						<Input
							bind:value={query}
							oninput={onInput}
							placeholder="Search companies by ticker or name…"
							autofocus
						/>
						{#if query.trim().length > 0}
							<div class="mt-2 overflow-hidden rounded-lg border border-rule">
								{#if searching && results.length === 0}
									<p class="px-3 py-2 text-sm text-ink-4">Searching…</p>
								{:else if results.length === 0}
									<p class="px-3 py-2 text-sm text-ink-4">No matches.</p>
								{:else}
									{#each results as r (r.id)}
										<form
											method="POST"
											action="?/add"
											use:enhance={() => {
												return async ({ update }) => {
													await update();
													closeAdd();
												};
											}}
										>
											<input type="hidden" name="companyId" value={r.id} />
											<button
												type="submit"
												disabled={watchedIds.has(r.id)}
												class="flex w-full items-center gap-3 border-b border-rule px-3 py-2 text-left last:border-b-0 hover:bg-paper-2 disabled:opacity-40"
											>
												<span class="tag tag-solid">{r.ticker}</span>
												<span class="flex-1 truncate text-sm text-ink"
													>{r.display_name ?? r.name}</span
												>
												{#if watchedIds.has(r.id)}
													<span class="meta text-ink-4">Watching</span>
												{:else}
													<Plus class="h-3.5 w-3.5 text-ink-3" />
												{/if}
											</button>
										</form>
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				{/if}

				{#if data.watching.length === 0}
					<p class="py-6 text-sm text-ink-3">Nothing here yet.</p>
				{:else}
					<div>
						{#each data.watching as c (c.company_id)}
							<div class="flex items-center gap-3 border-b border-rule py-4 last:border-b-0">
								<a href={resolve(`/c/${c.ticker}`)} class="contents">
									<span class="tag tag-solid">{c.ticker}</span>
									<div class="min-w-0 flex-1">
										<div class="truncate font-serif text-base text-ink">
											{c.display_name ?? c.name}
										</div>
										{#if c.sic_description}
											<div class="meta mt-0.5 truncate text-ink-3">{c.sic_description}</div>
										{/if}
									</div>
								</a>
								<form
									method="POST"
									action="?/remove"
									use:enhance={() => {
										return async ({ update }) => update();
									}}
								>
									<input type="hidden" name="companyId" value={c.company_id} />
									<Button type="submit" variant="ghost" size="sm" title="Remove from watchlist">
										<X class="h-3.5 w-3.5" />
									</Button>
								</form>
								<a href={resolve(`/c/${c.ticker}`)} class="text-ink-4 hover:text-ink">
									<ChevronRight class="h-4 w-4" />
								</a>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</section>

	<!-- Upcoming filings (placeholder) -->
	<section class="hairline-section">
		<div class="eyebrow mb-2.5">● &nbsp;Upcoming filings · next 60 days</div>
		<h2 class="section-heading mb-6">On the calendar.</h2>
		<div class="rounded-lg border border-dashed border-rule p-8 text-center">
			<p class="text-sm text-ink-3">
				Estimated filing dates for the companies you watch will appear here.
			</p>
			<p class="meta mt-2 text-ink-4">Coming soon</p>
		</div>
	</section>
</div>
