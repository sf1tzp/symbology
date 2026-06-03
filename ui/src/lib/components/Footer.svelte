<script lang="ts">
	import Mark from '$lib/components/Mark.svelte';
	import { resolve } from '$app/paths';
</script>

<footer class="border-t border-border">
	<div class="flex-between flex flex-row py-3 md:py-8">
		<div class="mx-auto flex items-center gap-1 font-serif text-sm text-ink-3 md:m-0">
			<a
				href={resolve('/')}
				class="flex items-center gap-2 font-serif text-sm text-ink-3 transition-colors hover:text-ink"
			>
				<Mark size={18} />
				Symbology
			</a>
			<p class="text-sm">
				by
				<a href="https://streetfortress.com" class="transition-colors hover:text-ink">
					Streetfortress Industries, LLC.
				</a>
			</p>
		</div>

		<nav class="hidden items-center gap-4 text-sm text-ink-3 md:flex">
			<a href={resolve('/companies')} class="transition-colors hover:text-ink">Companies</a>
			<a href={resolve('/faq')} class="transition-colors hover:text-ink">FAQ</a>
			<a
				href="https://github.com/sf1tzp/symbology/"
				target="_blank"
				rel="noopener noreferrer"
				class="transition-colors hover:text-ink">GitHub</a
			>
		</nav>
	</div>
</footer>
