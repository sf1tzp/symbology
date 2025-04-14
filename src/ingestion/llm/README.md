# AI Module Documentation

This module provides functionality for generating and managing AI completions using OpenAI APIs, storing results in the database, and analyzing the generated content.

## Components

- **client.py**: Handles direct communication with OpenAI API
- **completions.py**: Manages the process of generating, storing, and retrieving AI completions
- **prompts.py**: Contains prompt engineering utilities

## Usage Instructions

### Basic OpenAI Client Usage

The `OpenAIClient` class provides a simple interface for making requests to the OpenAI API:

```python
from ingestion.ai.client import OpenAIClient

# Initialize the client
client = OpenAIClient()

# Generate text with a simple prompt
response = client.generate_text(
    system_prompt="You are a financial analyst.",
    user_prompt="Summarize the key financial metrics for this quarter."
)

print(response)
```

### Using Context in Prompts

You can provide additional context to the model:

```python
# With additional context
context_texts = [
    "Revenue: $1.2M, up 15% YoY",
    "Net profit: $0.3M, up 8%",
    "Customer acquisition cost: $50, down 12%"
]

response = client.generate_text(
    system_prompt="You are a financial analyst.",
    user_prompt="Summarize the key financial metrics for this quarter.",
    context_texts=context_texts,
    temperature=0.3,  # More deterministic output
    max_tokens=500    # Limit response length
)
```

### Working with Prompt Templates and Database Storage

The `completions.py` module provides functions for working with templates and storing results:

```python
from sqlalchemy.orm import Session
from ingestion.database.base import SessionLocal
from ingestion.ai.completions import (
    create_predefined_prompt_templates,
    generate_and_store_completion,
    rate_completion,
    get_completion_dependency_chain
)

# Create a database session
db = SessionLocal()

try:
    # Create some predefined templates (or use existing ones)
    template_ids = create_predefined_prompt_templates(db)

    # Generate a completion using a template
    risk_analysis = generate_and_store_completion(
        db=db,
        prompt_template_id=template_ids["Risk Analysis"],
        user_prompt_vars={
            "company_name": "Apple Inc.",
            "document_type": "10-K Annual Report"
        },
        company_id=123,  # ID of the company in the database
        filing_id=456,   # ID of the filing in the database
        source_document_ids=[789, 790],  # IDs of source documents to use as context
        temperature=0.2
    )

    print(f"Generated completion ID: {risk_analysis.id}")
    print(risk_analysis.completion_text)

    # Add a rating for the completion
    rating = rate_completion(
        db=db,
        completion_id=risk_analysis.id,
        rating=4,  # 1-5 star rating
        accuracy_score=4,
        relevance_score=5,
        helpfulness_score=4,
        comments="Good analysis with concrete examples from the filing."
    )

    # Create a follow-up analysis that uses the first analysis as context
    follow_up = generate_and_store_completion(
        db=db,
        prompt_template_id=template_ids["Management Competency Assessment"],
        user_prompt_vars={
            "company_name": "Apple Inc.",
            "document_type": "10-K Annual Report"
        },
        company_id=123,
        filing_id=456,
        source_document_ids=[789, 790],
        context_completion_ids=[risk_analysis.id],  # Use previous analysis as context
        tags=["apple", "management", "2023"]
    )

    # Visualize the dependency chain between completions
    dependency_chain = get_completion_dependency_chain(db, follow_up.id)
    print(dependency_chain)

finally:
    db.close()
```

### Querying Completions from the Database

You can retrieve completions from the database using the CRUD operations:

```python
from ingestion.database.crud_ai_completion import (
    get_ai_completion,
    get_ai_completions,
    get_prompt_templates
)

# Get all active prompt templates
templates = get_prompt_templates(db, is_active=True)
for template in templates:
    print(f"{template.id}: {template.name} - {template.description}")

# Get completions for a specific company
apple_completions = get_ai_completions(
    db,
    company_id=123,
    limit=10
)

# Get completions that use a specific source document
document_completions = get_ai_completions(
    db,
    source_document_id=789
)

# Get completions that use another completion as context
dependent_completions = get_ai_completions(
    db,
    context_completion_id=risk_analysis.id
)

# Get completions with specific tags
tagged_completions = get_ai_completions(
    db,
    tags=["risk", "2023"]
)
```

## Advanced Usage: Multi-Step Analysis Chains

You can create chains of analysis where each step builds on previous completions:

```python
# Step 1: Financial position analysis
financial_analysis = generate_and_store_completion(
    db=db,
    prompt_template_id=template_ids["Financial Position Analysis"],
    user_prompt_vars={"company_name": "Tesla", "document_type": "Q1 2025 Report"},
    company_id=789,
    filing_id=101,
    source_document_ids=[555, 556]
)

# Step 2: Risk analysis building on financial analysis
risk_analysis = generate_and_store_completion(
    db=db,
    prompt_template_id=template_ids["Risk Analysis"],
    user_prompt_vars={"company_name": "Tesla", "document_type": "Q1 2025 Report"},
    company_id=789,
    filing_id=101,
    source_document_ids=[557],  # Risk factors section
    context_completion_ids=[financial_analysis.id]  # Use financial analysis as context
)

# Step 3: Executive summary that incorporates both analyses
executive_summary = generate_and_store_completion(
    db=db,
    prompt_template_id=template_ids["Business Model Summary"],
    user_prompt_vars={"company_name": "Tesla", "document_type": "Q1 2025 Report"},
    company_id=789,
    filing_id=101,
    context_completion_ids=[financial_analysis.id, risk_analysis.id]
)
```