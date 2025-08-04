sf1tzp: We're updating our app to use sveltekit, serve pages which are mobile-first, using shadcn ui components.


A working directory, `ui-sk/` has been created to house the work-in-progress conversion.

Let's begin by reviewing #file:App.svelte and #file:state-manager.svelte.ts to understand our current single-page design.

We have drafted some design goals and proposed work. We will also need to design a common layout.

Let's formulate a plan to implement this next generation of our user interface

Workspace: Collecting workspace informationLooking at your current Svelte app and the proposed SvelteKit migration with the routing structure, I can see you have a well-structured single-page application that needs to be converted to a multi-page SvelteKit app with mobile-first design using shadcn-ui components.

## Analysis of Current Architecture

Your current `App.svelte` uses a centralized state management system with `state-manager.svelte.ts` that handles navigation through view states (`company`, `filing`, `aggregate`, `completion`, `document`). The current flow is:

1. Company Selection → Company Detail
2. Company Detail → Aggregate/Filing Selection
3. Aggregate → Completion Selection
4. Completion/Filing → Document Selection
5. Document Detail View

## Migration Plan to SvelteKit

### Phase 1: Project Structure Setup

````typescript
// ui-sk/src/routes/
├── +layout.svelte          // Common layout with navigation
├── +page.svelte           // Landing page (current PlaceholderCard)
├── c/
│   └── [ticker]/
│       └── +page.svelte   // Company overview
├── g/
│   └── [ticker]/
│       └── [sha]/
│           └── +page.svelte // Generated content display
├── f/
│   └── [edgar_id]/
│       └── +page.svelte   // Filing display
└── d/
    └── [edgar_id]/
        └── +page.svelte   // Document display
````

### Phase 2: State Management Migration

Convert your centralized state to SvelteKit's approach:

````typescript
// ui-sk/src/lib/stores/app.svelte.ts
import type { CompanyResponse, AggregateResponse } from '$lib/types';

// Convert your current state-manager to use page-level state
export const pageState = $state({
  currentCompany: null as CompanyResponse | null,
  theme: 'light' as 'light' | 'dark',
  disclaimerAccepted: false,
});
````

### Phase 3: Layout Implementation

````svelte
<!-- ui-sk/src/routes/+layout.svelte -->
<script lang="ts">
  import '../app.css';
  import { ModeWatcher } from 'mode-watcher';
  import { page } from '$app/stores';
  import Header from '$lib/components/Header.svelte';
  import Navigation from '$lib/components/Navigation.svelte';

  let { children } = $props();
</script>

<ModeWatcher />

<div class="min-h-screen bg-background">
  <Header />

  <!-- Mobile-first navigation -->
  <Navigation currentPath={$page.url.pathname} />

  <main class="container mx-auto px-4 py-6">
    {@render children?.()}
  </main>
</div>
````

### Phase 4: Route Implementation

**Company Route (+page.svelte):**
````svelte
<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import CompanyDetail from '$lib/components/company/CompanyDetail.svelte';
  import AggregateSelector from '$lib/components/aggregates/AggregateSelector.svelte';

  const ticker = $page.params.ticker;

  // Load company data based on ticker
  let company = $state(null);
  let aggregates = $state([]);

  function handleAggregateSelected(aggregate) {
    // Navigate to generated content page
    goto(`/g/${ticker}/${aggregate.sha}`);
  }
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <div>
    <CompanyDetail {company} />
  </div>
  <div>
    <AggregateSelector {aggregates} on:selected={handleAggregateSelected} />
  </div>
</div>
````

**Generated Content Route (+page.svelte):**
````svelte
<script lang="ts">
  import { page } from '$app/stores';
  import ContentViewer from '$lib/components/content/ContentViewer.svelte';
  import SourcesList from '$lib/components/content/SourcesList.svelte';
  import ModelConfig from '$lib/components/ui/ModelConfig.svelte';

  const { ticker, sha } = $page.params;

  // Load generated content by SHA
  let content = $state(null);
  let sources = $state([]);
</script>

<div class="space-y-6">
  <header class="border-b pb-4">
    <h1 class="text-2xl font-bold">{content?.title}</h1>
    <p class="text-muted-foreground">Generated for {ticker}</p>
  </header>

  <ContentViewer {content} />
  <ModelConfig config={content?.modelConfig} />
  <SourcesList {sources} />
</div>
````

### Phase 5: Component Migration

Convert your existing components to use shadcn-ui:

````svelte
<!-- ui-sk/src/lib/components/company/CompanySelector.svelte -->
<script lang="ts">
  import { Input } from '$lib/components/ui/input';
  import { Button } from '$lib/components/ui/button';
  import { Card } from '$lib/components/ui/card';

  // Migrate your existing CompanySelector logic
</script>

<Card class="p-4">
  <div class="space-y-4">
    <Input placeholder="Search companies..." bind:value={searchTerm} />
    <!-- Company list with shadcn styling -->
  </div>
</Card>
````

### Phase 6: Mobile-First Navigation

````svelte
<!-- ui-sk/src/lib/components/Navigation.svelte -->
<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import { Sheet, SheetContent, SheetTrigger } from '$lib/components/ui/sheet';
  import MenuIcon from 'lucide-svelte/icons/menu';

  let { currentPath } = $props();
</script>

<!-- Mobile navigation -->
<div class="lg:hidden">
  <Sheet>
    <SheetTrigger asChild let:builder>
      <Button builders={[builder]} variant="ghost" size="sm">
        <MenuIcon class="h-4 w-4" />
      </Button>
    </SheetTrigger>
    <SheetContent side="left">
      <!-- Navigation items -->
    </SheetContent>
  </Sheet>
</div>

<!-- Desktop navigation -->
<nav class="hidden lg:flex space-x-4">
  <!-- Navigation items -->
</nav>
````

### Phase 7: Data Loading Strategy

Use SvelteKit's load functions for server-side data fetching:

````typescript
// ui-sk/src/routes/c/[ticker]/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
  const { ticker } = params;

  try {
    const [company, aggregates] = await Promise.all([
      fetch(`/api/companies/by-ticker/${ticker}`).then(r => r.json()),
      fetch(`/api/aggregates/by-ticker/${ticker}`).then(r => r.json())
    ]);

    return {
      company,
      aggregates,
      ticker
    };
  } catch (error) {
    throw error(404, 'Company not found');
  }
};
````

### Phase 8: SEO and Performance

````svelte
<!-- ui-sk/src/routes/c/[ticker]/+page.svelte -->
<script lang="ts">
  import { page } from '$app/stores';

  let { data } = $props();

  $effect(() => {
    // Update page title and meta tags
    document.title = `${data.company.name} - Symbology`;
  });
</script>

<svelte:head>
  <title>{data.company.name} - Symbology</title>
  <meta name="description" content="Financial analysis for {data.company.name}" />
</svelte:head>
````

## Implementation Timeline

1. **Week 1**: Set up SvelteKit project structure and basic routing
2. **Week 2**: Migrate core components to shadcn-ui and implement mobile-first layout
3. **Week 3**: Implement data loading and state management per route
4. **Week 4**: Add navigation, SEO optimization, and performance tuning

This plan maintains your existing component logic while leveraging SvelteKit's routing, SSR capabilities, and shadcn-ui's mobile-first design system. The URL structure follows your proposed Reddit-style format with SHA identifiers for content verification.