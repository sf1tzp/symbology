
from datetime import datetime
import argparse
import os
import ollama
import json
import time
from edgar import *

MODEL = "gemma3:4b-42k"
EDGAR_CONTACT = os.getenv("EDGAR_CONTACT") if os.getenv("EDGAR_CONTACT") else exit(1)
OLLAMA_HOST = (
    os.getenv("OLLAMA_HOST") if os.getenv("OLLAMA_HOST") else "localhost:24098"
)

SYSTEM_PROMPTS = {
    "10-k Section 7 Summarize 1": "Construct a high level analysis of {company_name} management's discussion for fiscal year ending {fiscal_year}. Provide a stuctured summary with sections `General Sentiment`, `Management Commentary`, `Important Challenges and Risks`, `Strategy for Risk Mitigation`, `Results of Strategy Implementation`, `Performance Wins`, and `Financial Highlights`'. Do not emphasize successes more than failures in your analysis. Summarize every point made in the discussion. Provide no other introduction or conclusion.",

    "10-k Section 7 Summarize 2": """
        You are researching {company_name}'s management discussion and analysis for fiscal year {fiscal_year}. Your report will later be used in aggregate analysis, so it is important that it strictly adheres to the following structure. DO NOT provide any introduction or conclusion in your report.
        - General Sentiment
        - Management Commentary
        - Challenges and Risks
        - Risk Mitigation Strategy
        - Overall Performance
        - Noteworth Extras
        Use Markdown H2 (##) to denote each section.     """,

    "10-k Section 7 Summarize 3": """
        Your report MUST conform to this markdown structure:
        ```
        ## General Sentiment
        ## Management Commentary
        ## Challenges and Risks
        ## Risk Mitigation Strategy
        ## Overall Performance
        ## Noteworthy Extras
        ```
        Summarize the General Sentiment, Commentary from Mangement, Challenges and Risks facing the company, their Risk Mitigation Strategy, their Overall Performance, and any Noteworthy Extras present in the user's report.
    """,

    "10-k Section 7 Summarize 4": """
        Prepare a report from the user's input.
        Your report MUST conform to this markdown structure exactly (DO NOT provide any introduction or conclusion):
        ```
        ## General Sentiment
        ## Management Commentary
        ## Challenges and Risks
        ## Risk Mitigation Strategy
        ## Noteworthy Extras
        ```
        Summarize the General Sentiment expressed by the document.
        Summarize the statements and commentary from upper management.
        Provide detailed descriptions of any Challenges and Risks factors stated in the document.
        Summarize any plans to mitigate risk that are stated in the document.
        Provide a list of any noteworthy details that were not previously mentioned.
    """,

    "10-k Section 7 Summarize 5": """
        Prepare a report from the user's input.
        Your report MUST conform to this markdown structure exactly. (DO NOT provide any introduction or conclusion):
        ```
        ## General Sentiment
        ## Management Commentary
        ## Challenges and Risks
        ## Risk Mitigation Strategy
        ## Noteworthy Extras
        ```
        Summarize the General Sentiment expressed by the document.
        Summarize the statements and commentary from upper management.
        Provide detailed descriptions of any Challenges and Risks factors stated in the document.
        Summarize any plans to mitigate risk that are stated in the document.
        Provide a list of any noteworthy details that were not previously mentioned.
    """,


    "Multi 10-K Summary Analysis": "Analyze these summaries of {company_name} management discussions. Begin your analysis by briefly explaining the company's business. Next, consider each year's filing in order. Consider the general sentiment, stated challenges, risks, and mitigation strategies the company has tried. Summarize trends in these areas and make a note of any new developments in the most recent filing. Conclude by answering the questions:\n- Did the company follow through on their strategy commitments?\n- Did management react if their strategies did not yield results?\nSet aside all concerns and offer your opinion of confidence in the company's management.\n\nFormat the analysis in Markdown for readability.",


    "Multi 10-K Summary Analysis 2": """
        You will be given a series of reports. Consider the general sentiment, stated challenges, risks, and mitigation strategies the company has adopted over time.
        Write a short blog post summary about the input (formatted in markdown). Attempt to answer:
        - Does management follow through on their strategy commitments?
        - Does management react if their strategies do not yield results?
    """,

    "Multi 10-K Summary Analysis 3": """
        You will be given a series of annual reports. Compare the general sentiment, management commentary, stated challenges, risks, and mitigation strategies over time.
        Write a short article about the input (formatted in markdown). Attempt to answer the following questions:
        - Has sentiment improved over time?
        - Does management follow through on their strategy commitments?
        - Does management react if their strategies do not yield results?
    """,

    "Multi 10-K Summary Analysis 4": """
        Analyze these reports about {company_name}. Consider each report in order.

        Summarize the change in general sentiment, stated challenges & risks, and mitigation strategies over time.

        Write a short post about the company. Attempt to answer:
            - Did the company follow through on their strategy commitments?
            - Did management react if their strategies did not yield results?
    """,
    "Multi 10-K Summary Analysis 5": """
        Analyze these reports about {company_name}. Consider each report in order.

        Consider how the general sentiment, stated challenges & risks, mitigation strategies, and overall performance have changed over time.

        Summarize the changes in two to three paragraphs.
    """,
    "Multi 10-K Summary Analysis 6": """
        The user's input provides historical context about {company_name}. Write a short, blog style essay about the company.
    """,
    "Multi 10-K Summary Analysis 7": """
        You are an writer at a financial magazine, working on an expose of {company_name}. You will be given some research about the company, and need to analyze it for trends. Write an article explaining your analysis of the research.
        """,
}

