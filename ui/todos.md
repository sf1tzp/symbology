Based on my analysis of the current UI structure and the new streamlined API flow, here's a comprehensive plan to update the UI to leverage the new component flow:

## Current vs. New Flow

**Current Flow:** Company → Filings → Documents
**New Streamlined Flow:** Company → Aggregates → Completions → Documents

## Refactoring Plan

### 1. Update API Types (Phase 1)
- **Update generated-api-types.ts** to include new aggregate and completion interfaces
- **Add new TypeScript interfaces** for:
  - `AggregateResponse`
  - `CompletionResponse`
  - Remove or deprecate `FilingResponse` related types

### 2. Create New Components (Phase 2)

#### A. Create `AggregateSelector.svelte`
- Replace FilingsSelector.svelte
- **API Integration:** Use `/api/aggregates/by-ticker/{ticker}`
- **Display Features:**
  - Show aggregate types (MDA, Risk Factors, Business Description)
  - Display model configuration info
  - Show response warnings if any
  - Implement same collapsible behavior as current selectors

#### B. Create `CompletionSelector.svelte`
- Replace DocumentSelector.svelte
- **API Integration:** Use `/api/aggregates/{aggregate_id}/completions`
- **Display Features:**
  - List completions used to create the aggregate
  - Show completion metadata
  - Model configuration details
  - Source document links

#### C. Update DocumentViewer.svelte
- **API Integration:** Use `/api/documents/{document_id}` and `/api/documents/{document_id}/content`
- **Enhanced Features:**
  - Add link to SEC filing online
  - Better content formatting
  - Document metadata display

### 3. Update Main App Flow (Phase 3)

#### A. Update App.svelte
- **Replace component imports:**
  ```typescript
  // Remove
  import FilingsSelector from '$components/filings/FilingsSelector.svelte';
  import DocumentSelector from '$components/documents/DocumentSelector.svelte';

  // Add
  import AggregateSelector from '$components/aggregates/AggregateSelector.svelte';
  import CompletionSelector from '$components/completions/CompletionSelector.svelte';
  ```

- **Update state management:**
  ```typescript
  // Replace filing-related state
  let selectedAggregate = $state<AggregateResponse | null>(null);
  let selectedCompletion = $state<CompletionResponse | null>(null);
  ```

#### B. Update Event Handlers
- Replace filing event handlers with aggregate handlers
- Add completion event handlers
- Update the cascading clear logic

### 4. Component Directory Restructure (Phase 4)

#### A. New Directory Structure
```
src/components/
├── company/
│   └── CompanySelector.svelte (keep existing)
├── aggregates/
│   └── AggregateSelector.svelte (new)
├── completions/
│   └── CompletionSelector.svelte (new)
├── documents/
│   └── DocumentViewer.svelte (updated)
└── ui/
    └── PlaceholderCard.svelte (keep existing)
```

#### B. Remove Old Components
- Delete `src/components/filings/` directory
- Remove FilingsSelector.svelte
- Remove old DocumentSelector.svelte

### 5. API Integration Updates (Phase 5)

#### A. Update API Base URLs in Config
- Verify config.ts works with new endpoints
- Add any new configuration needed for aggregate/completion APIs

#### B. Update Generated Types Script
- Ensure generate-api-types.js captures new aggregate and completion schemas
- Update the script to handle the new API structure

### 6. Enhanced UI Features (Phase 6)

#### A. Aggregate Overview Panel
- **Summary Section:** Model config, warnings
- **Content Section:** Aggregate content display
- **Source Links:** Links to source completions
- **Ratings:** If implemented in API

#### B. Completion Overview Panel
- **Summary Section:** Model config, warnings
- **Content Section:** Completion content
- **Source Documents:** Links to source documents
- **SEC Filing Links:** Direct links to SEC filings
- **Ratings:** If implemented in API

#### C. Enhanced Document Overview
- **Title and Metadata**
- **SEC Filing Link:** Direct link to online filing
- **Improved Content Display**

### 7. Styling and UX Improvements (Phase 7)

#### A. Consistent Component Styling
- Ensure new components use existing utility classes
- Maintain collapsible behavior consistency
- Update color schemes and spacing

#### B. Responsive Design
- Ensure new flow works on mobile and desktop
- Test side-by-side layout with new components

### 8. Testing and Validation (Phase 8)

#### A. Component Testing
- Test each new component independently
- Verify API integration works correctly
- Test error handling and loading states

#### B. Flow Testing
- Test complete user journey from company to document
- Verify state management and cascading updates
- Test collapsible behavior and responsive design

## Implementation Order

1. **Phase 1-2:** Update types and create new components
2. **Phase 3:** Update main app flow
3. **Phase 4:** Clean up old components
4. **Phase 5:** Verify API integration
5. **Phase 6-7:** Enhance UI features and styling
6. **Phase 8:** Testing and validation

This plan maintains the existing UI patterns and user experience while updating the data flow to match the new streamlined API structure. The collapsible behavior, responsive design, and overall styling will be preserved while providing a more logical flow through the financial data hierarchy.