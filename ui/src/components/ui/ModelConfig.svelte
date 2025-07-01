<script lang="ts">
  import type { CompletionResponse, AggregateResponse } from '$utils/generated-api-types';

  const { item, showSystemPrompt = false } = $props<{
    item: CompletionResponse | AggregateResponse;
    showSystemPrompt?: boolean;
  }>();
</script>

<div class="model-config">
  <h3>Model Configuration</h3>
  <div class="config-grid">
    <div class="config-item">
      <span class="label">Model:</span>
      <span>{item.model.replace('_', ' ').toUpperCase()}</span>
    </div>
    {#if item.temperature !== null && item.temperature !== undefined}
      <div class="config-item">
        <span class="label">Temperature:</span>
        <span>{item.temperature}</span>
      </div>
    {/if}
    {#if item.top_p !== null && item.top_p !== undefined}
      <div class="config-item">
        <span class="label">Top-p:</span>
        <span>{item.top_p}</span>
      </div>
    {/if}
    {#if item.num_ctx !== null && item.num_ctx !== undefined}
      <div class="config-item">
        <span class="label">Context Window:</span>
        <span>{item.num_ctx.toLocaleString()}</span>
      </div>
    {/if}
    {#if item.total_duration !== null && item.total_duration !== undefined}
      <div class="config-item">
        <span class="label">Duration:</span>
        <span>{item.total_duration.toFixed(2)}s</span>
      </div>
    {/if}
  </div>

  {#if showSystemPrompt && item.system_prompt_id}
    <div class="response-warnings">
      <h3>Response Information</h3>
      <div class="warning-item">
        <span class="label">System Prompt ID:</span>
        <span class="mono">{item.system_prompt_id}</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .model-config h3,
  .response-warnings h3 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-size: 1rem;
  }

  .config-grid {
    display: grid;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  .config-item,
  .warning-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .config-item .label,
  .warning-item .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
  }

  .config-item span:not(.label),
  .warning-item span:not(.label) {
    color: var(--color-text-light);
  }

  .mono {
    font-family: monospace;
    font-size: 0.9rem;
  }

  .response-warnings {
    margin-top: var(--space-md);
  }
</style>
