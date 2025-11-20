<script lang="ts">
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import CompanySelector from '$lib/components/company/CompanySelector.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let introContent = `
## [Investment Research](https://www.investor.gov/introduction-investing/getting-started/researching-investments) for the modern era.

Leverage LLMs to read the forms so you don't have to. With thoughtful prompt techniques, compare years of filing, identify changes and get _trustworthy*_ read-outs on Company status.

_*LLMs still generate gibberish despite our best efforts. Please [report](https://github.com/sf1tzp/symbology/issues) low quality content [here](https://github.com/sf1tzp/symbology/issues)._

This site is a work in progress. Please check out the [F.A.Q.](https://symbology.online/faq) and [code](https://github.com/sf1tzp/symbology/) for more details.
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
