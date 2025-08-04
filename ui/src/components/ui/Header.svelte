<!-- Header.svelte -->
<script lang="ts">
  import appState, { actions } from '$utils/state-manager.svelte';
  import MarkdownContent from './MarkdownContent.svelte';
</script>

<header class="header card">
  <div class="logo-section">
    <img src="https://i.imgur.com/UeEDuUi.png" alt="Symbology Logo" class="logo" />
    <button
      class="title-button"
      onclick={actions.clearAll}
      onkeydown={(e) => e.key === 'Enter' && actions.clearAll()}
    >
      <h1 class="clickable-title">Symbology</h1>
    </button>
  </div>

  <!-- <button class="theme-toggle" onclick={actions.toggleTheme} aria-label="Toggle theme">
    {#if appState.isDarkMode}
      <span class="theme-icon">☀️</span>
      <span class="theme-label">Light Mode</span>
    {:else}
      <span class="theme-icon">🌙</span>
      <span class="theme-label">Dark Mode</span>
    {/if}
  </button> -->

  <!-- <button class="theme-toggle">
    <MarkdownContent
      content="#### [🚧 Status Page](https://snapshots.raintank.io/dashboard/snapshot/BMPyLd8cvFdQMmpx1mJA0CjjMiVwdEMC?orgId=0&refresh=10s)"
    />
  </button> -->
</header>

<style>
  .header {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--color-surface);
    padding: var(--space-md) var(--space-md) var(--space-lg) var(--space-md);
    border-bottom: none;
    margin-bottom: 0;
    box-shadow: none;
    border-radius: var(--border-radius, 5px);
  }

  .logo-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-xs);
    width: 100%;
  }

  .logo {
    max-width: 240px;
    height: auto;
    border-radius: var(--border-radius);
  }

  h1 {
    margin: 0 0 var(--space-xs) 0;
    color: var(--color-primary);
    font-weight: var(--font-weight-bold);
    font-size: 2rem;
    letter-spacing: 0.04em;
    text-align: center;
  }

  .clickable-title {
    cursor: pointer;
    transition: color 0.2s ease;
  }

  .clickable-title:hover {
    color: var(--color-secondary, var(--color-primary));
    opacity: 0.8;
  }

  .title-button {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .title-button:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .theme-toggle {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    background-color: var(--color-background);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    padding: var(--space-xs) var(--space-sm);
    cursor: pointer;
    transition: all 0.2s ease;
    margin-top: var(--space-xs);
    font-size: 1rem;
    width: 100%;
    justify-content: center;
  }

  .theme-toggle:hover {
    border-color: var(--color-primary);
    background-color: var(--color-surface);
  }

  .theme-icon {
    font-size: 1.2rem;
  }

  @media (max-width: 768px) {
    .header {
      padding: var(--space-xs) var(--space-sm) var(--space-sm) var(--space-sm);
    }

    .logo {
      max-width: 80px; /* Much smaller logo on mobile */
    }

    h1 {
      font-size: 1.25rem; /* Even smaller title on mobile */
      margin: 0;
    }

    .logo-section {
      gap: var(--space-xs);
    }
  }

  @media (max-width: 600px) {
    .theme-label {
      display: none;
    }

    .theme-toggle {
      padding: var(--space-xs);
      font-size: 0.95rem;
    }

    .logo {
      width: 40px;
      height: 40px;
    }

    h1 {
      font-size: 1.3rem;
    }

    .logo-section {
      gap: var(--space-xs);
    }

    .header {
      padding: var(--space-md) var(--space-xs) var(--space-lg) var(--space-xs);
    }
  }
</style>
