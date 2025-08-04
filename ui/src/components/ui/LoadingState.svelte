<script lang="ts">
  import { Spinner } from 'kampsy-ui';

  const { message = 'Loading...', size = 'normal' } = $props<{
    message?: string;
    size?: 'small' | 'normal' | 'large';
  }>();

  // Map our size prop to kampsy-ui spinner sizes
  const spinnerSize = size === 'small' ? 'small' : size === 'large' ? 'large' : 'medium';
</script>

<div class="flex flex-col items-center p-8 gap-4">
  <Spinner size={spinnerSize} />
  <p class="text-[var(--color-text)] opacity-80 text-sm">{message}</p>
</div>
