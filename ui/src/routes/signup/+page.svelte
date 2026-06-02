<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let errorMsg = $state('');

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		errorMsg = '';
		const { error } = await authClient.signUp.email({ name, email, password });
		loading = false;
		if (error) {
			errorMsg = error.message ?? 'Could not create your account.';
			return;
		}
		await goto('/watchlist', { invalidateAll: true });
	}
</script>

<svelte:head><title>Create account · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	<div class="eyebrow mb-3">● &nbsp;Get started</div>
	<h1 class="display mb-8" style="font-size: 2.75rem;">Create your account.</h1>

	<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
		<label class="flex flex-col gap-1.5">
			<span class="text-sm text-ink-2">Name</span>
			<Input bind:value={name} required autocomplete="name" placeholder="Sam Kim" />
		</label>
		<label class="flex flex-col gap-1.5">
			<span class="text-sm text-ink-2">Email</span>
			<Input type="email" bind:value={email} required autocomplete="email" placeholder="you@example.com" />
		</label>
		<label class="flex flex-col gap-1.5">
			<span class="text-sm text-ink-2">Password</span>
			<Input type="password" bind:value={password} required autocomplete="new-password" minlength={8} />
			<span class="text-xs text-ink-4">At least 8 characters.</span>
		</label>

		{#if errorMsg}
			<p class="text-sm text-danger">{errorMsg}</p>
		{/if}

		<Button type="submit" disabled={loading} class="mt-2">
			{loading ? 'Creating account…' : 'Create account'}
		</Button>
	</form>

	<p class="mt-6 text-sm text-ink-3">
		Already have an account?
		<a href={resolve('/login')} class="text-teal-2 hover:underline">Sign in</a>.
	</p>
</div>
