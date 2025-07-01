<script lang="ts">
  import { marked } from 'marked';

  const { content, class: className = '' } = $props<{
    content: string;
    class?: string;
  }>();

  function renderMarkdown(text: string): string {
    const result = marked.parse(text, {
      breaks: true,
      gfm: true,
      async: false,
    });
    return typeof result === 'string' ? result : '';
  }
</script>

<div class="markdown-content {className}">
  {@html renderMarkdown(content)}
</div>

<style>
  .markdown-content :global(p) {
    margin: 0 0 var(--space-sm) 0;
    line-height: 1.6;
    color: var(--color-text);
    word-break: break-word;
  }

  .markdown-content :global(p:last-child) {
    margin-bottom: 0;
  }

  .markdown-content :global(h1),
  .markdown-content :global(h2),
  .markdown-content :global(h3),
  .markdown-content :global(h4),
  .markdown-content :global(h5),
  .markdown-content :global(h6) {
    margin: var(--space-md) 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
  }

  .markdown-content :global(h1:first-child),
  .markdown-content :global(h2:first-child),
  .markdown-content :global(h3:first-child),
  .markdown-content :global(h4:first-child),
  .markdown-content :global(h5:first-child),
  .markdown-content :global(h6:first-child) {
    margin-top: 0;
  }

  .markdown-content :global(h1) {
    font-size: 1.8rem;
    border-bottom: 2px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .markdown-content :global(h2) {
    font-size: 1.5rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-xs);
  }

  .markdown-content :global(h3) {
    font-size: 1.3rem;
  }

  .markdown-content :global(h4) {
    font-size: 1.1rem;
  }

  .markdown-content :global(h5) {
    font-size: 1rem;
  }

  .markdown-content :global(h6) {
    font-size: 0.9rem;
  }

  .markdown-content :global(ul),
  .markdown-content :global(ol) {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .markdown-content :global(li) {
    margin: var(--space-xs) 0;
    line-height: 1.5;
  }

  .markdown-content :global(strong) {
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .markdown-content :global(em) {
    font-style: italic;
  }

  .markdown-content :global(code) {
    background-color: var(--color-surface);
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    font-family: monospace;
    font-size: 0.9em;
    border: 1px solid var(--color-border);
  }

  .markdown-content :global(pre) {
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
    overflow-x: auto;
    margin: var(--space-sm) 0;
    border: 1px solid var(--color-border);
  }

  .markdown-content :global(pre code) {
    background: none;
    padding: 0;
    border: none;
  }

  .markdown-content :global(blockquote) {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--space-md);
    margin: var(--space-sm) 0;
    font-style: italic;
    color: var(--color-text-light);
    background-color: var(--color-surface);
    padding: var(--space-md);
    border-radius: var(--border-radius);
  }

  .markdown-content :global(table) {
    border-collapse: collapse;
    width: 100%;
    margin: var(--space-md) 0;
    border: 1px solid var(--color-border);
  }

  .markdown-content :global(th),
  .markdown-content :global(td) {
    border: 1px solid var(--color-border);
    padding: var(--space-sm);
    text-align: left;
  }

  .markdown-content :global(th) {
    background-color: var(--color-surface);
    font-weight: var(--font-weight-bold);
  }

  .markdown-content :global(hr) {
    border: none;
    border-top: 2px solid var(--color-border);
    margin: var(--space-lg) 0;
  }

  .markdown-content :global(a) {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .markdown-content :global(a:hover) {
    color: var(--color-primary-hover);
  }
</style>
