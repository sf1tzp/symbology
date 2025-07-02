Symbology aims to automate the extraction of trends and other insights from the _qualitative_ reporting present in SEC filings. While this pro

SEC Filings are often extremely verbose. We start our analysis by using [edgartools](https://github.com/dgunning/edgartools) to extract three primary documents from each:
  - Business Description
  - Risk Factors
  - Management & Director Commentary

Each source document is first summarized with a small model, using as large a context window possible.

Those summaries are then aggregated together using a larger model. This lets us draw insights from changes in a company's behavior over time.

**This system is not been perfect**, and the nature of LLMs (and the quality of my prompts) has led to some known issues:
- Some documents are so verbose, they cannot fit into the 24k context window used for processing.
- Some generated aggregations focus on a single year.
- Some generated contents do not match the expected output format.
- Some companies use an inconsistent filing structure, so the extracted documents are not what we expect.
- Among others

However, we provide as much detail of the LLM completions as possible:
- Model Config (name, context, temperature, top p).
- The exact system prompt used in the completion.
- The exact context which was provided with the request.

So that users can better understand exactly how some generated text came to be.