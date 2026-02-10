<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let introContent = `
## [Investment Research](https://www.investor.gov/introduction-investing/getting-started/researching-investments), intelligently automated.

Every quarter, thousands of public companies file detailed reports with the SEC. The insights are there — buried in thousands of pages of dense, unstructured text.

Symbology uses large language models to read, distill, and compare these filings over time — so you can focus on what actually changed.

Learn more in the [FAQ](/faq) or explore the [source code](https://github.com/sf1tzp/symbology/).
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
