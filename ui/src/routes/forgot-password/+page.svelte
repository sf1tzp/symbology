<script lang="ts">
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let email = $state('');
	let loading = $state(false);
	let errorMsg = $state('');
	let submitted = $state(false);

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		errorMsg = '';
		// redirectTo is where Better Auth lands the user after they click the link;
		// it forwards the token as a `?token=` query param to /reset-password.
		const { error } = await authClient.requestPasswordReset({
			email,
			redirectTo: '/reset-password'
		});
		loading = false;
		if (error) {
			errorMsg = error.message ?? 'Could not send the reset email.';
			return;
		}
		submitted = true;
	}
</script>

<svelte:head><title>Forgot password · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	{#if submitted}
		<div class="eyebrow mb-3">● &nbsp;Check your inbox</div>
		<h1 class="display mb-8" style="font-size: 2.75rem;">Reset link sent.</h1>
		<p class="max-w-md text-ink-2">
			If an account exists for <span class="text-ink-1">{email}</span>, we've sent a link to reset
			your password. It expires in 1 hour.
		</p>
	{:else}
		<div class="eyebrow mb-3">● &nbsp;Password reset</div>
		<h1 class="display mb-8" style="font-size: 2.75rem;">Forgot your password?</h1>

		<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
			<p class="text-ink-2">Enter your email and we'll send you a link to choose a new password.</p>
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

			{#if errorMsg}
				<p class="text-sm text-danger">{errorMsg}</p>
			{/if}

			<Button type="submit" disabled={loading} class="mt-2">
				{loading ? 'Sending…' : 'Send reset link'}
			</Button>
		</form>

		<p class="mt-6 text-sm text-ink-3">
			Remembered it?
			<a href={resolve('/login')} class="text-teal-2 hover:underline">Sign in</a>.
		</p>
	{/if}
</div>
