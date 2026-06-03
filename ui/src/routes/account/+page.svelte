<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';

	let { data } = $props();

	// ── Profile ──
	let name = $state(data.account.name);
	let profileSaving = $state(false);
	let profileMsg = $state('');

	async function saveProfile(e: SubmitEvent) {
		e.preventDefault();
		profileSaving = true;
		profileMsg = '';
		const { error } = await authClient.updateUser({ name });
		profileSaving = false;
		if (error) {
			profileMsg = error.message ?? 'Could not save changes.';
			return;
		}
		profileMsg = 'Saved.';
		await invalidateAll();
	}

	// ── Change password ──
	let currentPassword = $state('');
	let newPassword = $state('');
	let pwSaving = $state(false);
	let pwMsg = $state('');

	async function changePassword(e: SubmitEvent) {
		e.preventDefault();
		pwSaving = true;
		pwMsg = '';
		const { error } = await authClient.changePassword({
			currentPassword,
			newPassword,
			revokeOtherSessions: true
		});
		pwSaving = false;
		if (error) {
			pwMsg = error.message ?? 'Could not change password.';
			return;
		}
		pwMsg = 'Password updated.';
		currentPassword = '';
		newPassword = '';
	}

	// ── Sign out ──
	async function signOut() {
		await authClient.signOut();
		await goto('/', { invalidateAll: true });
	}

	// ── Delete account ──
	let confirmingDelete = $state(false);
	let deletePassword = $state('');
	let deleting = $state(false);
	let deleteMsg = $state('');

	async function deleteAccount() {
		deleting = true;
		deleteMsg = '';
		const { error } = await authClient.deleteUser({ password: deletePassword });
		deleting = false;
		if (error) {
			deleteMsg = error.message ?? 'Could not delete account.';
			return;
		}
		await goto('/', { invalidateAll: true });
	}
</script>

<svelte:head><title>Account · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-10">
	<div class="flex-between mb-8">
		<div>
			<div class="eyebrow mb-3">● &nbsp;Your account</div>
			<h1 class="display" style="font-size: 2.75rem;">Account.</h1>
		</div>
		<Button variant="ghost" onclick={signOut}>Sign out</Button>
	</div>

	<!-- Profile -->
	<section class="max-w-md">
		<h2 class="sub mb-4 text-ink-3">Profile</h2>
		<form class="flex flex-col gap-4" onsubmit={saveProfile}>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">Name</span>
				<Input bind:value={name} required autocomplete="name" />
			</label>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">Email</span>
				<Input value={data.account.email} readonly disabled />
			</label>
			{#if profileMsg}<p class="text-sm text-ink-3">{profileMsg}</p>{/if}
			<Button type="submit" disabled={profileSaving} class="mt-1 self-start">
				{profileSaving ? 'Saving…' : 'Save'}
			</Button>
		</form>
	</section>

	<Separator class="my-10" />

	<!-- Change password -->
	<section class="max-w-md">
		<h2 class="sub mb-4 text-ink-3">Change password</h2>
		<form class="flex flex-col gap-4" onsubmit={changePassword}>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">Current password</span>
				<Input
					type="password"
					bind:value={currentPassword}
					required
					autocomplete="current-password"
				/>
			</label>
			<label class="flex flex-col gap-1.5">
				<span class="text-sm text-ink-2">New password</span>
				<Input
					type="password"
					bind:value={newPassword}
					required
					autocomplete="new-password"
					minlength={8}
				/>
			</label>
			{#if pwMsg}<p class="text-sm text-ink-3">{pwMsg}</p>{/if}
			<Button type="submit" disabled={pwSaving} class="mt-1 self-start">
				{pwSaving ? 'Updating…' : 'Update password'}
			</Button>
		</form>
	</section>

	<Separator class="my-10" />

	<!-- Delete account -->
	<section class="max-w-md">
		<h2 class="sub mb-2 text-danger">Danger zone</h2>
		<p class="mb-4 text-sm text-ink-3">
			Deleting your account is permanent and removes your watchlist.
		</p>
		{#if deleteMsg}<p class="mb-3 text-sm text-danger">{deleteMsg}</p>{/if}
		{#if confirmingDelete}
			<form
				class="flex flex-col gap-3"
				onsubmit={(e) => {
					e.preventDefault();
					deleteAccount();
				}}
			>
				<label class="flex flex-col gap-1.5">
					<span class="text-sm text-ink-2">Confirm your password</span>
					<Input
						type="password"
						bind:value={deletePassword}
						required
						autocomplete="current-password"
					/>
				</label>
				<div class="flex items-center gap-3">
					<Button type="submit" variant="destructive" disabled={deleting}>
						{deleting ? 'Deleting…' : 'Yes, delete my account'}
					</Button>
					<Button
						type="button"
						variant="ghost"
						disabled={deleting}
						onclick={() => {
							confirmingDelete = false;
							deletePassword = '';
						}}
					>
						Cancel
					</Button>
				</div>
			</form>
		{:else}
			<Button variant="destructive" onclick={() => (confirmingDelete = true)}>Delete account</Button
			>
		{/if}
	</section>
</div>
