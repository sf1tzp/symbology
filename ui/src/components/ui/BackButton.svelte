<script lang="ts">
  import { createEventDispatcher } from 'svelte';

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

<button
  type="button"
  class="btn btn-link {variant === 'minimal' ? 'minimal-back' : 'default-back'}"
  onclick={handleClick}
  aria-label={label}
>
  <span class="back-icon">←</span>
  <span class="back-label">{label}</span>
</button>

<style>
  .default-back {
    background-color: var(--color-surface);
    border: 1px solid var(--color-border);
    padding: var(--space-sm) var(--space-md);
  }

  .default-back:hover {
    border-color: var(--color-primary);
    background-color: var(--color-background);
    transform: translateX(-2px);
  }

  .minimal-back {
    background: none;
    border: none;
    padding: var(--space-xs) var(--space-sm);
    color: var(--color-primary);
  }

  .minimal-back:hover {
    background-color: var(--color-surface);
    transform: translateX(-2px);
  }

  .back-icon {
    font-size: 1.1rem;
    font-weight: bold;
  }

  .back-label {
    font-weight: var(--font-weight-medium);
  }

  /* Responsive adjustments */
  @media (max-width: 600px) {
    .btn {
      padding: var(--space-xs) var(--space-sm);
      font-size: 0.85rem;
    }

    .back-label {
      display: none;
    }

    .back-icon {
      font-size: 1.2rem;
    }
  }
</style>
