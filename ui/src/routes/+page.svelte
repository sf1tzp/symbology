<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let introContent = `
# Investment Research Made Easy

We use LLMs at what they're good at: Summarizing text.

Utilizing simple prompting techniques and primary sources, we aim to provide clear and consistent analysis of:
- Strategy and Market Position
- Risk Exposure and Management
- Financial Standing and Accounting Principles

Our analysis are collated and displayed here. Find out more on [github](github.com/sf1tzp/symbology).
`;
</script>

<div class="grid grid-cols-1 gap-8 lg:grid-cols-12">
	<section class="lg:col-span-4">
		<Card>
			<CardContent>
				<MarkdownContent content={introContent} />
			</CardContent>
		</Card>
	</section>

	<section class="lg:col-span-8">
		<Card>
			<CardHeader>
				<CardTitle class="text-lg">Select a Company to Get Started</CardTitle>
			</CardHeader>
			<CardContent>
				<CompanySelector showCompanyList={true} />
			</CardContent>
		</Card>
	</section>
</div>
