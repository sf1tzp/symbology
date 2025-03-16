
from datetime import datetime
import argparse
import os
import ollama
import json
import time
from edgar import *

MODEL = "llama3.2-54k:latest"
EDGAR_CONTACT = os.getenv("EDGAR_CONTACT") if os.getenv("EDGAR_CONTACT") else exit(1)
OLLAMA_HOST = (
    os.getenv("OLLAMA_HOST") if os.getenv("OLLAMA_HOST") else "localhost:24098"
)

ollama_client = ollama.Client(host=f"http://{OLLAMA_HOST}")
set_identity(EDGAR_CONTACT)

def ollama_summarize(model, content, **kwargs):
    response = ollama_client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"Construct a high level analysis of {kwargs['name']} management's discussion for fiscal year ending {kwargs['year']}. Proivde a stuctured summary with sections `General Sentiment`, `Management Commentary`, `Important Challenges and Risks`, `Performance Wins`, and `Financial Highlights`'. Provide no other introduction or conclusion. Only provide sections using the names previously listed.",
            },
            {"role": "user", "content": content},
        ],
    )
    return response.message["content"]


def ollama_summarize_rollup(model, content, name):
    response = ollama_client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"Analyze these summaries of {name} management discussions. Consider each year's briefing in order. State any observations made about the company over time. Format your response in Markdown.",
            },
            {"role": "user", "content": content},
        ],
    )
    return response.message["content"]


def generate_management_discussion_summary(model, company, date="2020-01-01:"):
    token_count = 0
    ticker = company.tickers[0]
    output_dir = f"summaries/{ticker}"
    os.makedirs(output_dir, exist_ok=True)

    filings = company.get_filings(date=date, form="10-K")
    if filings == None:
        print(f"WARN: No filings found for {company.name}")
        return
    num_filings = len(filings)

    print(f"Summarizing {num_filings} 10-Ks for {ticker}")
    summaries = {}

    start = time.time()
    for f in filings:
        tenk = f.data_object()
        filing_date = f.filing_date
        reporting_date = datetime.strptime(f.period_of_report, "%Y-%m-%d")

        url = f.filing_url

        if not tenk.management_discussion:
            print(f"INFO: {ticker} {filing_date} has no management discussion")
            continue

        print(
            f"INFO: {ticker} {filing_date} discussion length {len(tenk.management_discussion)}"
        )
        summary = ollama_summarize(
            model,
            tenk.management_discussion,
            name=company.name,
            year=reporting_date,
        )
        token_count += len(summary)
        citation = f"\n\nsource: {url}"
        summary += citation

        file_path = os.path.join(output_dir, f"{filing_date}-10K-Summary.md")
        with open(file_path, "w") as file:
            file.write(summary)

        summaries[filing_date] = summary


    five_year_summary = ollama_summarize_rollup(
        model, str(summaries), name=company.name
    )

    file_path = os.path.join(output_dir, f"{num_filings} Year Roll Up.md")
    with open(file_path, "w") as file:
        file.write(five_year_summary)
        token_count += len(five_year_summary)

    duration = time.time() - start
    tokens_per_second = token_count / duration
    print(
        f"{company.name} ({ticker}) generated {token_count} tokens in {duration:.2f} seconds ({tokens_per_second:.2f} tokens/second)"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate management discussion summaries.")
    parser.add_argument("--tickers", nargs="+", required=True, help="List of tickers")
    parser.add_argument("--date", default="2020-01-01:", help="Date range for filings")
    parser.add_argument("--model", default=MODEL, help="Model name")
    args = parser.parse_args()

    for ticker in args.tickers:
        company = Company(ticker)
        if company is None:
            print(f"WARN: Unknown ticker {ticker}")
            continue

        print(json.dumps(company.to_dict(), indent=2))
        print(args.tickers)
        generate_management_discussion_summary(args.model, company, date=args.date)

if __name__ == "__main__":
    main()

# other interesting fields
# facts = company.get_facts()
# latest_tenk = company.latest_tenk
# print(len(latest_tenk.management_discussion))
# latest_tenk.income_statement.get_dataframe()
# latest_tenk.balance_sheet.get_dataframe()
# latest_tenk.cash_flow_statement.get_dataframe()
# latest_tenk._filing.view()
