<script lang="ts">
  const {
    message,
    onRetry,
    showRetry = true,
  } = $props<{
    message: string;
    onRetry?: () => void;
    showRetry?: boolean;
  }>();
</script>

<div class="error-message">
  <p>{message}</p>
  {#if showRetry && onRetry}
    <button onclick={onRetry} class="retry-button">Retry</button>
  {/if}
</div>

<style>
  .error-message {
    color: var(--color-error);
    text-align: center;
    padding: var(--space-lg);
  }

  .error-message p {
    margin: 0 0 var(--space-sm) 0;
  }

  .retry-button {
    background-color: var(--color-primary);
    color: var(--color-surface);
    border: none;
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--border-radius);
    cursor: pointer;
    margin-top: var(--space-sm);
    transition: background-color 0.2s ease;
  }

  .retry-button:hover {
    background-color: var(--color-primary-hover);
  }
</style>
