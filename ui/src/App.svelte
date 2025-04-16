<script lang="ts">
  import CompanySelector from './components/company/CompanySelector.svelte';
  import FilingsSelector from './components/filings/FilingsSelector.svelte';
  import DocumentSelector from './components/documents/DocumentSelector.svelte';
  import DocumentViewer from './components/documents/DocumentViewer.svelte';
</script>

<main>
  <h1>Symbology</h1>
  <div class="dashboard">
    <div class="selectors">
      <CompanySelector />
      <FilingsSelector />
      <DocumentSelector />
    </div>
    <div class="viewer">
      <DocumentViewer />
    </div>
  </div>
</main>

<style>
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

    .viewer {
      width: 70%;
    }
  }
</style>
