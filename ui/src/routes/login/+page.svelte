<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let errorMsg = $state('');
	// True when the sign-in failed because the email isn't verified — we then
	// offer to resend the verification link rather than just showing an error.
	let needsVerification = $state(false);
	let resendNote = $state('');

	function redirectTarget(): string {
		const to = page.url.searchParams.get('returnTo');
		// Only allow same-site relative paths.
		return to && to.startsWith('/') ? to : '/a/watchlist';
	}

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		errorMsg = '';
		needsVerification = false;
		resendNote = '';
		const { error } = await authClient.signIn.email({ email, password });
		loading = false;
		if (error) {
			if (error.code === 'EMAIL_NOT_VERIFIED') {
				needsVerification = true;
				errorMsg = 'Please verify your email before signing in.';
			} else {
				errorMsg = error.message ?? 'Could not sign in. Check your email and password.';
			}
			return;
		}
		await goto(redirectTarget(), { invalidateAll: true });
	}

	async function resendVerification() {
		resendNote = '';
		const { error } = await authClient.sendVerificationEmail({
			email,
			callbackURL: '/a/watchlist'
		});
		resendNote = error
			? (error.message ?? 'Could not send the verification email.')
			: 'Verification email sent — check your inbox.';
	}
</script>

<svelte:head><title>Sign in · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	<div class="eyebrow mb-3">● &nbsp;Welcome back</div>
	<h1 class="display mb-8" style="font-size: 2.75rem;">Sign in.</h1>

	<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
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
		<label class="flex flex-col gap-1.5">
			<span class="text-sm text-ink-2">Password</span>
			<Input type="password" bind:value={password} required autocomplete="current-password" />
		</label>

		<a href={resolve('/forgot-password')} class="text-sm text-teal-2 hover:underline">
			Forgot password?
		</a>

		{#if errorMsg}
			<p class="text-sm text-danger">{errorMsg}</p>
		{/if}

		{#if needsVerification}
			<p class="text-sm text-ink-3">
				<button type="button" class="text-teal-2 hover:underline" onclick={resendVerification}>
					Resend verification email
				</button>
			</p>
		{/if}

		{#if resendNote}
			<p class="text-sm text-ink-3">{resendNote}</p>
		{/if}

		<Button type="submit" disabled={loading} class="mt-2">
			{loading ? 'Signing in…' : 'Sign in'}
		</Button>
	</form>

	<p class="mt-6 text-sm text-ink-3">
		No account?
		<a href={resolve('/signup')} class="text-teal-2 hover:underline">Create one</a>.
	</p>
</div>
