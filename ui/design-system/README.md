# Symbology design system previews

Standalone HTML preview cards for the UI's design tokens and components,
rendered with the site's **real** stylesheet. The canonical design lives in the
Svelte components and `src/app.css`; these files are small, browsable snapshots
of it — one card per token group or component.

## How it works

- `site.css` is compiled from `src/app.css` with `just design-system` (Tailwind
  v4 CLI). It is generated and gitignored — rebuild it whenever `app.css` or a
  preview changes.
- Each preview is a self-contained HTML file linking `site.css` plus the same
  Google Fonts as `src/app.html`. Styles that live in a Svelte component's
  scoped `<style>` block (e.g. ChangeCard) are copied into that preview's
  `<style>` — if a component's scoped styles change, update its preview.
- The first line of every preview is a `@dsCard` marker comment
  (`group`, `name`, `subtitle`, `width`) — the claude.ai/design Design System
  pane builds its card index from these.

## Syncing to claude.ai/design

Previews are pushed to the "Symbology" design-system project on claude.ai
via the DesignSync tool from a Claude Code session ("sync the design system
previews"). The web UI then shows a paned library of per-component cards —
an always-current view of what's actually shipped, and a place to compare
variants.

## Iterating

Design iteration happens in the repo: generate variants against the real
Svelte/CSS (frontend-design skill), compare them here or in the design pane,
land the winner in the components, then re-sync the affected previews.
