<script lang="ts">
  const { message = 'Loading...', size = 'normal' } = $props<{
    message?: string;
    size?: 'small' | 'normal' | 'large';
  }>();
</script>

<div class="loading-container">
  <div class="loading-spinner {size}"></div>
  <p class="loading-message">{message}</p>
</div>

<style>
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-xl);
    gap: var(--space-md);
  }

  .loading-spinner {
    border: 3px solid var(--color-border);
    border-top: 3px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .loading-spinner.small {
    width: 1rem;
    height: 1rem;
    border-width: 2px;
  }

  .loading-spinner.normal {
    width: 24px;
    height: 24px;
  }

  .loading-spinner.large {
    width: 30px;
    height: 30px;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .loading-message {
    font-weight: 500;
    color: var(--color-text);
    margin: 0;
  }
</style>
