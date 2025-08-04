# UI routes

Remember, we're using svelte 5 with rune syntax for this project.

Let's use short, reddit inspired url formats (/c/, /g/, etc)
Let's use a short-form SHA 256 in urls as identifiers (inspired from github's short commit SHAs)


## company overview

url: symbology.online/c/{{ticker}}

Display:
- Desc
- Financial Overview
- Link to Filings / Analysis

## content display

This page will display generated content

url: symbology.online/g/{{ticker}}/{sha256[0:12]}

> note: we need to implement some backend changes to support this page design
> 1. Consolidate the `Aggregate` and `Completion` types. These are similar, but Completions maintain a 'source documents' list, and Aggregates maintain a 'source completions' list.
> 1a. One proposed solution is to create new 'GeneratedContent'. The GeneratedContent type will resemble the two existing types, but support either Documents, other GenreatedContents, or both as source material.
> 2. We want to save sha256 hashes of generated content for content verification as to use the short format as a identifier in urls
> 3. We want to utilize the 'Options' type from the ollama library in our ModelConfig type... then use the ModelConfig type in our database models instead of individual fields for model, ctx, temperature, etc.

Display:
- Content
- Options
- System and User Prompt
- Sources

## filing display

url: symbology.online/f/{edgar_id}

Display:
- Filing Information
- Links to things that reference this filing
- links to child documents
- Financials

## document display

url: symbology.online/d/{edgar_id}

Display
- Document content
- link to parent filing
- links to things that reference this document
