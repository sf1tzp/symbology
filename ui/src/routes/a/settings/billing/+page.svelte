<script lang="ts">
	import { resolve } from '$app/paths';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ExternalLink from '@lucide/svelte/icons/external-link';

	let { data } = $props();

	const fmtDate = (iso: string) =>
		new Date(iso).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});

	const planLabel = (plan: string) =>
		plan === 'one' ? 'One-time' : plan === 'duration' ? 'Pick your duration' : plan;
</script>

<svelte:head><title>Billing history · Symbology</title></svelte:head>

{#snippet stat(label: string, value: string | number)}
	<div class="min-w-0">
		<div class="font-mono text-[10.5px] tracking-[0.08em] text-ink-4 uppercase">{label}</div>
		<div class="mt-1.5 truncate font-serif text-[19px] text-ink">{value}</div>
	</div>
{/snippet}

<div class="page narrow mx-auto py-10">
	<a
		href={resolve('/a/settings')}
		class="meta mb-6 inline-flex items-center gap-1 text-ink-4 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3.5 w-3.5" /> Back to settings
	</a>

	<div class="mb-8">
		<div class="eyebrow mb-3">● &nbsp;Your account</div>
		<h1 class="display" style="font-size: 2.75rem;">Billing history.</h1>
		<p class="mt-3 max-w-[54ch] text-sm text-ink-3">
			Every supporter contribution on your account. These are one-time payments — there's no
			subscription to cancel.
		</p>
	</div>

	{#if data.grants.length > 0}
		<div class="flex flex-col gap-4">
			{#each data.grants as grant (grant.id)}
				<div class="rounded-2xl border border-rule-2 bg-paper p-5 sm:p-6">
					<div class="grid grid-cols-2 gap-x-5 gap-y-4 sm:grid-cols-3 lg:grid-cols-6">
						{@render stat('Date', fmtDate(grant.grantedAt))}
						{@render stat('Amount', `$${(grant.amountCents / 100).toLocaleString()}`)}
						{@render stat('Days', grant.days)}
						{@render stat('Plan', planLabel(grant.planType))}
						{@render stat('Active through', fmtDate(grant.expiresAt))}
						<div class="min-w-0">
							<div class="font-mono text-[10.5px] tracking-[0.08em] text-ink-4 uppercase">
								Receipt
							</div>
							{#if grant.receiptUrl}
								<a
									href={grant.receiptUrl}
									target="_blank"
									rel="noopener noreferrer"
									class="mt-1.5 inline-flex items-center gap-1 font-mono text-[13px] text-teal-2 no-underline transition-colors hover:text-ink"
								>
									View <ExternalLink class="h-3.5 w-3.5" />
								</a>
							{:else}
								<div class="mt-1.5 font-serif text-[19px] text-ink-4">—</div>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div
			class="grid items-start gap-5 rounded-2xl border border-teal-2 bg-paper p-7 text-center shadow-[0_0_0_1px_var(--teal-2)] sm:justify-items-start sm:text-left"
		>
			<div>
				<h2 class="section-heading text-2xl">No purchases yet.</h2>
				<p class="mt-2 max-w-[48ch] text-sm text-ink-2">
					You haven't made any supporter contributions. Become a supporter to unlock quarterly
					synthesis, full history, and the complete disclosure clusters.
				</p>
			</div>
			<a
				href="/support"
				class="inline-flex w-fit items-center gap-[7px] rounded-[10px] border border-teal-2 bg-teal-2 px-[18px] py-2.5 font-mono text-[13px] font-medium text-white no-underline transition-all hover:brightness-[1.06]"
				>Become a supporter</a
			>
		</div>
	{/if}
</div>
