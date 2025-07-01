<!-- AnalysisPanel.svelte -->
<script lang="ts">
  import type { CompletionResponse } from '$utils/generated-api-types';
  import { formatModelName, formatDate } from '$utils/formatters';
  import MetaItems from '$components/ui/MetaItems.svelte';

  // Props to show relevant analysis based on current selection
  const { completion } = $props<{
    completion: CompletionResponse | undefined;
  }>();

  // Prepare meta items for display
  const metaItems = $derived(
    completion
      ? [
          { label: 'Model', value: formatModelName(completion.model) },
          ...(completion.temperature
            ? [{ label: 'Temperature', value: completion.temperature }]
            : []),
          { label: 'Created', value: formatDate(completion.created_at) },
          ...(completion.source_documents?.length
            ? [
                {
                  label: 'Source Documents',
                  value: `${completion.source_documents.length} document${
                    completion.source_documents.length === 1 ? '' : 's'
                  }`,
                },
              ]
            : []),
        ]
      : []
  );
</script>

<div class="analysis-panel card">
  <h2>Analysis Panel</h2>
  <div class="analysis-content">
    {#if completion}
      <div class="completion-analysis">
        <h3>Current Completion</h3>
        <MetaItems items={metaItems} />

        <div class="content-preview">
          <h4>Response Preview</h4>
          <p class="preview-text">
            {completion.content.length > 200
              ? completion.content.substring(0, 200) + '...'
              : completion.content}
          </p>
        </div>
      </div>
    {:else}
      <div class="placeholder-content">
        <p>Select a completion to view analysis</p>
        <div class="features-list">
          <h4>Available Analysis:</h4>
          <ul>
            <li>Model configuration details</li>
            <li>Source document information</li>
            <li>Response content preview</li>
            <li>Creation timestamps</li>
          </ul>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .analysis-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  h2 {
    color: var(--color-primary);
    margin-top: 0;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--space-sm);
  }

  .analysis-content {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
  }

  .completion-analysis {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }

  .completion-analysis h3 {
    margin: 0;
    color: var(--color-text);
    font-size: 1.1rem;
  }

  .content-preview {
    margin-top: var(--space-md);
  }

  .content-preview h4 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-primary);
    font-size: 1rem;
  }

  .preview-text {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin: 0;
    line-height: 1.6;
    color: var(--color-text);
  }

  .placeholder-content {
    text-align: center;
    color: var(--color-text-light);
  }

  .placeholder-content p {
    font-size: 1.1rem;
    margin-bottom: var(--space-lg);
  }

  .features-list {
    text-align: left;
    display: inline-block;
  }

  .features-list h4 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
  }

  .features-list ul {
    margin: 0;
    padding-left: var(--space-lg);
  }

  .features-list li {
    margin-bottom: var(--space-xs);
    color: var(--color-text-light);
  }
</style>
