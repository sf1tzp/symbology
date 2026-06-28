<script lang="ts">
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let errorMsg = $state('');
	// Set once sign-up succeeds: verification is required, so there's no session
	// yet — we ask the user to confirm their email instead of entering the app.
	let submitted = $state(false);

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		errorMsg = '';
		// `callbackURL` is where Better Auth lands the user after they click the
		// verification link (auto-signed-in).
		const { error } = await authClient.signUp.email({
			name,
			email,
			password,
			callbackURL: '/a/watchlist'
		});
		loading = false;
		if (error) {
			errorMsg = error.message ?? 'Could not create your account.';
			return;
		}
		submitted = true;
	}
</script>

<svelte:head><title>Create account · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-12">
	{#if submitted}
		<div class="eyebrow mb-3">● &nbsp;Almost there</div>
		<h1 class="display mb-8" style="font-size: 2.75rem;">Check your inbox.</h1>
		<div class="max-w-md">
			<p class="text-ink-2">
				We sent a verification link to <span class="text-ink-1">{email}</span>. Click it to confirm
				your address and finish setting up your account.
			</p>
			<p class="mt-4 text-sm text-ink-3">
				Didn't get it? Check your spam folder, or
				<a
					href={resolve('/verify-email') + `?email=${encodeURIComponent(email)}`}
					class="text-teal-2 hover:underline">request a new link</a
				>.
			</p>
		</div>
	{:else}
		<div class="eyebrow mb-3">● &nbsp;Get started</div>
		<h1 class="display mb-8" style="font-size: 2.75rem;">Create your account.</h1>

		<form class="flex max-w-md flex-col gap-4" onsubmit={onSubmit}>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">Name</span>
				<Input bind:value={name} required autocomplete="name" placeholder="Sam Kim" />
			</label>
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
				<Input
					type="password"
					bind:value={password}
					required
					autocomplete="new-password"
					minlength={8}
				/>
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
	{/if}
</div>
