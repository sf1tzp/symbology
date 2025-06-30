<!-- AnalysisPanel.svelte -->
<script lang="ts">
  import type { CompletionResponse } from '$utils/generated-api-types';

  // Props to show relevant analysis based on current selection
  const { completion } = $props<{
    completion: CompletionResponse | undefined;
  }>();
</script>

<div class="analysis-panel card">
  <h2>Analysis Panel</h2>
  <div class="analysis-content">
    {#if completion}
      <div class="completion-analysis">
        <h3>Current Completion</h3>
        <div class="analysis-item">
          <label>Model:</label>
          <span>{completion.model.replace('_', ' ').toUpperCase()}</span>
        </div>
        {#if completion.temperature}
          <div class="analysis-item">
            <label>Temperature:</label>
            <span>{completion.temperature}</span>
          </div>
        {/if}
        <div class="analysis-item">
          <label>Created:</label>
          <span>{new Date(completion.created_at).toLocaleDateString()}</span>
        </div>
        {#if completion.source_documents?.length}
          <div class="analysis-item">
            <label>Source Documents:</label>
            <span
              >{completion.source_documents.length} document{completion.source_documents.length ===
              1
                ? ''
                : 's'}</span
            >
          </div>
        {/if}

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

  .analysis-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-sm);
    background-color: var(--color-background);
    border-radius: var(--border-radius);
    border: 1px solid var(--color-border);
  }

  .analysis-item label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
  }

  .analysis-item span {
    color: var(--color-text-light);
    font-family: monospace;
    font-size: 0.9rem;
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
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--color-text);
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .placeholder-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    text-align: center;
    gap: var(--space-lg);
  }

  .placeholder-content > p {
    font-style: italic;
    color: var(--color-text-light);
    margin: 0;
  }

  .features-list {
    text-align: left;
  }

  .features-list h4 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
  }

  .features-list ul {
    padding-left: var(--space-lg);
    margin: 0;
  }

  .features-list li {
    margin-bottom: var(--space-sm);
    color: var(--color-text-light);
  }
</style>
