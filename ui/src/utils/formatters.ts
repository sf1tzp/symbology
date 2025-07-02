/**
 * Format a date string for display
 */
export function formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
}

/**
 * Extract year from a date string with type safety
 */
export function formatYear(dateString: string | undefined): string {
    if (!dateString) return '';
    try {
        const year = new Date(dateString).getFullYear();
        return isNaN(year) ? '' : year.toString();
    } catch {
        return '';
    }
}

/**
 * Format model name for display (replace underscores, uppercase)
 */
export function formatModelName(model: string): string {
    return model.replace('_', ' ').toUpperCase();
}

/**
 * Format document type names for display
 */
export function formatDocumentType(type: string): string {
    switch (type) {
        case 'MDA':
        case 'management_discussion':
            return 'Management Discussion & Analysis';
        case 'RISK_FACTORS':
        case 'risk_factors':
            return 'Risk Factors';
        case 'DESCRIPTION':
        case 'business_description':
            return 'Business Description';
        default:
            return type;
    }
}

/**
 * Clean content by removing <think> tags and internal reasoning patterns
 */
export function cleanContent(content: string | undefined): string | undefined {
    if (!content) return undefined;

    // Remove <think>...</think> blocks and any content before them
    let cleaned = content.replace(/<think>[\s\S]*?<\/think>\s*/gi, '');

    // Also handle cases where there might be thinking content without tags
    cleaned = cleaned.replace(
        /^(Okay,|Let me|I need to|First,|Based on)[\s\S]*?(?=\n\n|\. [A-Z])/i,
        ''
    );

    // Trim any remaining whitespace
    cleaned = cleaned.trim();

    return cleaned || undefined;
}

/**
 * Get filing type label for display
 */
export function getFilingTypeLabel(filingType: string): string {
    const typeLabels: Record<string, string> = {
        '10-K': 'Annual Report',
        '10-Q': 'Quarterly Report',
        '8-K': 'Current Report',
        '10-K/A': 'Annual Report (Amendment)',
        '10-Q/A': 'Quarterly Report (Amendment)',
        'DEF 14A': 'Proxy Statement',
        'S-1': 'Registration Statement',
        'S-3': 'Registration Statement',
        'S-4': 'Registration Statement',
        'S-8': 'Registration Statement',
    };
    return typeLabels[filingType] || filingType;
}

/**
 * Get document type name from document name patterns
 */
export function getDocumentTypeName(docName: string): string {
    // Extract meaningful name from document names like "10-K Annual Report - Risk Factors"
    if (docName.toLowerCase().includes('risk')) return 'Risk Factors';
    if (docName.toLowerCase().includes('mda') || docName.toLowerCase().includes('management'))
        return 'Management Discussion & Analysis';
    if (docName.toLowerCase().includes('description') || docName.toLowerCase().includes('business'))
        return 'Business Description';
    return docName;
}

export function formatTitleCase(name: string): string {
    if (!name) return '';

    return name
        .toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
