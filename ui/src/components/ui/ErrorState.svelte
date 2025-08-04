<script lang="ts">
  import { Button } from 'kampsy-ui';

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

<div class="text-gruvbox-red text-center p-6">
  <p class="m-0 mb-2">{message}</p>
  {#if showRetry && onRetry}
    <Button onclick={onRetry} size="small" class="mt-2" aria-label="Retry operation">Retry</Button>
  {/if}
</div>
