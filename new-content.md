# New Content Features

We've recently received a design mockup (~/symbology-design) and are planning how to implement the various blocks of content needed for each page. As we expand the volume of generated content, we're taking a moment to check our posture and ensure we proceed on solid footing.

## Generation Depth

Introduce a "generation_depth" heuristic on Generated Content representing 'how far away from source' a piece of generated content is. This wil be used internally and also shown on the site to give users more context about the displayed content.

Source Documents -> Summary (l1) -> Aggregate Summary (l2) -> Page Content (l3) -> Page Subheading (l4) ...

## Additional Page Content & Standardization

### Document Analysis and Change Reporting

These generations form the foundation for populating content on our various pages. For each filing, we extract a standard set of Documents.

Each Document type is Summarized, and the past n l1 Document Summaries are aggregated to produce a l2 Document {type} Change Report.

Each l2 Change Report then gets a brief introduction (2-3) sentences.

Generations:

1. Single Source Document {type} -> l1 Document {type} Summary
2. Multiple l1 Document Summaries -> l2 Document {type} Change Report
3. Each l2 Document {type} Change Report -> l3 Change Report Introduction

### Company Page Content

Each Company Page derives it's l3 main page content from the l2 Business Description Change Report.

Each l3 Company Main Content also gets a brief introduction (2-3 sentences)

Generations:

1. l2 Business Description Change Report -> l3 Company Main Content
2. l3 Company Main Content -> l4 Company Introduction

### Group Page Content

Each Group analysis is derived from the member companies l2 Business Description Change Reports.

Each l3 Group Main Content also gets a brief introduction (2-3 sentences)

Generations:

1. Multiple l2 summaries (from different companies) -> l3 Group Main Content
2. l3 Group Main Content -> l4 Group introduction

### Filing Page Content

The Filing Page content is derived from its Document's l1 Document Summaries

Each l3 Filing Main Content also gets a brief introduction (2-3 sentences)

1. Multiple l1 Document Summaries -> l2 Filing Main Content
2. l2 Filing Main Content -> l3 Filing Introduction

### Document Page Content

The main content of the Document Page is the source document and its l1 Document Summary.

We also need a breif introduction for the Document.

1. l1 Document Summary -> l2 Document Page Introduction


## Prompt and Model Config Organization

We have a loose collection of prompt files under server/prompts/

ModelConfigs are loosely defined in code that invokes the LLM

Prompts and ModelConfigs are stored in the DB and associated with GeneratedContent (and displayed on the site)

Prompts are currently only indexed by a string (directory name under prompts/ , derived by document type or descriptive text eg 'aggregate-summary')

### Seeking Organization

We're seeking a more consolidated approach, maybe using yaml to store model configuration close to the prompts?

```
prompts/
├── model_configs.yaml
├── l1/
    ├── business_description.md
    ├── management_discussion.md
    ├── market_risk.md
    ├── controls_procedures.md
    └── risk_factors.md

├── l2/
    ├── change-report.md
    ├── filing-main-content.md
    └── document-intro-content.md

├── l3/
    ├── company-main-content.md
    ├── group-main-content.md
    └── filing-intro-content.md


├── l4/
    ├── company-intro-content.md
    └── group-intro-content.md
```

Pipeline workers would reference the yaml file at runtime and insert new ModelConfigs at runtime. Something like:

```
model_configs:
  - name: "l1_document_summary"
    model: "claude-sonnet"
    temperature: 0.3
    num_predict: 8192
    num_ctx: 65536 # high context for long source documents
  ...
  - name: "l4_company-intro-content"
    model: "claude-sonnet"
    temperature: 0.8
    num_predict: 300 # lower request for intro content
    num_ctx: 8192
```


#### Worker LLM Client Flexibility

We recently added an Open AI compatibile endpoint to our internal infrastructure. We use this for generating embeddings from Documents and Generated Content.

It would be nice to update our workers to support BOTH Anthropic APIs and our internal LLM API, and for this to be dynamically inferred from the model_configs yaml:

```
model: "claude-sonnet" # Anything Claude -> Anthropic API
model: "google/gemma-4-e4b" # Any other model -> Internal Open AI API
```





----

Just thinking about how the pipeline will look in the end. Right now we just have handle_full_pipeline but I'm thinking of breaking it up - or making it more 'page' oriented. Something like this?

  ```
  document_page_content_pipeline(Document):
      l1 document summary
      l2 document page intro

  filing_page_content_pipeline(Filing):
      for document in filing:
          document_page_content(document)

      l2 filing page main content
      l3 filing page intro content


  change_report_content_pipeline(documents Document[]):
      get_n_l1_document_summaries(documents)
      l2 change report main content
      l3 change report intro content

  company_page_content_pipeline(Company):
      Filings = last_5_tenk_s(Company)

      for doc_type in change_report_doc_types:
          # get documents from filings ...
          change_report_pipeline(documents)

   .  l3 company main content
      l4 comapny intro content


  group_page_content_pipeline(companies Company[]):
      # get company l2 business description summaries
      l3 group main content
      l4 group intro content
  ```

  And while writing that, it occurred to me that we might want to introduce 'PageContent' as a formal data concept. A layer which lets us keep track of everything published, publish sweeping revisions that cover every
  piece of content etc

  Eg, CompanyPageContent might look like

  ```
  CompanyPageContent:
      company: contoso
      source_filings:
          - 10-K 2026
          - 10-K 2025
          - 10-K 2024
          - 10-K 2023
          - 10-K 2022
          - 10-K 2021
      intro_content: abc123
      main_content: abc123
      change_reports:
          - business_description: abc123
          - management_discussion: abc123
          - risk_factors: abc123
          ...
      created_at: 2026-01-01
  ```
