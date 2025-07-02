<!-- PlaceholderCard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { getLogger } from '$utils/logger';
  import appState, { actions } from '$utils/state-manager.svelte';
  import MarkdownContent from './MarkdownContent.svelte';

  const logger = getLogger('PlaceholderCard');

  let projectDescription = $state('');

  // Read project description from markdown file
  onMount(async () => {
    try {
      const response = await fetch('/welcome.md');
      if (response.ok) {
        projectDescription = await response.text();
      } else {
        logger.error('Failed to load project description');
        projectDescription = 'Failed to load project description.';
      }
    } catch (error) {
      logger.error('Error loading project description:', error);
      projectDescription = 'Error loading project description.';
    }
  });

  // Landing page component with Symbology branding and information
  function handleAcceptDisclaimer() {
    actions.acceptDisclaimer();
  }
</script>

<div class="landing-page card">
  <div class="header-section">
    <div class="logo-container">
      <img src="https://i.imgur.com/UeEDuUi.png" alt="Symbology Logo" class="logo" />
    </div>
    <h1>Symbology</h1>
    <p class="tagline">Open Source Insights from SEC Filings</p>
  </div>

  <div class="content-sections">
    <section class="about-section">
      {#if projectDescription}
        <MarkdownContent content={projectDescription} />
      {/if}
      {#if !appState.disclaimerAccepted}
        <div class="disclaimer-notice">
          <strong>Important:</strong> The summaries presented by Symbology were generated with the
          help of LLMs and are provided with no warranty or guarantee of accuracy.
          <br /><br />
          <strong>Please be aware that:</strong>
          <ul>
            <li>AI-generated content may contain errors, inaccuracies, or misinterpretations</li>
            <li>This information is provided for research and educational purposes only</li>
            <li>
              You should verify all information independently before making any financial decisions
            </li>
            <li>
              Symbology provides no warranty or guarantee of accuracy for any AI-generated content
            </li>
          </ul>
          <p>
            By continuing to use this site, you acknowledge that you understand these limitations
            and agree to use the information at your own discretion.
          </p>
          <button class="accept-button" onclick={handleAcceptDisclaimer}>
            I Understand and Accept
          </button>
        </div>
      {:else}
        <div class="disclaimer-accepted">
          <strong>✓ Thanks.</strong> You have acknowledged the limitations of AI-generated content.
        </div>
      {/if}
    </section>

    <section class="articles-section">
      <!-- TODO: Let's create an ArticleViewer component to render markdown written in `public/articles`
      Here we will link to the articles
      - how it works
      - vibe coding
      - labbing and infrastructure -->
    </section>

    <section class="acknowledgments-section links-section">
      <h3>Acknowledgments</h3>
      <div class="link-group">
        <ul class="acknowledgments-list">
          <li>
            <a href="https://www.edgarcompany.sec.gov/" target="_blank">
              <strong>SEC EDGAR:</strong>
              U.S. Securities and Exchange Commision Database
            </a>
          </li>
          <li>
            <a href="https://finance.yahoo.com/markets/stocks/most-active/" target="_blank">
              <strong>Yahoo! Finance:</strong>
              Most Active Stocks
            </a>
          </li>
          <li>
            <a href="https://github.com/dgunning/edgartools" target="_blank">
              <strong>Edgar Tools:</strong>
              Python library for SEC data access
            </a>
          </li>
          <li>
            <a href="https://ollama.com/" target="_blank">
              <strong>Ollama:</strong>
              Self-hosted LLM processing capabilities
            </a>
          </li>
          <li>
            <a href="https://svelte.dev/" target="_blank">
              <strong>Svelte:</strong>
              Modern Web Framework
            </a>
          </li>
          <li>
            <a href="https://fastapi.tiangolo.com/" target="_blank">
              <strong>FastAPI:</strong>
              Python API Framework
            </a>
          </li>
          <li>
            <a href="https://www.postgresql.org/" target="_blank">
              <strong>PostgreSQL:</strong>
              Robust data storage and relationships
            </a>
          </li>
        </ul>
      </div>
    </section>

    <section class="links-section">
      <div class="links-grid">
        <div class="link-group">
          <h3>External Resources</h3>
          <ul>
            <li><a href="https://www.investopedia.com/" target="_blank">Investopedia</a></li>
            <li>
              <a href="https://www.xbrl.org/" target="_blank"
                >XBRL: The Business Reporting Standard</a
              >
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</div>

<style>
  .landing-page {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .header-section {
    text-align: center;
    padding-bottom: var(--space-lg);
    border-bottom: 1px solid var(--color-border);
    margin-bottom: var(--space-lg);
  }
  .header-section h1 {
    color: var(--color-primary);
  }

  .logo-container {
    margin-bottom: var(--space-md);
  }

  .logo {
    max-width: 480px;
    height: auto;
    border-radius: var(--border-radius);
  }

  .tagline {
    color: var(--color-text-light);
    font-size: 1.1rem;
    margin: 0;
    font-style: italic;
  }

  .disclaimer-notice {
    border: 1px solid var(--color-warning-border, #d17c36);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin: var(--space-md) 0;
  }

  .disclaimer-notice ul {
    margin: var(--space-sm) 0;
    padding-left: var(--space-lg);
  }

  .disclaimer-notice li {
    margin-bottom: var(--space-xs);
    line-height: 1.4;
  }

  .disclaimer-notice p {
    margin: var(--space-sm) 0;
  }

  .accept-button {
    padding: var(--space-sm) var(--space-md);
    background-color: var(--color-primary);
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .accept-button:hover {
    background-color: var(--color-primary-hover);
  }

  .disclaimer-accepted {
    border: 1px solid var(--color-primary, #c3e6cb);
    border-radius: var(--border-radius);
    padding: var(--space-md);
    margin: var(--space-md) 0;
    text-align: center;
  }

  .content-sections {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  section {
    margin-bottom: var(--space-md);
  }

  section h3 {
    color: var(--color-text);
    margin: var(--space-md) 0 var(--space-sm) 0;
    font-size: 1.2rem;
  }

  section p {
    color: var(--color-text);
    line-height: 1.6;
    margin-bottom: var(--space-md);
  }

  .acknowledgments-list {
    margin: 0;
    padding-left: var(--space-lg);
  }

  .acknowledgments-list li {
    margin-bottom: var(--space-sm);
    color: var(--color-text);
    line-height: 1.5;
  }

  .acknowledgments-list strong {
    color: var(--color-primary);
  }

  .links-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-lg);
    margin-top: var(--space-md);
  }

  .link-group h3 {
    margin: 0 0 var(--space-sm) 0;
    color: var(--color-text);
    font-size: 1.1rem;
  }

  .link-group ul {
    margin: 0;
    padding-left: var(--space-md);
    list-style-type: none;
  }

  .link-group li {
    margin-bottom: var(--space-xs);
  }

  .link-group a {
    color: var(--color-primary);
    text-decoration: none;
    transition: color 0.2s ease;
  }

  .link-group a:hover {
    color: var(--color-primary-hover, var(--color-primary));
    text-decoration: underline;
  }

  @media (max-width: 768px) {
    .links-grid {
      grid-template-columns: 1fr;
      gap: var(--space-md);
    }

    .logo {
      max-width: 100px;
    }
  }
</style>