ollama_client = ollama.Client(host=f"http://{OLLAMA_HOST}")
set_identity(EDGAR_CONTACT)

def estimate_tokens(text):
    return len(text) // 4 # Rough estimation: ~4 chars per token in English text

def model_context_window(model):
    model_info = ollama.show(model)
    # fixme - this retrieval is not right. Set default to match my 54k context window
    context_window = model_info.get('llama.context_length', 43008)
    return context_window


def ollama_summarize(model, system_prompt, content, temperature):
    input_tokens = estimate_tokens(system_prompt + content)
    context_window = model_context_window(model)

    if input_tokens > context_window:
        print(f"WARNING token input ({input_tokens}) is larger than the context window {context_window}")
        # return progressive_refinement(model, context_window, system_prompt, content)

    start = time.time()
    response = ollama_client.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Always use integers(1.) in headings as opposed to roman numerals (I.). Always use Markdown Headers (#, ##, ...) to denote sections instead of bold text (**)"
            },
            {
                "role": "assistant",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content
            },
        ],
        options={"temperature": temperature}
    )
    duration = time.time() - start
    summary = response.message['content']
    output_tokens = estimate_tokens(summary)
    tokens_per_second = output_tokens / duration
    print(
        f"{input_tokens} tokens in, {output_tokens} tokens out in {duration:.2f} seconds ({tokens_per_second:.2f} tokens/second)"
    )
    return summary

def filter_summary(summary):
    # Remove the first line of the summary
    lines = summary.split('\n')
    if lines:
        lines = lines[1:]

    # Find the last line containing '---'
    last_separator_index = None
    for i in range(len(lines) - 1, -1, -1):
        if '---' in lines[i]:
            last_separator_index = i
            break

    # Remove that line and any lines thereafter
    if last_separator_index is not None:
        lines = lines[:last_separator_index]

    # Join the remaining lines and return
    return '\n'.join(lines)

