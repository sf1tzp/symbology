import type {
    CompanyResponse,
    AggregateResponse,
    CompletionResponse,
    DocumentResponse,
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

    // UI state
    isDarkMode: false,

    // Loading states
    loading: {
        company: false,
        aggregate: false,
        completion: false,
        document: false,
    },

    // Error states
    errors: {
        company: null as string | null,
        aggregate: null as string | null,
        completion: null as string | null,
        document: null as string | null,
    },

    // Derived state
    currentView: () => {
        if (appState.selectedDocument) return 'document';
        if (appState.selectedCompletion) return 'completion';
        if (appState.selectedAggregate) return 'aggregate';
        if (appState.selectedCompany) return 'company';
        return 'empty';
    },
});

// Actions for state management
export const actions = {
    // Company actions
    selectCompany: (company: CompanyResponse) => {
        logger.debug('[StateManager] Selecting company', { company });
        appState.selectedCompany = company;
        // Clear downstream selections
        appState.selectedAggregate = null;
        appState.selectedCompletion = null;
        appState.selectedDocument = null;
        // Clear errors
        appState.errors.company = null;
    },

    // Aggregate actions
    selectAggregate: (aggregate: AggregateResponse) => {
        logger.debug('[StateManager] Selecting aggregate', { aggregate });
        appState.selectedAggregate = aggregate;
        // Clear downstream selections
        appState.selectedCompletion = null;
        appState.selectedDocument = null;
        // Clear errors
        appState.errors.aggregate = null;
    },

    // Completion actions
    selectCompletion: (completion: CompletionResponse) => {
        logger.debug('[StateManager] Selecting completion', { completion });
        appState.selectedCompletion = completion;
        // Clear downstream selections
        appState.selectedDocument = null;
        // Clear errors
        appState.errors.completion = null;
    },

    // Document actions
    selectDocument: (document: DocumentResponse) => {
        logger.debug('[StateManager] Selecting document', { documentId: document.id, documentName: document.document_name });
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
        logger.debug('[StateManager] Clearing all selections');
        appState.selectedCompany = null;
        appState.selectedAggregate = null;
        appState.selectedCompletion = null;
        appState.selectedDocument = null;
        // Clear all errors
        Object.keys(appState.errors).forEach(key => {
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

export default appState;