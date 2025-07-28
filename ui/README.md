# Symbology UI

Frontend interface for the Symbology financial intelligence platform, built with Svelte 5 and TypeScript.

## Overview

The UI provides a streamlined research interface for exploring AI-generated insights from SEC filings. The application follows a clear navigation flow: Company List → Company Detail → Aggregate Overview → Completion Overview → Document Overview.

## Architecture

- **Framework**: Svelte 5 with runes mode enabled
- **Language**: TypeScript with strict type checking
- **Build Tools**: Vite for development and production builds
- **Code Quality**: ESLint and Prettier for consistent formatting
- **Routing**: Client-side routing with svelte-routing
- **Content Security**: DOMPurify for safe HTML rendering

## Key Features

- **Company Discovery**: Search and browse companies with SEC filings
- **Aggregate Insights**: View AI-generated summaries by document type
- **Source Traceability**: Navigate from aggregates to source completions and original documents
- **Document Viewer**: Full-text viewing of SEC filing content
- **Responsive Design**: Optimized for financial research workflows

The interface connects to the Symbology API backend for all data access and maintains full traceability from high-level insights back to source documents.
