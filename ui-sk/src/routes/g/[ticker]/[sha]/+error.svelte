<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { AlertCircle } from '@lucide/svelte';

	function handleGoHome() {
		goto('/');
	}

	function handleGoBack() {
		history.back();
	}
</script>

<svelte:head>
	<title>Content Not Found - Symbology</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center">
	<Card class="mx-auto max-w-md">
		<CardHeader>
			<div class="flex items-center space-x-2">
				<AlertCircle class="h-5 w-5 text-red-500" />
				<CardTitle class="text-lg">Content Not Found</CardTitle>
			</div>
			<CardDescription>
				The generated content you're looking for could not be found.
			</CardDescription>
		</CardHeader>
		<CardContent class="space-y-4">
			<p class="text-muted-foreground text-sm">This might happen if:</p>
			<ul class="text-muted-foreground space-y-1 text-sm">
				<li>• The content hash is invalid</li>
				<li>• The content has been removed</li>
				<li>• The API is temporarily unavailable</li>
			</ul>
			<div class="flex space-x-2">
				<Button variant="outline" onclick={handleGoBack} class="flex-1">Go Back</Button>
				<Button onclick={handleGoHome} class="flex-1">Go Home</Button>
			</div>
		</CardContent>
	</Card>
</div>
