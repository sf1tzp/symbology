<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { authClient } from '$lib/auth-client';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import SupporterCard from '$lib/components/SupporterCard.svelte';
	import SupporterBadges from '$lib/components/SupporterBadges.svelte';
	import { initials } from '$lib/nav';
	import { hints } from '$lib/state/hints.svelte';
	import type { BadgeKey } from '$lib/supporter-plans';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	let { data } = $props();

	// ── Hints preference ── (client-only, persisted in localStorage)
	$effect(() => {
		hints.load();
	});

	// ── Profile icon (avatar badge) ──
	// The choice persists in Better Auth's `user.avatarBadge` field; clearing it
	// ('') falls back to initials. Optimistic update, reverted on error.
	/* svelte-ignore state_referenced_locally */
	let selectedBadge = $state<BadgeKey | null>(data.avatarBadgeKey);
	let avatarSaving = $state(false);
	let avatarMsg = $state('');

	async function chooseAvatar(key: BadgeKey | null) {
		if (avatarSaving || key === selectedBadge) return;
		const prev = selectedBadge;
		selectedBadge = key;
		avatarSaving = true;
		avatarMsg = '';
		const { error } = await authClient.updateUser({ avatarBadge: key ?? '' });
		avatarSaving = false;
		if (error) {
			selectedBadge = prev;
			avatarMsg = error.message ?? 'Could not update your profile icon.';
			return;
		}
		await invalidateAll();
	}

	// ── Profile ── (editable form field, seeded from the loaded account)
	/* svelte-ignore state_referenced_locally */
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

<svelte:head><title>Settings · Symbology</title></svelte:head>

<div class="page narrow mx-auto py-10">
	<a
		href={resolve('/a/watchlist')}
		class="meta mb-6 inline-flex items-center gap-1 text-ink-4 no-underline transition-colors hover:text-ink"
	>
		<ChevronLeft class="h-3.5 w-3.5" /> Back to account
	</a>
	<div class="flex-between mb-8">
		<div>
			<div class="eyebrow mb-3">● &nbsp;Your account</div>
			<h1 class="display" style="font-size: 2.75rem;">Settings.</h1>
		</div>
		<Button variant="ghost" onclick={signOut}>Sign out</Button>
	</div>

	<!-- Supporter status -->
	<section class="mb-10">
		<SupporterCard supporter={data.supporter} />
		<a
			href={resolve('/a/settings/billing')}
			class="meta mt-4 inline-flex items-center gap-1 text-ink-4 no-underline transition-colors hover:text-ink"
		>
			Billing history <ChevronRight class="h-3.5 w-3.5" />
		</a>
	</section>

	{#if data.supporter.badges.length > 0}
		<Separator class="mb-10" />

		<!-- Profile icon: pick an earned badge, or keep initials -->
		<section class="mb-10">
			<h2 class="sub mb-2 text-ink-3">Profile icon</h2>
			<p class="mb-4 text-sm text-ink-3">
				Use one of your earned badges as your profile icon, or stick with your initials.
			</p>
			<SupporterBadges
				badges={data.supporter.badges}
				selectable
				selectedKey={selectedBadge}
				initials={initials(data.account.name)}
				busy={avatarSaving}
				onselect={chooseAvatar}
			/>
			{#if avatarMsg}<p class="mt-3 text-sm text-danger">{avatarMsg}</p>{/if}
		</section>
	{/if}

	<Separator class="mb-10" />

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

	<!-- Preferences -->
	<section class="max-w-md">
		<h2 class="sub mb-4 text-ink-3">Preferences</h2>
		<div class="flex items-center justify-between gap-6">
			<div>
				<div class="text-sm text-ink-2">Show hints</div>
				<p class="mt-1 text-sm text-ink-4">
					Occasional on-screen tips, like the mobile content-type switcher. Saved on this device.
				</p>
			</div>
			<button
				type="button"
				role="switch"
				aria-checked={!hints.disabled}
				aria-label="Show hints"
				onclick={() => hints.set(!hints.disabled)}
				class="relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors {hints.disabled
					? 'bg-border'
					: 'bg-teal-2'}"
			>
				<span
					class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {hints.disabled
						? 'translate-x-0.5'
						: 'translate-x-[1.125rem]'}"
				></span>
			</button>
		</div>
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
