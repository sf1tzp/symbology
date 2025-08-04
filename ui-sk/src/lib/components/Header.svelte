<!-- Header.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { toggleMode } from 'mode-watcher';
	import { Button } from '$lib/components/ui/button';

	function handleHomeClick() {
		goto('/');
	}
</script>

<header class="bg-card flex flex-col items-center border-b p-4">
	<div class="flex w-full flex-col items-center gap-2">
		<img
			src="https://i.imgur.com/UeEDuUi.png"
			alt="Symbology Logo"
			class="h-auto max-w-[240px] rounded md:max-w-[80px]"
		/>
		<button
			class="focus:outline-primary cursor-pointer border-none bg-transparent p-0 transition-opacity hover:opacity-80 focus:outline-2 focus:outline-offset-2"
			onclick={handleHomeClick}
			onkeydown={(e) => e.key === 'Enter' && handleHomeClick()}
		>
			<h1 class="text-primary m-0 text-center text-2xl font-bold tracking-wide md:text-xl">
				Symbology
			</h1>
		</button>
	</div>

	<Button variant="ghost" size="sm" class="mt-2" onclick={toggleMode} aria-label="Toggle theme">
		<span class="text-lg">🌙</span>
		<span class="ml-2 text-sm">Toggle Theme</span>
	</Button>
</header>
