# SvelteKit Routes Structure

## Overview
This document outlines the routes structure established for the Symbology SvelteKit migration.

## Routes Directory Structure

```
ui-sk/src/routes/
├── +layout.svelte                    # Main layout with header, navigation, theme
├── +page.svelte                      # Landing page with company search
├── companies/
│   └── +page.svelte                  # Companies browse/search page
├── filings/
│   └── +page.svelte                  # Filings browse/search page
├── analysis/
│   └── +page.svelte                  # AI analysis browse/search page
├── api/                              # API proxy routes
│   └── companies/
│       └── by-ticker/
│           └── [ticker]/
│               └── +server.ts        # Company API proxy
├── c/                                # Company routes
│   └── [ticker]/
│       ├── +page.ts                  # Data loading for company page
│       └── +page.svelte              # Company overview page
├── g/                                # Generated content routes
│   └── [ticker]/
│       └── [sha]/
│           ├── +page.ts              # Data loading for generated content
│           └── +page.svelte          # Generated content display
├── f/                                # Filing routes
│   └── [edgar_id]/
│       ├── +page.ts                  # Data loading for filing page
│       └── +page.svelte              # Filing detail page
└── d/                                # Document routes
    └── [edgar_id]/
        ├── +page.ts                  # Data loading for document page
        └── +page.svelte              # Document detail page
```

## URL Patterns

Following the Reddit-inspired short URL format:

- **Landing Page**: `/`
- **Companies Browse**: `/companies` - Browse and search companies
- **Filings Browse**: `/filings` - Browse and search SEC filings
- **Analysis Browse**: `/analysis` - Browse and search AI-generated analysis
- **Company Overview**: `/c/{ticker}` (e.g., `/c/AAPL`)
- **Generated Content**: `/g/{ticker}/{sha256[0:12]}` (e.g., `/g/AAPL/a1b2c3d4e5f6`)
- **Filing Display**: `/f/{edgar_id}` (e.g., `/f/0000320193-23-000077`)
- **Document Display**: `/d/{edgar_id}` (e.g., `/d/0000320193-23-000077-xbrl`)

## Data Loading Strategy

Each route uses SvelteKit's `+page.ts` files for server-side data loading:

1. **Company Page**: Loads company info, aggregates, and filings
2. **Generated Content**: Loads content by SHA and company info
3. **Filing Page**: Loads filing details, documents, and company info
4. **Document Page**: Loads document content, parent filing, and company info

## Navigation Flow

1. **Landing** → Company Search → **Company Page**
2. **Company Page** → **Generated Content** or **Filing Page**
3. **Filing Page** → **Document Page**
4. **Generated Content** → Sources → **Document Page**

## Mobile-First Design

- Responsive grid layouts using Tailwind CSS
- Card-based UI components from shadcn-ui
- Mobile navigation with collapsible sidebar
- Touch-friendly button sizes and interactions

## Component Dependencies

The routes reference these component categories:
- `$lib/components/ui/*` - shadcn-ui components (Button, Card, Badge, etc.)
- `$lib/components/company/*` - Company-specific components
- `$lib/components/filings/*` - Filing-specific components
- `$lib/components/documents/*` - Document-specific components
- `$lib/components/content/*` - Generated content components

## Next Steps

1. Install and configure shadcn-ui components
2. Create the component directory structure in `$lib/components/`
3. Migrate existing components from the original `ui/` directory
4. Set up API proxy routes for backend communication
5. Configure environment variables for API endpoints
6. Add type definitions for API responses

## State Management

Unlike the original single-page app with centralized state, the SvelteKit version uses:
- Page-level state management through load functions
- URL-based navigation state
- Local component state with Svelte 5 runes
- Minimal global state for theme and user preferences
