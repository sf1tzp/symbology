/**
 * Mock data for development while the migration is in progress
 */

export interface MockGeneratedContent {
    id: string;
    content_hash: string | null;
    short_hash: string | null;
    company_id: string | null;
    document_type: string | null;
    source_type: string;
    created_at: string;
    total_duration: number | null;
    content: string | null;
    summary: string | null;
    model_config_id: string | null;
    system_prompt_id: string | null;
    user_prompt_id: string | null;
    source_document_ids: string[];
    source_content_ids: string[];
}

export interface MockModelConfig {
    id: string;
    name: string;
    created_at: string;
    options: Record<string, any> | null;
    num_ctx: number | null;
    temperature: number | null;
    top_k: number | null;
    top_p: number | null;
    seed: number | null;
    num_predict: number | null;
    num_gpu: number | null;
}

export interface MockCompany {
    id: string;
    cik: string;
    name: string;
    display_name: string;
    is_company: boolean;
    tickers: string[];
    exchanges: string[];
    sic: string;
    sic_description: string;
    fiscal_year_end: string;
    entity_type: string;
    ein: string;
    former_names: Array<{
        name: string;
        date_changed: string;
    }>;
    summary: string | null;
}

export interface MockDocument {
    id: string;
    filing_id: string | null;
    company_id: string;
    document_name: string;
    content: string | null;
}

export const mockGeneratedContent: MockGeneratedContent = {
    id: "123e4567-e89b-12d3-a456-426614174007",
    content_hash: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
    short_hash: "a1b2c3d4e5f6",
    company_id: "123e4567-e89b-12d3-a456-426614174000",
    document_type: "MDA",
    source_type: "documents",
    created_at: "2023-12-25T12:30:45.123456",
    total_duration: 3.8,
    content: `# Management's Discussion and Analysis - Key Insights

## Financial Performance Overview

The company has demonstrated strong financial performance throughout the fiscal year, with significant improvements in several key metrics:

- **Revenue Growth**: 15% year-over-year increase, reaching $2.8 billion
- **Operating Margin**: Improved to 22.5%, up from 19.3% in the previous year
- **Cash Position**: Strong balance sheet with $1.2 billion in cash and equivalents

## Strategic Initiatives

### Digital Transformation
The company continued its digital transformation initiatives, investing heavily in technology infrastructure and automation. These investments are expected to yield significant operational efficiencies over the next 2-3 years.

### Market Expansion
Successful expansion into three new international markets, contributing approximately 8% to total revenue growth. The company plans to continue this expansion strategy with entry into two additional markets next fiscal year.

### Product Innovation
Launch of five new product lines, with particularly strong reception for our premium offerings. R&D spending increased by 12% to support continued innovation.

## Risk Factors and Mitigation

The company faces several key risks including supply chain disruptions, regulatory changes, and increased competition. Management has implemented comprehensive risk mitigation strategies including supplier diversification and strategic partnerships.

## Outlook

Looking forward, the company is well-positioned for continued growth with strong fundamentals, robust cash position, and clear strategic direction. Management expects continued revenue growth in the range of 10-15% for the upcoming fiscal year.`,
    summary: "Comprehensive financial analysis showing strong performance with 15% revenue growth, improved margins, and successful market expansion. Digital transformation and product innovation remain key strategic priorities.",
    model_config_id: "123e4567-e89b-12d3-a456-426614174006",
    system_prompt_id: "123e4567-e89b-12d3-a456-426614174003",
    user_prompt_id: null,
    source_document_ids: ["123e4567-e89b-12d3-a456-426614174002", "123e4567-e89b-12d3-a456-426614174008"],
    source_content_ids: []
};

export const mockModelConfig: MockModelConfig = {
    id: "123e4567-e89b-12d3-a456-426614174006",
    name: "qwen3:14b",
    created_at: "2023-12-25T12:30:45.123456",
    options: {
        num_ctx: 8000,
        temperature: 0.8,
        top_k: 40,
        top_p: 0.9,
        seed: 42,
        num_predict: -1,
        num_gpu: 1
    },
    num_ctx: 8000,
    temperature: 0.8,
    top_k: 40,
    top_p: 0.9,
    seed: 42,
    num_predict: -1,
    num_gpu: 1
};

export const mockCompany: MockCompany = {
    id: "123e4567-e89b-12d3-a456-426614174000",
    cik: "0000320193",
    name: "Apple Inc.",
    display_name: "Apple Inc.",
    is_company: true,
    tickers: ["AAPL"],
    exchanges: ["NASDAQ"],
    sic: "3571",
    sic_description: "Electronic Computers",
    fiscal_year_end: "2023-09-30",
    entity_type: "CORPORATION",
    ein: "94-2404110",
    former_names: [
        {
            name: "Apple Computer, Inc.",
            date_changed: "2007-01-09"
        }
    ],
    summary: "Apple Inc. is a leading technology company that designs, develops and sells consumer electronics, computer software and online services..."
};

export const mockSourceDocuments: MockDocument[] = [
    {
        id: "123e4567-e89b-12d3-a456-426614174002",
        filing_id: "123e4567-e89b-12d3-a456-426614174001",
        company_id: "123e4567-e89b-12d3-a456-426614174000",
        document_name: "10-K Annual Report - Management Discussion & Analysis",
        content: null
    },
    {
        id: "123e4567-e89b-12d3-a456-426614174008",
        filing_id: "123e4567-e89b-12d3-a456-426614174001",
        company_id: "123e4567-e89b-12d3-a456-426614174000",
        document_name: "10-K Annual Report - Risk Factors",
        content: null
    }
];
