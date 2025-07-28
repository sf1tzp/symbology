<script lang="ts">
  const {
    items,
    columns = 1,
    variant = 'default',
  } = $props<{
    items: Array<{ label: string; value: string | number; mono?: boolean }>;
    columns?: number;
    variant?: 'default' | 'surface';
  }>();
</script>

<div class="meta-grid" style="grid-template-columns: repeat({columns}, 1fr)">
  {#each items as item, index (index)}
    <div class="meta-item {variant}">
      <span class="label">{item.label}:</span>
      <span class:mono={item.mono}>{item.value}</span>
    </div>
  {/each}
</div>

<style>
  .meta-grid {
    display: grid;
    gap: var(--space-sm);
  }

  .meta-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .meta-item.default {
    background-color: var(--color-background);
  }

  .meta-item.surface {
    background-color: var(--color-surface);
  }

  .meta-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    font-size: 0.9rem;
    flex-shrink: 0;
    margin-right: var(--space-sm);
  }

  .meta-item span:not(.label) {
    color: var(--color-text);
    font-size: 0.9rem;
    text-align: right;
    word-break: break-word;
  }

  .mono {
    color: var(--color-text);
    font-family: monospace;
    font-size: 0.8rem;
  }

  @media (max-width: 768px) {
    .meta-item {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-xs);
    }

    .meta-item .label {
      margin-right: 0;
    }

    .meta-item span:not(.label) {
      text-align: left;
    }
  }
</style>
