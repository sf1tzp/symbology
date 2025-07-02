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

<button type="button" class="back-button {variant}" onclick={handleClick} aria-label={label}>
  <span class="back-icon">←</span>
  <span class="back-label">{label}</span>
</button>

<style>
  .back-button {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    background-color: var(--color-surface);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-sm) var(--space-md);
    cursor: pointer;
    font-size: 0.9rem;
    font-family: inherit;
    transition: all 0.2s ease;
    text-decoration: none;
  }

  .back-button:hover {
    border-color: var(--color-primary);
    background-color: var(--color-background);
    transform: translateX(-2px);
  }

  .back-button:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .back-button.minimal {
    background: none;
    border: none;
    padding: var(--space-xs) var(--space-sm);
    color: var(--color-primary);
  }

  .back-button.minimal:hover {
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
    .back-button {
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
