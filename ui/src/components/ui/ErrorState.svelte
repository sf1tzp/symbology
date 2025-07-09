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
    <button onclick={onRetry} class="btn btn-action">Retry</button>
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

  .error-message .btn {
    margin-top: var(--space-sm);
  }
</style>
