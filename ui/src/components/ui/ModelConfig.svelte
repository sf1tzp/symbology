<script lang="ts">
  import type {
    CompletionResponse,
    AggregateResponse,
    PromptResponse,
  } from '$utils/generated-api-types';
  import { config } from '$utils/config';
  import { getLogger } from '$utils/logger';
  import { onMount } from 'svelte';
  import MarkdownContent from './MarkdownContent.svelte';

  const logger = getLogger('ModelConfig');

  const { item, showSystemPrompt = false } = $props<{
    item: CompletionResponse | AggregateResponse;
    showSystemPrompt?: boolean;
  }>();

  let promptData: PromptResponse | null = $state(null);
  let promptLoading = $state(false);
  let promptError = $state<string | null>(null);
  let showModelConfig = $state(false);
  let showPromptInfo = $state(false);

  async function fetchPrompt(promptId: string) {
    promptLoading = true;
    promptError = null;

    try {
      const response = await fetch(`${config.api.baseUrl}/prompts/${promptId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch prompt: ${response.statusText}`);
      }
      promptData = await response.json();
    } catch (error) {
      promptError = error instanceof Error ? error.message : 'Failed to fetch prompt';
      logger.error('Error fetching prompt:', error);
    } finally {
      promptLoading = false;
    }
  }

  onMount(() => {
    if (showSystemPrompt && item.system_prompt_id) {
      fetchPrompt(item.system_prompt_id);
    }
  });
</script>

<div class="model-config">
  <div
    class="section-header"
    role="button"
    tabindex="0"
    onclick={() => (showModelConfig = !showModelConfig)}
    onkeydown={(e) => e.key === 'Enter' && (showModelConfig = !showModelConfig)}
    aria-label={showModelConfig ? 'Hide model config' : 'Show model config'}
  >
    <h3>Model Configuration</h3>
    <span class="toggle-icon" class:collapsed={!showModelConfig}>▼</span>
  </div>

  {#if showModelConfig}
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
  {/if}

  {#if showSystemPrompt && item.system_prompt_id}
    <div class="response-warnings">
      <div
        class="section-header"
        role="button"
        tabindex="0"
        onclick={() => (showPromptInfo = !showPromptInfo)}
        onkeydown={(e) => e.key === 'Enter' && (showPromptInfo = !showPromptInfo)}
        aria-label={showPromptInfo ? 'Hide prompt info' : 'Show prompt info'}
      >
        <h3>System Prompt Information</h3>
        <span class="toggle-icon" class:collapsed={!showPromptInfo}>▼</span>
      </div>

      {#if showPromptInfo}
        {#if promptLoading}
          <div class="warning-item">
            <span class="label">Loading prompt...</span>
            <span class="loading-spinner">⟳</span>
          </div>
        {:else if promptError}
          <div class="warning-item error">
            <span class="label">Error:</span>
            <span>{promptError}</span>
          </div>
        {:else if promptData}
          <div class="prompt-content">
            <span class="label">Content:</span>
            <MarkdownContent content={promptData.content} class="prompt-markdown" />
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-md);
    cursor: pointer;
    padding: var(--space-xs);
    border-radius: var(--border-radius);
    transition: background-color 0.2s ease;
  }

  .section-header:hover {
    background-color: var(--color-background);
  }

  .section-header:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .section-header h3 {
    margin: 0;
    color: var(--color-primary);
    font-size: 1rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
    flex: 1;
    pointer-events: none;
  }

  .toggle-icon {
    display: inline-block;
    font-size: 0.8rem;
    color: var(--color-text-light);
    transition: transform 0.2s ease;
    pointer-events: none;
  }

  .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

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

  /* Removed unused .mono selector */

  .response-warnings {
    margin-top: var(--space-md);
  }

  .loading-spinner {
    animation: spin 1s linear infinite;
    font-size: 1.2rem;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .error {
    border-color: var(--color-error, #ef4444);
    background-color: var(--color-error-background, #fef2f2);
  }

  .prompt-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .prompt-content .label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    margin-bottom: var(--space-xs);
  }

  .prompt-content :global(.prompt-markdown) {
    padding: var(--space-sm);
    /* background-color: var(--color-background-alt, #f8fafc); */
    border: 1px solid var(--color-border-light, #e2e8f0);
    border-radius: var(--border-radius);
    max-height: 300px;
    overflow-y: auto;
  }
</style>
