<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	// Pre-fill from the ?email= hint passed by the signup "check your inbox" state.
	let email = $state(page.url.searchParams.get('email') ?? '');
	let loading = $state(false);
	let note = $state('');
	let isError = $state(false);

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		note = '';
		const { error } = await authClient.sendVerificationEmail({
			email,
			callbackURL: '/a/watchlist'
		});
		loading = false;
		isError = !!error;
		note = error
			? (error.message ?? 'Could not send the verification email.')
			: 'Verification email sent — check your inbox.';
	}
</script>

<svelte:head><title>Verify your email · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	<div class="eyebrow mb-3">● &nbsp;Verify email</div>
	<h1 class="display mb-8" style="font-size: 2.75rem;">Resend verification.</h1>

	<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
		<p class="text-ink-2">
			Enter your email and we'll send a fresh verification link. Links expire after 24 hours.
		</p>
		<label class="flex flex-col gap-1.5">
			<span class="text-sm text-ink-2">Email</span>
			<Input
				type="email"
				bind:value={email}
				required
				autocomplete="email"
				placeholder="you@example.com"
			/>
		</label>

		{#if note}
			<p class="text-sm {isError ? 'text-danger' : 'text-ink-3'}">{note}</p>
		{/if}

		<Button type="submit" disabled={loading} class="mt-2">
			{loading ? 'Sending…' : 'Send verification email'}
		</Button>
	</form>

	<p class="mt-6 text-sm text-ink-3">
		Already verified?
		<a href={resolve('/login')} class="text-teal-2 hover:underline">Sign in</a>.
	</p>
</div>
