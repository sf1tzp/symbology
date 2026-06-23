# TenQ item-boundary detection scatters MD&A into a phantom "Part I, Item 6" (Freddie Mac 10-Q)

## Summary

For a Freddie Mac (FMCC) 10-Q, `TenQ` section/item detection mis-aligns the Part I
item boundaries. The bulk of MD&A (~165k chars) is assigned to a **phantom
`part_i_item_6`** — a 10-Q Part I only has Items 1–4 — while the real items return
tiny, mislabeled scraps:

- `Part I, Item 2` (MD&A) returns a 1,264-char fragment (a single net-interest-income table).
- `Part I, Item 4` (Controls & Procedures) returns a *non-interest-income* MD&A table — wrong section content entirely.

The likely trigger is the filing's repeating page headers ("Management's Discussion
and Analysis" appears 36 times as a running header), which the boundary detector
appears to treat as section starts.

## Environment

- `edgartools` 5.36.0 (also reviewed 5.39.0 release notes; parser work noted for other form types)
- Python 3.13.2

## Filing

- Company: FEDERAL HOME LOAN MORTGAGE CORP (FMCC), CIK 0001026214
- Form: 10-Q, period 2026-03-31, filed 2026-04-30
- Accession: 0001026214-26-000027

## Reproduction

```python
import os
os.environ.setdefault("EDGAR_IDENTITY", "you your.email@example.com")
from edgar import Company

f = Company("FMCC").get_filings(form="10-Q").head(1)[0]
obj = f.obj()                       # TenQ
print(type(obj).__name__)
print("full text:", len(f.text()))  # ~379,149

# Detected items include phantom Part I, Item 5 and Item 6:
print(obj.items)

# Per-section lengths show the bulk in a phantom Part I item:
for k, s in obj.sections.items():
    print(f"{k}: {len(s.text())}")

# The mapped items return scraps / wrong content:
for label, key in [("MD&A", "Part I, Item 2"),
                   ("MarketRisk", "Part I, Item 3"),
                   ("Controls", "Part I, Item 4")]:
    t = obj[key] or ""
    print(label, key, len(t))
```

## Observed

```
TenQ
full text: 379149

obj.items:
['Part I, Item 5', 'Part I, Item 6', 'Part II, Item 1', 'Part II, Item 1A',
 'Part II, Item 2', 'Part II, Item 5', 'Part II, Item 6', 'Part I, Item 1',
 'Part I, Item 2', 'Part I, Item 3', 'Part I, Item 4']

per-section lengths:
  part_i_item_1: 634
  part_i_item_2: 1264      <- MD&A scrap (single table)
  part_i_item_3: 1533
  part_i_item_4: 1082      <- "Controls" but actually an MD&A non-interest-income table
  part_i_item_5: 669       <- phantom (10-Q Part I has no Item 5)
  part_i_item_6: 165252    <- phantom; contains the real MD&A bulk
  part_ii_item_1: 2248
  part_ii_item_1a: 375
  part_ii_item_2: 2797
  part_ii_item_5: 8180
  part_ii_item_6: 8180

obj["Part I, Item 4"]  -> begins:
  "The table below presents the components of non-interest income.
   Table 4 - Components of Non-Interest Income ..."   (MD&A content, not Controls)

obj.sections["part_i_item_6"]  -> 165,252 chars, ends with:
  "... END OF CONDENSED CONSOLIDATED FINANCIAL STATEMENTS AND ACCOMPANYING NOTES
   Freddie Mac 1Q 2026 Form 10-Q77  Other Information ..."
```

The legacy fallback parser finds nothing here:

```python
obj.chunked_document.list_items()   # -> []
```

## Expected

- No phantom `part_i_item_5` / `part_i_item_6` for a 10-Q (Part I has Items 1–4 only).
- `Part I, Item 2` returns the full MD&A (the ~165k currently captured under the phantom item).
- `Part I, Item 4` returns the Controls & Procedures section, not an MD&A table.

## Impact

Downstream consumers that read `tenq["Part I, Item 2"]` (MD&A) get a misleading
1.2k-char fragment instead of the full section, and `Part I, Item 4` returns text
from the wrong section. Because the content is mis-attributed rather than missing,
length/quality heuristics can't reliably distinguish it from a genuinely short
section — the scraps look like valid short items.

## Notes

This appears specific to filers with this non-standard layout (heavy running page
headers; financial tables interleaved through MD&A). Standard 10-Q filers
(e.g. AAPL, KO) parse correctly — MD&A and Risk Factors return full-length sections.
Happy to provide additional problem filings if useful.
