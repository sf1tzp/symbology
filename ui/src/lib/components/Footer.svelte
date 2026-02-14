<script lang="ts">
	import { Separator } from '$lib/components/ui/separator';
	import ExternalLink from '@lucide/svelte/icons/external-link';
</script>

<footer class="border-t bg-card">
	<div class="mx-auto max-w-5xl px-4 py-12 md:py-18">
		<div class="flex flex-col items-center gap-6">
			<!-- Logo -->
			<img
				src="https://i.imgur.com/UeEDuUi.png"
				alt="Symbology Logo"
				class="h-8 w-auto rounded opacity-50"
			/>

			<!-- Nav links -->
			<nav class="flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
				<a href="/" class="transition-colors hover:text-foreground">Home</a>
				<Separator orientation="vertical" class="h-4" />
				<a href="/companies" class="transition-colors hover:text-foreground">Companies</a>
				<Separator orientation="vertical" class="h-4" />
				<a href="/groups" class="transition-colors hover:text-foreground">Groups</a>
				<Separator orientation="vertical" class="h-4" />
				<a href="/search" class="transition-colors hover:text-foreground">Search</a>
				<Separator orientation="vertical" class="h-4" />
				<a href="/faq" class="transition-colors hover:text-foreground">FAQ</a>
				<Separator orientation="vertical" class="h-4" />
				<a
					href="https://github.com/sf1tzp/symbology/"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center gap-1 transition-colors hover:text-foreground"
				>
					GitHub
					<ExternalLink class="h-3 w-3" />
				</a>
			</nav>

			<!-- Copyright -->
			<p class="text-xs text-muted-foreground">
				&copy; {new Date().getFullYear()}
				<a
					href="https://streetfortress.com"
					target="_blank"
					rel="noopener noreferrer"
					class="transition-colors hover:text-foreground"
				>
					Streetfortress Industries LLC</a
				>. All rights reserved.
			</p>
		</div>
	</div>
</footer>
