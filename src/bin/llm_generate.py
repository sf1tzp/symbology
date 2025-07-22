# Imports and Config
from collections import defaultdict
import time

from src.database.base import init_db
from src.database.companies import get_company_by_ticker, update_company
from src.database.completions import Completion
from src.database.documents import DocumentType, get_documents_by_filing
from src.database.filings import get_filings_by_company
from src.database.prompts import *
from src.llm.aggregates import create_document_type_aggregate
from src.llm.client import get_generate_response, init_client, ModelConfig, remove_thinking_tags
from src.llm.completions import process_document_completion
from src.utils.config import settings
from src.utils.logging import configure_logging

configure_logging(log_level="INFO")
logger = get_logger(__name__)

init_db(settings.database.url)
session = get_db_session()

client = init_client(settings.openai_api.url)

TICKERS = ['NFLX', 'NU', 'NVDA', 'ORCL', 'PCG', 'PFE', 'PLTR', 'PR', 'QUBT', 'RIG', 'RIOT', 'RKLB', 'RKT', 'RXRX', 'S', 'SMCI', 'SMR', 'SNAP', 'SOFI', 'TSLA', 'UBER', 'UNH', 'VZ', 'WBD', 'WFC', 'WMT', 'XOM']
# prompts and model config
document_prompt = get_prompt('06878708-7a86-76e0-8000-8b1f4e2ed08c')
document_model_config = ModelConfig(
    name="qwen3:4b",
    num_ctx=24567,
    temperature=0.8,
    top_k=45
)
logger.debug("document_prompt",
            content=f"'{document_prompt.content.strip()[:90]}...'",
            model_config=document_model_config,)


# aggregate_prompt = get_prompt("068786e2-1e9e-7eb6-8000-e716f8eb8a3f")
# aggregate_prompt = get_prompt("0687a819-b5cb-73a3-8000-4326f7819960")
aggregate_prompt = get_prompt("0687ab13-8e9b-7d45-8000-e36b40bd5fcd")

risk_aggregate_prompt = get_prompt("0687abe9-4f99-7ca7-8000-77b422a5c1dc")

aggregate_model_config = ModelConfig(
    name="qwen3:14b",
    num_ctx=9000,
    temperature=0.7,
    num_gpu=41
)

# aggregate_model_config = ModelConfig(
#     name="hf.co/unsloth/gemma-3-12b-it-qat-GGUF:latest",
#     num_ctx=10000,
#     temperature=0.0,
# )

markdown_prompt = get_prompt('0687a885-7cc1-7e88-8000-a95d86e69d22')
markdown_model_config = ModelConfig(
    name="hf.co/unsloth/gemma-3-12b-it-qat-GGUF:latest",
    num_ctx=10000,
    temperature=0.0,
)

front_page_prompt = get_prompt('0687a424-1757-743d-8000-01257e133b73')
front_page_model_config = ModelConfig(
    name="hf.co/unsloth/gemma-3-12b-it-qat-GGUF:latest",
    num_ctx=10000,
    temperature=0.8,
)

logger.info("get_completion_for_filing_documents")
for (i, ticker) in enumerate(TICKERS):
    company = get_company_by_ticker(ticker)

    loop_timer = time.time()
    logger.info("company_loop", company=company.name, ticker=company.ticker, index=f"{i}/{len(TICKERS) - 1}")

    filings = get_filings_by_company(company.id)
    if not filings:
        logger.warning("no_filings", company=company.name, ticker=company.ticker)
        continue

    # filings = [filing for filing in filings if filing.period_of_report.year > 2023]

    # store output to make aggregate from
    completions_by_type: defaultdict[DocumentType, List[Completion]] = defaultdict(list)


    for (j, filing) in enumerate(filings):
        logger.info("filing_loop", filing=filing, index=f"{j}/{len(filings) - 1}")
        documents = get_documents_by_filing(filing.id)
        if len(documents) < 1:
            logger.warning("no documents")
            continue

        for (k, document) in enumerate(documents):
            logger.info("document_loop", document=document, index=f"{k}/{len(documents) - 1}")
            result = process_document_completion(document, document_prompt, document_model_config)
            completions_by_type[document.document_type].append(result)

    if len(completions_by_type) == 0:
        logger.warning("no_documents_to_agggregate_by")
        continue

    logger.info("get_aggregates_for_document_types")
    logger.debug("aggregate_prompt", content=f"'{aggregate_prompt.content.strip()[:90]}...'")

    logger.info("get_mda_aggregate")
    mda_aggregate = create_document_type_aggregate(DocumentType.MDA, completions_by_type[DocumentType.MDA], aggregate_prompt, aggregate_model_config)

    logger.info("get_business_description_aggregate")
    description_aggregate = create_document_type_aggregate(DocumentType.DESCRIPTION, completions_by_type[DocumentType.DESCRIPTION], aggregate_prompt, aggregate_model_config)

    # use a different prompt for risk factors
    logger.info("get_risk_factors_aggregate")
    logger.info("risk_aggregate_prompt", content=f"'{risk_aggregate_prompt.content.strip()[:90]}...'")
    risk_aggregate = create_document_type_aggregate(DocumentType.RISK_FACTORS, completions_by_type[DocumentType.RISK_FACTORS], risk_aggregate_prompt, aggregate_model_config)


    # Make the company 'front page summary' text
    # remove <thinking>, format markdown, lint for misclanious wrapper text
    logger.info("formatting_content")
    unformatted_markdown = remove_thinking_tags(description_aggregate.content)
    with open('unformatted_markdown.md', 'w') as f:
        f.write(unformatted_markdown)

    markdown_response = get_generate_response(markdown_model_config, markdown_prompt.content, unformatted_markdown)
    with open('formatted_markdown.md', 'w') as f:
        f.write(markdown_response.response)

    summary_response = get_generate_response(front_page_model_config, front_page_prompt.content, markdown_response.response)
    linted_summary = get_generate_response(markdown_model_config, "We are cleaning up for publication. Remove any introductory 'meta' lines from the provided document.", summary_response.response)
    company = update_company(company.id, {'summary': linted_summary.response})

    logger.info("finished_company", duration=f"{time.time() - loop_timer:.2f}s")
