<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	// Better Auth redirects here with the validated token, or `?error=...` if the
	// link was invalid/expired.
	const token = page.url.searchParams.get('token') ?? '';
	const linkError = page.url.searchParams.get('error');

	let password = $state('');
	let confirm = $state('');
	let loading = $state(false);
	let errorMsg = $state('');

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		errorMsg = '';
		if (password !== confirm) {
			errorMsg = 'Passwords do not match.';
			return;
		}
		loading = true;
		const { error } = await authClient.resetPassword({ newPassword: password, token });
		loading = false;
		if (error) {
			errorMsg = error.message ?? 'Could not reset your password. The link may have expired.';
			return;
		}
		await goto('/login');
	}
</script>

<svelte:head><title>Reset password · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	<div class="eyebrow mb-3">● &nbsp;Password reset</div>
	<h1 class="display mb-8" style="font-size: 2.75rem;">Choose a new password.</h1>

	{#if linkError || !token}
		<div class="max-w-md">
			<p class="text-danger">This reset link is invalid or has expired.</p>
			<p class="mt-4 text-sm text-ink-3">
				<a href={resolve('/forgot-password')} class="text-teal-2 hover:underline">
					Request a new link
				</a>.
			</p>
		</div>
	{:else}
		<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">New password</span>
				<Input
					type="password"
					bind:value={password}
					required
					autocomplete="new-password"
					minlength={8}
				/>
				<span class="text-xs text-ink-4">At least 8 characters.</span>
			</label>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">Confirm new password</span>
				<Input type="password" bind:value={confirm} required autocomplete="new-password" />
			</label>

			{#if errorMsg}
				<p class="text-sm text-danger">{errorMsg}</p>
			{/if}

			<Button type="submit" disabled={loading} class="mt-2">
				{loading ? 'Saving…' : 'Reset password'}
			</Button>
		</form>
	{/if}
</div>
