<script lang="ts">
	import Mark from '$lib/components/Mark.svelte';
	import { resolve } from '$app/paths';
</script>

<footer class="border-t border-border">
	<div class="page flex-between py-8">
		<div class="flex items-center gap-2 align-middle font-serif text-sm text-ink-3">
			<a
				href={resolve('/')}
				class="flex items-center gap-2 font-serif text-sm text-ink-3 transition-colors hover:text-ink"
			>
				<Mark size={18} />
				<span>Symbology</span>
			</a>
			<p class="text-xs">by</p>
			<a href="https://streetfortress.com" class="transition-colors hover:text-ink">
				<span>Streetfortress Industries, LLC.</span>
			</a>
		</div>

		<nav class="flex items-center gap-4 text-sm text-ink-3">
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
