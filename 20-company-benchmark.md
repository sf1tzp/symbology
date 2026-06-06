# Usage after 20 companies, 3 year 10-K lookback

```
steven 🌀 devbox ~/worktrees/symbology/raw-filings-brush-up                                                            [symbology v3.13.2] | raw-filings-brush-up 2 M -- 12:12:07 UTC
 >  j cli db status
just -d server -f server/justfile cli db status
uv run -m symbology.cli.main db status
Database: 10.0.0.32:5432/fortune500

               Objects
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Type                     ┃   Rows ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Companies                │     20 │
│ Filings                  │     60 │
│ Documents                │    470 │
│ Document chunks          │ 10,174 │
│ Chunk topics             │  4,300 │
│ Generated content        │    794 │
│ Generated content chunks │      0 │
│ Diff sets                │    120 │
│ Section diffs            │  8,074 │
│ Jobs                     │    247 │
└──────────────────────────┴────────┘

               Documents by type
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━┓
┃ Document type          ┃ Rows ┃ Substantive ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━┩
│ market_risk            │   60 │          48 │
│ business_description   │   60 │          60 │
│ risk_factors           │   60 │          60 │
│ controls_procedures    │   60 │          60 │
│ management_discussion  │   60 │          54 │
│ directors_officers     │   58 │          28 │
│ legal_proceedings      │   57 │          24 │
│ executive_compensation │   55 │           4 │
└────────────────────────┴──────┴─────────────┘

      Generated content by stage
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┓
┃ Content stage        ┃ Rows ┃ Depth ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━┩
│ document_page_intro  │  239 │     2 │
│ single_summary       │  239 │     1 │
│ change_report_intro  │   78 │     3 │
│ change_report        │   78 │     2 │
│ filing_intro         │   60 │     3 │
│ filing_main_content  │   60 │     2 │
│ company_main_content │   20 │     3 │
│ company_intro        │   20 │     4 │
└──────────────────────┴──────┴───────┘

                             Embeddings
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ Chunk table              ┃  Total ┃ Embedded ┃ Pending ┃ Coverage ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ Document chunks          │ 10,174 │   10,174 │       0 │   100.0% │
│ Generated content chunks │      0 │        0 │       0 │        - │
└──────────────────────────┴────────┴──────────┴─────────┴──────────┘

 Section diffs by change
          kind
┏━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Change kind   ┃  Rows ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━┩
│ removed       │ 2,274 │
│ new           │ 2,046 │
│ reworded      │ 1,804 │
│ unchanged     │ 1,131 │
│ escalated     │   416 │
│ de_emphasised │   403 │
└───────────────┴───────┘

                                 Disk usage (top 15)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Table                                  ┃    Total ┃    Table ┃  Indexes ┃   TOAST ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ document_chunks                        │  92.1 MB │  10.1 MB │  40.3 MB │ 41.7 MB │
│ chunk_topics                           │  20.9 MB │ 792.0 KB │ 352.0 KB │ 19.8 MB │
│ section_diffs                          │  12.0 MB │   7.4 MB │   1.1 MB │  3.5 MB │
│ documents                              │   6.5 MB │ 328.0 KB │ 136.0 KB │  6.1 MB │
│ generated_content                      │   2.4 MB │ 648.0 KB │ 392.0 KB │  1.4 MB │
│ financial_values                       │ 480.0 KB │ 224.0 KB │ 224.0 KB │ 32.0 KB │
│ financial_concepts                     │ 264.0 KB │ 120.0 KB │ 112.0 KB │ 32.0 KB │
│ jobs                                   │ 248.0 KB │ 112.0 KB │  96.0 KB │ 40.0 KB │
│ filings                                │ 192.0 KB │  16.0 KB │ 144.0 KB │ 32.0 KB │
│ generated_content_source_association   │ 192.0 KB │  96.0 KB │  64.0 KB │ 32.0 KB │
│ companies                              │ 136.0 KB │  16.0 KB │  88.0 KB │ 32.0 KB │
│ diff_sets                              │ 128.0 KB │  48.0 KB │  48.0 KB │ 32.0 KB │
│ document_page_content                  │ 104.0 KB │  32.0 KB │  48.0 KB │ 24.0 KB │
│ filing_page_content_document           │  80.0 KB │  24.0 KB │  32.0 KB │ 24.0 KB │
│ generated_content_document_association │  80.0 KB │  24.0 KB │  32.0 KB │ 24.0 KB │
└────────────────────────────────────────┴──────────┴──────────┴──────────┴─────────┘
```