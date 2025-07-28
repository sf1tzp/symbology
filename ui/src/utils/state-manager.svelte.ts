import type {
  CompanyResponse,
  AggregateResponse,
  CompletionResponse,
  DocumentResponse,
  FilingResponse,
} from './generated-api-types';
import { getLogger } from './logger';

const logger = getLogger('StateManager');

// Application state using runes
export const appState = $state({
  // Selected entities
  selectedCompany: null as CompanyResponse | null,
  selectedAggregate: null as AggregateResponse | null,
  selectedCompletion: null as CompletionResponse | null,
  selectedDocument: null as DocumentResponse | null,
  selectedFiling: null as FilingResponse | null,

  // UI state
  isDarkMode: false,
  disclaimerAccepted: false,

  // Loading states
  loading: {
    company: false,
    aggregate: false,
    completion: false,
    document: false,
    filing: false,
  },

  // Error states
  errors: {
    company: null as string | null,
    aggregate: null as string | null,
    completion: null as string | null,
    document: null as string | null,
    filing: null as string | null,
  },

  // Derived state
  currentView: () => {
    if (appState.selectedDocument) return 'document';
    if (appState.selectedCompletion) return 'completion';
    if (appState.selectedAggregate) return 'aggregate';
    if (appState.selectedFiling) return 'filing';
    if (appState.selectedCompany) return 'company';
    return 'empty';
  },
});

// Actions for state management
export const actions = {
  // Company actions
  selectCompany: (company: CompanyResponse) => {
    logger.info('company_selected', { companyId: company.id });
    appState.selectedCompany = company;
    // Clear downstream selections
    appState.selectedAggregate = null;
    appState.selectedCompletion = null;
    appState.selectedDocument = null;
    appState.selectedFiling = null;
    // Clear errors
    appState.errors.company = null;
  },

  // Filing actions
  selectFiling: (filing: FilingResponse) => {
    logger.info('filing_selected', { filingId: filing.id });
    appState.selectedFiling = filing;
    // Clear downstream selections and conflicting selections
    appState.selectedDocument = null;
    appState.selectedCompletion = null;
    appState.selectedAggregate = null;
    // Clear errors
    appState.errors.filing = null;
  },

  // Aggregate actions
  selectAggregate: (aggregate: AggregateResponse) => {
    logger.info('aggregate_selected', { aggregateId: aggregate.id });
    appState.selectedAggregate = aggregate;
    // Clear downstream selections
    appState.selectedCompletion = null;
    appState.selectedDocument = null;
    appState.selectedFiling = null;
    // Clear errors
    appState.errors.aggregate = null;
  },

  // Completion actions
  selectCompletion: (completion: CompletionResponse) => {
    logger.info('completion_selected', { completionId: completion.id });
    appState.selectedCompletion = completion;
    // Clear downstream selections
    appState.selectedDocument = null;
    appState.selectedFiling = null;
    // Clear errors
    appState.errors.completion = null;
  },

  // Document actions
  selectDocument: (document: DocumentResponse) => {
    logger.info('document_selected', { documentId: document.id });
    appState.selectedDocument = document;
    // Clear errors
    appState.errors.document = null;
  },

  // Loading state actions
  setLoading: (key: keyof typeof appState.loading, loading: boolean) => {
    appState.loading[key] = loading;
  },

  // Error state actions
  setError: (key: keyof typeof appState.errors, error: string | null) => {
    appState.errors[key] = error;
  },

  // Clear all selections
  clearAll: () => {
    logger.info('state_cleared');
    appState.selectedCompany = null;
    appState.selectedAggregate = null;
    appState.selectedCompletion = null;
    appState.selectedDocument = null;
    appState.selectedFiling = null;
    // Clear all errors
    Object.keys(appState.errors).forEach((key) => {
      appState.errors[key as keyof typeof appState.errors] = null;
    });
  },

  // Theme actions
  toggleTheme: () => {
    appState.isDarkMode = !appState.isDarkMode;
    updateThemeClass();
    saveThemePreference();
  },

  initializeTheme: () => {
    const savedTheme = localStorage.getItem('theme');
    appState.isDarkMode = savedTheme === 'dark';
    updateThemeClass();
  },

  // Disclaimer actions
  acceptDisclaimer: () => {
    logger.info('disclaimer_accepted');
    appState.disclaimerAccepted = true;
    saveDisclaimerAcceptance();
  },

  initializeDisclaimer: () => {
    const disclaimerAccepted = localStorage.getItem('disclaimerAccepted');
    appState.disclaimerAccepted = disclaimerAccepted === 'true';
  },

  // Navigation actions
  navigateBack: () => {
    logger.info('navigation_back', { currentView: appState.currentView() });

    // Navigate back based on current hierarchy
    if (appState.selectedDocument) {
      // From Document → go back to the parent (Completion, Filing, or Aggregate)
      appState.selectedDocument = null;
      appState.errors.document = null;
    } else if (appState.selectedCompletion) {
      // From Completion → go back to Aggregate
      appState.selectedCompletion = null;
      appState.errors.completion = null;
    } else if (appState.selectedAggregate) {
      // From Aggregate → go back to Company
      appState.selectedAggregate = null;
      appState.errors.aggregate = null;
    } else if (appState.selectedFiling) {
      // From Filing → go back to Company
      appState.selectedFiling = null;
      appState.errors.filing = null;
    }
    // Note: We don't clear selectedCompany as that's handled by the CompanySelector's "Clear" button
  },

  // Navigate back from company level (clears company selection)
  navigateBackFromCompany: () => {
    logger.info('navigation_back_from_company');
    // This is equivalent to clearAll, but more semantic for navigation
    actions.clearAll();
  },

  // Helper to check if back navigation is available
  canNavigateBack: () => {
    return (
      appState.selectedDocument ||
      appState.selectedCompletion ||
      appState.selectedAggregate ||
      appState.selectedFiling
    );
  },

  // Helper to check if we can navigate back from company level
  canNavigateBackFromCompany: () => {
    return (
      appState.selectedCompany !== null &&
      !appState.selectedDocument &&
      !appState.selectedCompletion &&
      !appState.selectedAggregate &&
      !appState.selectedFiling
    );
  },
};

// Helper functions
function updateThemeClass() {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', appState.isDarkMode);
  }
}

function saveThemePreference() {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('theme', appState.isDarkMode ? 'dark' : 'light');
  }
}

function saveDisclaimerAcceptance() {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('disclaimerAccepted', 'true');
  }
}

export default appState;
