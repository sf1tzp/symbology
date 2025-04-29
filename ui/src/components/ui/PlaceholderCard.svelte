<!-- PlaceholderCard.svelte -->
<script lang="ts">
  import { getLogger } from '$utils/logger';
  import { fetchApi, isApiError } from '$utils/generated-api-types';
  import type { CompletionResponse, PromptResponse } from '$utils/generated-api-types';
  import config from '$utils/config';
  import { onDestroy, onMount } from 'svelte';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';

  const logger = getLogger('PlaceholderCard');
  logger.debug('[PlaceholderCard] Component initializing');

  // Props
  const { documentId } = $props<{ documentId: string | undefined }>();

  // Using Svelte 5 runes
  let loading = $state(false);
  let error = $state<string | null>(null);
  let completions = $state<string[]>([]);
  let systemPrompts = $state<PromptResponse[]>([]);
  let userPrompts = $state<PromptResponse[]>([]);
  let selectedCompletion = $state<CompletionResponse | null>(null);
  let completionContent = $state<string>('');

  // Track the last processed document ID to prevent unnecessary re-processing
  let lastProcessedDocId = $state<string | undefined>(undefined);
  // Flag to track if we're currently processing to prevent reentrancy
  let isProcessing = $state(false);

  onMount(() => {
    logger.debug('[PlaceholderCard] Component mounted');
    logger.debug('[PlaceholderCard] Initial documentId:', { documentId });
  });

  onDestroy(() => {
    logger.debug('[PlaceholderCard] Component destroyed');
  });

  // Watch for changes in documentId and check for completions
  $effect(() => {
    // Only proceed if the document ID has actually changed and we're not already processing
    if (documentId === lastProcessedDocId || isProcessing) {
      return;
    }

    logger.debug('[PlaceholderCard] Effect watching documentId triggered', {
      documentId,
      previousDocId: lastProcessedDocId,
      previousCompletionCount: completions.length,
      hasSelectedCompletion: !!selectedCompletion,
      isProcessing,
    });

    // Update the last processed ID before we do anything else
    lastProcessedDocId = documentId;

    if (documentId) {
      logger.debug('[PlaceholderCard] Document ID changed, fetching completions', { documentId });
      void processDocumentChange();
    } else {
      logger.debug('[PlaceholderCard] Clearing completions because documentId is undefined');
      completions = [];
      selectedCompletion = null;
      completionContent = '';
    }
  });

  // Separate the async processing to avoid issues with effects
  async function processDocumentChange() {
    if (!documentId || isProcessing) {
      return;
    }

    try {
      isProcessing = true;
      await fetchCompletions();
    } finally {
      isProcessing = false;
    }
  }

  async function fetchCompletions() {
    if (!documentId) {
      logger.debug('[PlaceholderCard] Aborting fetchCompletions: No document selected');
      error = 'No document selected';
      return;
    }

    try {
      logger.debug('[PlaceholderCard] Starting to fetch completions', { documentId });
      loading = true;
      error = null;

      // Fetch completions for this document
      logger.debug('[PlaceholderCard] Sending request to get completion IDs', {
        url: `${config.api.baseUrl}/completions/?document_id=${documentId}`,
      });
      const completionIds = await fetchApi<string[]>(
        `${config.api.baseUrl}/completions/?document_id=${documentId}`
      );
      completions = completionIds;

      logger.debug('[PlaceholderCard] Completions fetched', {
        documentId,
        completionCount: completionIds.length,
        completionIds,
      });

      if (completionIds.length > 0) {
        // If completions exist, get the first one
        logger.debug('[PlaceholderCard] Fetching first completion', {
          completionId: completionIds[0],
          url: `${config.api.baseUrl}/completions/${completionIds[0]}`,
        });

        const completionData = await fetchApi<CompletionResponse>(
          `${config.api.baseUrl}/completions/${completionIds[0]}`
        );
        selectedCompletion = completionData;

        logger.debug('[PlaceholderCard] Retrieved completion', {
          id: completionData.id,
          model: completionData.model,
          hasSystemPrompt: !!completionData.system_prompt_id,
          hasUserPrompt: !!completionData.user_prompt_id,
          contextTextLength: completionData.context_text?.length || 0,
        });

        // Extract the completion content from the context_text
        if (completionData.context_text && completionData.context_text.length > 0) {
          logger.debug('[PlaceholderCard] Processing completion content', {
            contextTextLength: completionData.context_text.length,
          });

          // Find the assistant message, which contains the completion
          const assistantMessage = completionData.context_text.find(
            (msg) => typeof msg === 'object' && msg && 'role' in msg && msg.role === 'assistant'
          );

          if (assistantMessage && 'content' in assistantMessage) {
            completionContent = String(assistantMessage.content);
            logger.debug('[PlaceholderCard] Found assistant message content', {
              contentLength: completionContent.length,
              contentPreview:
                completionContent.substring(0, 50) + (completionContent.length > 50 ? '...' : ''),
            });
          } else {
            logger.warn('[PlaceholderCard] No assistant message found in completion', {
              messageRoles: completionData.context_text
                .filter((msg) => typeof msg === 'object' && msg && 'role' in msg)
                .map((msg) => (msg as any).role),
            });
            completionContent = 'No content found in completion';
          }
        } else {
          logger.warn('[PlaceholderCard] Completion has no context_text');
          completionContent = 'No content found in completion';
        }
      } else {
        // If no completions exist, fetch prompts to create a new one
        logger.debug('[PlaceholderCard] No existing completions, will create a new one');
        await fetchPrompts();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('[PlaceholderCard] Error fetching completions', {
        documentId,
        errorMessage,
        error: err,
      });
      error = errorMessage;
    } finally {
      loading = false;
      logger.debug('[PlaceholderCard] fetchCompletions completed', {
        hasError: !!error,
        hasContent: !!completionContent,
        completionCount: completions.length,
      });
    }
  }

  async function fetchPrompts() {
    try {
      logger.debug('[PlaceholderCard] Starting to fetch prompts');

      // Fetch system prompts
      logger.debug('[PlaceholderCard] Fetching system prompts', {
        url: `${config.api.baseUrl}/prompts/by-role/system`,
      });
      systemPrompts = await fetchApi<PromptResponse[]>(
        `${config.api.baseUrl}/prompts/by-role/system`
      );
      logger.debug('[PlaceholderCard] System prompts fetched', {
        count: systemPrompts.length,
        promptNames: systemPrompts.map((p) => p.name),
      });

      // Fetch user prompts
      logger.debug('[PlaceholderCard] Fetching user prompts', {
        url: `${config.api.baseUrl}/prompts/by-role/user`,
      });
      userPrompts = await fetchApi<PromptResponse[]>(`${config.api.baseUrl}/prompts/by-role/user`);
      logger.debug('[PlaceholderCard] User prompts fetched', {
        count: userPrompts.length,
        promptNames: userPrompts.map((p) => p.name),
      });

      // Create a new completion if we have prompts and a document
      if (systemPrompts.length > 0 && userPrompts.length > 0 && documentId) {
        logger.debug('[PlaceholderCard] Have all required data, creating completion', {
          systemPromptId: systemPrompts[0].id,
          systemPromptName: systemPrompts[0].name,
          userPromptId: userPrompts[0].id,
          userPromptName: userPrompts[0].name,
          documentId,
        });
        await createCompletion();
      } else {
        logger.warn('[PlaceholderCard] Missing data required to create completion', {
          haveSystemPrompts: systemPrompts.length > 0,
          haveUserPrompts: userPrompts.length > 0,
          haveDocumentId: !!documentId,
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('[PlaceholderCard] Error fetching prompts', {
        errorMessage,
        error: err,
      });
      error = errorMessage;
    }
  }

  async function createCompletion() {
    if (!documentId || systemPrompts.length === 0 || userPrompts.length === 0) {
      logger.warn('[PlaceholderCard] Aborting createCompletion: Missing required data', {
        haveDocumentId: !!documentId,
        systemPromptsCount: systemPrompts.length,
        userPromptsCount: userPrompts.length,
      });
      error = 'Missing required data to create completion';
      return;
    }

    try {
      logger.debug('[PlaceholderCard] Starting to create completion', {
        documentId,
        systemPromptId: systemPrompts[0].id,
        userPromptId: userPrompts[0].id,
      });
      loading = true;
      error = null;

      // Create payload for the completion request
      const payload = {
        system_prompt_id: systemPrompts[0].id,
        user_prompt_id: userPrompts[0].id,
        document_ids: [documentId],
        model: 'my-gemma:latest', // Using a default model
        temperature: 0.7,
      };

      logger.debug('[PlaceholderCard] Sending completion creation request', {
        url: `${config.api.baseUrl}/completions/`,
        payload,
      });

      // Create a new completion using the first system and user prompts
      const completionData = await fetchApi<CompletionResponse>(
        `${config.api.baseUrl}/completions/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      );

      selectedCompletion = completionData;
      logger.debug('[PlaceholderCard] Completion created successfully', {
        id: completionData.id,
        model: completionData.model,
        hasContextText: completionData.context_text && completionData.context_text.length > 0,
      });

      // Fetch the created completion to get its content
      if (completionData.id) {
        logger.debug('[PlaceholderCard] Fetching full completion data', {
          completionId: completionData.id,
          url: `${config.api.baseUrl}/completions/${completionData.id}`,
        });
        const fullCompletion = await fetchApi<CompletionResponse>(
          `${config.api.baseUrl}/completions/${completionData.id}`
        );

        // Extract the completion content
        if (fullCompletion.context_text && fullCompletion.context_text.length > 0) {
          logger.debug('[PlaceholderCard] Processing context_text from full completion', {
            contextTextLength: fullCompletion.context_text.length,
          });

          const assistantMessage = fullCompletion.context_text.find(
            (msg) => typeof msg === 'object' && msg && 'role' in msg && msg.role === 'assistant'
          );

          if (assistantMessage && 'content' in assistantMessage) {
            completionContent = String(assistantMessage.content);
            logger.debug('[PlaceholderCard] Found assistant message in full completion', {
              contentLength: completionContent.length,
              contentPreview:
                completionContent.substring(0, 50) + (completionContent.length > 50 ? '...' : ''),
            });
          } else {
            logger.warn('[PlaceholderCard] No assistant message found in full completion', {
              messageRoles: fullCompletion.context_text
                .filter((msg) => typeof msg === 'object' && msg && 'role' in msg)
                .map((msg) => (msg as any).role),
            });
            completionContent = 'No content found in completion';
          }
        } else {
          logger.warn('[PlaceholderCard] Full completion has no context_text');
          completionContent = 'No content found in completion';
        }
      } else {
        logger.warn('[PlaceholderCard] Created completion has no ID');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      logger.error('[PlaceholderCard] Error creating completion', {
        documentId,
        errorMessage,
        error: err,
      });
      error = errorMessage;
    } finally {
      loading = false;
      logger.debug('[PlaceholderCard] createCompletion completed', {
        hasError: !!error,
        hasContent: !!completionContent,
        contentLength: completionContent.length,
      });
    }
  }

  // Render markdown content safely
  function renderMarkdown(text: string): string {
    // Parse markdown to HTML
    const rawHtml = marked(text);
    // Sanitize the HTML to prevent XSS attacks
    return DOMPurify.sanitize(rawHtml);
  }
</script>

<div class="placeholder-card card">
  <h2>Analysis Panel</h2>

  {#if !documentId}
    <div class="placeholder-content">
      <p>Select a document to analyze.</p>
    </div>
  {:else if loading}
    <div class="loading-container">
      <p>Loading analysis...</p>
    </div>
  {:else if error}
    <div class="error-container">
      <p class="error">Error: {error}</p>
    </div>
  {:else if completionContent}
    <div class="completion-content">
      {@html renderMarkdown(completionContent)}
    </div>
  {:else}
    <div class="placeholder-content">
      <p>No analysis available for this document yet.</p>
    </div>
  {/if}
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

  .loading-container {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .error-container {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .error {
    color: var(--color-error);
  }

  .completion-content {
    flex-grow: 1;
    overflow-y: auto;
    padding: var(--space-md);
    line-height: 1.5;
  }
</style>