def generate_management_discussion_summary(model, company, date="2020-01-01:"):
    ticker = company.tickers[0]
    output_dir = f"summaries/{ticker}"
    os.makedirs(output_dir, exist_ok=True)

    filings = company.get_filings(date=date, form="10-K")
    if filings == None:
        print(f"WARN: No filings found for {company.name}")
        return
    num_filings = len(filings)

    print(f"Summarizing {num_filings} 10-Ks for {company.name}")
    summaries = {}

    for f in filings:
        tenk = f.data_object()

        if not tenk.management_discussion:
            print(f"INFO: {ticker} {f.filing_date} has no management discussion")
            continue

        s = {
            "company_name": company.name,
            "filing_date": f.filing_date,
            "fiscal_year": datetime.strptime(f.period_of_report, "%Y-%m-%d").year,
            "url": f.filing_url,
        }
        system_prompt = SYSTEM_PROMPTS["10-k Section 7 Summarize 4"].format(**s)

        summary = ollama_summarize(
            model,
            system_prompt,
            tenk.management_discussion,
            0.0
        )

        summary = filter_summary(summary)

        heading = "{company_name} {fiscal_year} 10-K Section 7 (Management’s Discussion and Analysis)\n\n"
        citation = "\n\nsource: {url}"
        summary = (heading + summary + citation).format(**s)

        file_path = os.path.join(output_dir, f"{f.filing_date}-MDA-Summary.md")
        with open(file_path, "w") as file:
            file.write(summary)

        summaries[f.filing_date] = summary

def generate_meta_analysis(model, company, temperature):
    system_prompt_name = "Multi 10-K Summary Analysis 7"
    ticker = company.tickers[0]
    working_dir = f"summaries/{ticker}"
    # Initialize an empty list to store the file contents
    summaries_list = []

    # Loop through the *.md files in working_dir
    for file_name in sorted(os.listdir(working_dir)):
        if file_name.endswith('.md'):
            with open(os.path.join(working_dir, file_name), 'r') as file:
                summaries_list.append(file.read())

    print(f"Found {len(summaries_list)} Summaries for {company.name}")
    # Join the strings together with the separator
    summaries = "\n\n-----\n\n".join(summaries_list)
    # print(summaries)
    # return

    # Define variables needed for the next steps
    s = {"company_name": company.name}
    num_filings = len(summaries_list)
    output_dir = working_dir

    system_prompt = SYSTEM_PROMPTS[system_prompt_name].format(**s)

    meta_analysis = ollama_summarize(model, system_prompt, summaries, temperature)
    meta_analysis = filter_summary(meta_analysis)

    file_path = os.path.join(output_dir, f"{ticker} {system_prompt_name} @ ({temperature})")
    with open(file_path, "w") as file:
        file.write(meta_analysis)


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
        generate_management_discussion_summary(args.model, company, date=args.date)
        for temperature in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]:
            generate_meta_analysis(args.model, company, temperature)


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

# def chunk_document(text, token_count, overlap):
#     chunk_size = int((token_count * 4) * 0.8) # convert from tokens to char estimate, then leave a buffer
#     print(f"Chunk size: {chunk_size}")
#     chunks = []
#     start = 0
#     while start < len(text):
#         end = min(start + chunk_size, len(text))
#         print(f"{start} {end} {len(text)}")
#         if end < len(text):
#             end = text.rfind('. ', start, end) + 1
#         chunks.append(text[start:end])
#         start = end if end == len(text) else end - overlap
#     return chunks
#
# def progressive_refinement(model, context_window, system_prompt, content):
#     token_estimate = estimate_tokens(content)
#     chunk_size = context_window - estimate_tokens(system_prompt)
#     chunks = chunk_document(content, chunk_size, 200)
#     print(f"Progressive refinement. {model} {context_window}, using {len(chunks)} chunks of {chunk_size} to analyze {token_estimate} tokens of content")
#     refinement_prefix = "\n\nUpdate and extend this summary with new information from the provided chunk."
#     current_summary = ""
#     for i, chunk in enumerate(chunks):
#         if i == 0:
#             response = ollama.chat(
#                 model=model,
#                 messages=[
#                     {
#                         "role": "system", "content": system_prompt,
#                     },
#                     {
#                         "role": "user", "content": chunk,
#                     }
#                 ]
#             )
#             current_summary = response.message['content']
#         else:
#             response = ollama.chat(
#                 model=model,
#                 messages=[
#                     {
#                         "role": "system", "content": system_prompt + refinement_prefix,
#                     },
#                     {
#                         "role": "user", "content": f"Summary:\n{current_summary}\n\nNew information to consider:\n{chunk}",
#                     }
#                 ]
#             )
#             current_summary = response.message['content']
#     return current_summary