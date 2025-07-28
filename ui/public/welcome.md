# Explore LLM-generated insights on publicly traded companies.

Symbology leverages company filings to identify their trends and developments since the COVID-19 pandemic.

To effectively capture the full scope of these often extensive filings, we begin by using a smaller LLM with a large context window to ingest the source material. We then employ a ‘thinking’ model to compare each year’s report, highlighting changes and emerging trends over time.

Each report's generation process – including model, prompt engineering, and context – is fully documented, allowing you to trace the analysis back to the original SEC filings.  This allows for reproducible results by anyone with access to Ollama.

This website and all of it's content is open source! Star the repository [on Github](https://github.com/sf1tzp/symbology).

_Note: the contents of this site may change periodically as we ingest new data or experiment with new models._
