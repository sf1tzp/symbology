<!-- Header.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { toggleMode } from 'mode-watcher';
	import { Button } from '$lib/components/ui/button';

	function handleHomeClick() {
		goto('/');
	}
</script>

<!-- Mobile Header -->
<header class="flex flex-col items-center border-b bg-card p-4 lg:hidden">
	<div class="flex w-full flex-col items-center gap-2">
		<img
			src="https://i.imgur.com/UeEDuUi.png"
			alt="Symbology Logo"
			class="h-auto max-w-[240px] rounded"
		/>
		<button
			class="cursor-pointer border-none bg-transparent p-0 transition-opacity hover:opacity-80 focus:outline-2 focus:outline-offset-2 focus:outline-primary"
			onclick={handleHomeClick}
			onkeydown={(e) => e.key === 'Enter' && handleHomeClick()}
		>
			<h1 class="m-0 text-center text-2xl font-bold tracking-wide text-primary">Symbology</h1>
		</button>
	</div>

	<Button variant="ghost" size="sm" class="mt-2" onclick={toggleMode} aria-label="Toggle theme">
		<span class="text-lg">🌙</span>
		<span class="ml-2 text-sm">Toggle Theme</span>
	</Button>
</header>

<!-- Desktop Header -->
<header class="hidden border-b bg-card lg:block">
	<div class="container mx-auto flex items-center gap-4 p-4">
		<img src="https://i.imgur.com/UeEDuUi.png" alt="Symbology Logo" class="h-12 w-auto rounded" />
		<div class="flex flex-col">
			<button
				class="cursor-pointer border-none bg-transparent p-0 text-left transition-opacity hover:opacity-80 focus:outline-2 focus:outline-offset-2 focus:outline-primary"
				onclick={handleHomeClick}
				onkeydown={(e) => e.key === 'Enter' && handleHomeClick()}
			>
				<h1 class="m-0 text-2xl font-bold tracking-wide text-primary">Symbology</h1>
			</button>
			<p class="text-sm text-muted-foreground">
				Explore LLM-generated insights from public SEC filings
			</p>
		</div>
	</div>
</header>
