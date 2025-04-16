<script lang="ts">
  import CompanySelector from '$components/company/CompanySelector.svelte';
</script>

<main>
  <header>
    <h1>Symbology Test</h1>
  </header>

  <div class="dashboard">
    <div class="selectors">
      <CompanySelector />
    </div>
  </div>
</main>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .dashboard {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  @media (min-width: 768px) {
    .dashboard {
      flex-direction: row;
    }

    .selectors {
      width: 30%;
    }
  }
</style>
