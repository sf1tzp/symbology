<!-- PlaceholderCard.svelte -->
<script lang="ts">
  import { getLogger } from '$utils/logger';
  const logger = getLogger('PlaceholderCard');

  // This component will be enhanced later with actual functionality
  // Currently it's a placeholder for the side-by-side layout requirement
</script>

<div class="placeholder-card card">
  <h2>Analysis Panel</h2>
  <div class="placeholder-content">
    <p>This panel will contain analysis tools, financial metrics, and other insights.</p>
    <p>Future enhancements will include:</p>
    <ul>
      <li>Financial metrics visualization</li>
      <li>Document insights</li>
      <li>AI-powered analysis</li>
      <li>Custom annotations</li>
    </ul>
  </div>
</div>

<style>
  .placeholder-card {
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

  .placeholder-content {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  ul {
    padding-left: var(--space-lg);
  }

  li {
    margin-bottom: var(--space-sm);
  }
</style>
