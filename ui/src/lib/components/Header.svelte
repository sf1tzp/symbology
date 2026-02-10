<!-- Header.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';

	function handleHomeClick() {
		goto('/');
	}
</script>

<header class="flex flex-col items-center border-b bg-card p-4 lg:hidden">
	<div class="flex w-full flex-col items-center gap-2">
		<img
			src="https://i.imgur.com/UeEDuUi.png"
			alt="Symbology Logo"
			class="h-auto max-w-60 rounded"
		/>
		<h1 class="m-0 text-center text-2xl font-bold tracking-wide text-primary">symbology.online</h1>
		<p class="justify-center text-center text-sm text-muted-foreground">
			AI-powered analysis of public SEC filings
		</p>
	</div>
</header>

<header class="hidden border-b bg-card lg:block">
	<div class="container mx-auto flex max-w-7xl items-center gap-4 p-2 py-4">
		<img
			src="https://i.imgur.com/UeEDuUi.png"
			alt="Symbology Logo"
			class="mr-4 h-18 w-auto rounded"
		/>
		<div class="flex flex-col">
			<h1 class="text-6xl font-bold tracking-wide text-primary">symbology.online</h1>
			<p class="text-center text-sm text-muted-foreground">
				AI-powered analysis of public SEC filings
			</p>
		</div>
	</div>
</header>
