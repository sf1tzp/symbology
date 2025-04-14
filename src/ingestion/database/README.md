# Database Structure

## Overview

The Symbology database uses SQLAlchemy ORM with PostgreSQL to store financial data, company information, and AI-related data. The database is organized into several key areas:

1. **Company & Filing Data**: Core entities representing companies and their SEC filings
2. **Financial Statements**: Structured financial data extracted from XBRL filings
3. **Source Documents**: Full-text documents extracted from company filings
4. **AI Infrastructure**: Prompts, completions, and user feedback for AI-generated analysis

## Entity Relationships

```
Company 1──┐
           │
           ├─N Filing 1──┐
           │             │
           │             ├─N SourceDocument
           │             │
           │             ├─N BalanceSheetValue
           │             │
           │             ├─N IncomeStatementValue
           │             │
           │             └─N CashFlowStatementValue
           │
           ├─N BalanceSheetValue
           │
           ├─N IncomeStatementValue
           │
           └─N CashFlowStatementValue
```

```
PromptTemplate 1───N AICompletion N───M SourceDocument
                              │
                              ├───N CompletionRating
                              │
                              └───M AICompletion (self-referential)
```

## Key Models

- **Company**: Company information (CIK, name, tickers, exchange, etc.)
- **Filing**: SEC filing metadata (type, date, accession number)
- **FinancialConcept**: Financial concepts like revenue, assets, etc.
- **Statement Models**: Balance sheet, income statement, cash flow statement values
- **SourceDocument**: Full-text documents from filings
- **PromptTemplate**: Customizable templates for AI queries
- **AICompletion**: Generated AI text with metadata and parameters
- **CompletionRating**: User feedback on AI-generated content

## Notes on Implementation

# Why use Raw SQL in some crud functions?

Raw SQL is used in the `get_balance_sheet_by_date()` and `get_income_statement_by_date()` functions for performance reasons:

1. **Window Function Support**: The code uses `ROW_NUMBER() OVER (PARTITION BY...)` window functions which are more verbose and complex to express in SQLAlchemy's ORM syntax, especially the ranking operations.

2. **Complex Query Structure**: The query uses a Common Table Expression (CTE) with `WITH ranked_values AS (...)` to create a temporary result set that's then filtered. This pattern is more straightforward in raw SQL.

3. **Performance Overhead**: SQLAlchemy's ORM adds abstraction layers that can introduce performance overhead, particularly for complex queries with window functions and subqueries.

4. **Date-Based Proximity Logic**: The query finds the closest financial data to a given date using `ORDER BY ABS(EXTRACT(EPOCH FROM (value_date - :target_date)))`, which would require more verbose code in SQLAlchemy's expression language.

5. **Query Readability**: For complex financial data queries, raw SQL can sometimes be more readable and maintainable than equivalent ORM code.

For simpler CRUD operations elsewhere in the file, the code uses SQLAlchemy's ORM approach, which provides better type safety and abstraction. The hybrid approach uses each tool where it makes the most sense.