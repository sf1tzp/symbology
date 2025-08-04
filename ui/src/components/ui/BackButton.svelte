<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Button } from 'kampsy-ui';

  const dispatch = createEventDispatcher<{
    back: void;
  }>();

  const { label = 'Back', variant = 'default' } = $props<{
    label?: string;
    variant?: 'default' | 'minimal';
  }>();

  function handleClick() {
    dispatch('back');
  }
</script>

<Button
  type="button"
  variant={variant === 'minimal' ? 'tertiary' : 'secondary'}
  onclick={handleClick}
  aria-label={label}
  size="small"
  class="hover:-translate-x-0.5 transition-transform"
>
  <span class="mr-1 text-lg font-bold">←</span>
  <span class="hidden sm:inline font-medium">{label}</span>
</Button>
