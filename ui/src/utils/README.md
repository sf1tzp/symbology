# UI Utilities

This directory contains utility functions used throughout the Symbology UI application.

## API Integration Files

### generated-api-types.ts

This is an auto-generated file containing TypeScript interfaces created from the OpenAPI schema:

- **DO NOT EDIT MANUALLY** - Generated via `generate-api-types.js` in the scripts directory
- Contains detailed interface definitions with all properties from the API schema
- Includes documentation comments from the schema
- Provides error handling and API fetching utilities

## Usage Guidelines

- Import types directly from `generated-api-types.ts` as it contains the most up-to-date definitions
- When updating the API in the backend, run the type generation script to update the generated types:

```bash
node scripts/generate-api-types.js
```