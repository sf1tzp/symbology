#!/usr/bin/env python3
"""
Refactored Analysis Pipeline CLI Script

This script processes all companies in the database through the complete pipeline:
1. Process document completions
2. Create aggregates
3. Generate company summary
4. Generate individual aggregate summaries
5. Display summary report
"""

import argparse
import sys
from typing import Dict, List, Any

# Import the refactored modules
from src.database.base import init_db
from src.database.companies import get_all_company_tickers
from src.llm.client import init_client
from src.llm.completions import (
    process_company_document_completions,
    get_completion_results_by_type,
)
from src.llm.aggregations import (
    process_all_aggregates,
    generate_company_summary,
    generate_aggregate_summaries,
    verify_company_summary,
    get_aggregates_summary_report
)
from src.database.documents import DocumentType
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger


def get_default_tickers() -> List[str]:
    """Get the default list of tickers to process."""
    return ['AGNC']

def process_company(ticker: str, client, doc_model: str, aggregate_model: str, logger) -> Dict[str, Any]:
    """Process a single company through the complete pipeline."""
    print(f"\n📄 Step 1: Processing document completions for {ticker}...")
    OUTPUT_DIR = f"outputs/{ticker}"

    completion_ids_by_type = process_company_document_completions(
        client=client,
        ticker=ticker,
        model=doc_model,
        output_dir=OUTPUT_DIR
    )
    print(f"✅ Completion IDs by type: {completion_ids_by_type}")

    # Step 2: Load Completion Data and Process Aggregates
    print(f"\n🔄 Step 2: Loading completion data and processing aggregates for {ticker}...")
    completion_data_by_type = {
        "mda": get_completion_results_by_type(ticker, DocumentType.MDA),
        "risk_factors": get_completion_results_by_type(ticker, DocumentType.RISK_FACTORS),
        "description": get_completion_results_by_type(ticker, DocumentType.DESCRIPTION)
    }

    aggregates = process_all_aggregates(
        client=client,
        ticker=ticker,
        completion_ids_by_type=completion_ids_by_type,
        completion_data_by_type=completion_data_by_type,
        model=aggregate_model,
        output_dir=OUTPUT_DIR
    )
    print(f"✅ Created aggregates: {list(aggregates.keys())}")

    # Step 3: Generate Individual Aggregate Summaries

    print(f"\n📊 Step 3: Generating aggregate summaries for {ticker}...")
    summary_results = generate_aggregate_summaries(
        client=client,
        ticker=ticker,
        model=aggregate_model
    )

    successful_summaries = sum(summary_results.values())
    total_aggregates = len(summary_results)
    print(f"✅ Generated summaries for {successful_summaries}/{total_aggregates} aggregates")

    # Step 4: Generate Company Summary
    print(f"\n📋 Step 4: Generating company summary for {ticker}...")
    company_summary = generate_company_summary(
        client=client,
        ticker=ticker,
        model=aggregate_model
    )

    if company_summary:
        print(f"✅ Company summary generated ({len(company_summary)} characters)")
        success, preview = verify_company_summary(ticker)
        if success:
            print("✅ Summary verification successful")
        else:
            print("❌ Summary verification failed")
    else:
        print("❌ Failed to generate company summary")


    # Step 5: Generate Summary Report
    print(f"\n📋 Step 5: Generating summary report for {ticker}...")
    report = get_aggregates_summary_report(ticker)

    return {
        'completion_ids': completion_ids_by_type,
        'aggregates': list(aggregates.keys()),
        'has_company_summary': bool(company_summary),
        'aggregate_summaries': f"{successful_summaries}/{total_aggregates}",
        'report': report
    }


def display_results_summary(results_summary: Dict[str, Dict], failed_tickers: List[str]):
    """Display detailed results summary."""
    print("\n📊 DETAILED RESULTS SUMMARY")
    print(f"{'='*80}")

    for ticker, results in results_summary.items():
        print(f"\n🏢 {ticker}:")
        print(f"  Completions: {results['completion_ids']}")
        print(f"  Aggregates: {results['aggregates']}")
        print(f"  Company Summary: {'✅' if results['has_company_summary'] else '❌'}")
        print(f"  Aggregate Summaries: {results['aggregate_summaries']}")

        # Show report details
        if results['report']:
            for doc_type, info in results['report'].items():
                print(f"    {doc_type.upper()}: {info['content_length']} chars, Summary: {'✅' if info['has_summary'] else '❌'}")

    if failed_tickers:
        print(f"\n❌ FAILED TICKERS: {failed_tickers}")


def main():
    """Main function to run the refactored analysis pipeline."""
    parser = argparse.ArgumentParser(description="Run the refactored analysis pipeline")
    parser.add_argument(
        "--doc-model",
        default="qwen3:4b",
        help="Model to use for document processing (default: qwen3:4b)"
    )
    parser.add_argument(
        "--aggregate-model",
        default="qwen3:14b",
        help="Model to use for aggregation processing (default: qwen3:14b)"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Specific tickers to process (default: process all default tickers)"
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Get tickers from database instead of using default list"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Initialize components
    configure_logging()
    logger = get_logger(name="refactored_pipeline_cli")

    try:
        _, _ = init_db(settings.database.url)
        client = init_client(settings.openai_api.url)
        _ = client.ps()
        logger.info("System initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        sys.exit(1)

    # Determine which tickers to process
    if args.tickers:
        tickers = args.tickers
        print(f"Processing specified tickers: {tickers}")
    elif args.from_db:
        tickers = get_all_company_tickers()
        if not tickers:
            print("No tickers found in database. Please ingest some companies first.")
            sys.exit(1)
        print(f"Found {len(tickers)} tickers in database: {tickers[:10]}{'...' if len(tickers) > 10 else ''}")
    else:
        tickers = get_default_tickers()
        print(f"Processing default tickers: {len(tickers)} companies")

    # Process all companies
    results_summary = {}
    failed_tickers = []

    for i, ticker in enumerate(tickers, 1):
        print(f"\n{'='*60}")
        print(f"Processing {i}/{len(tickers)}: {ticker}")
        print(f"{'='*60}")

        try:
            results = process_company(
                ticker=ticker,
                client=client,
                doc_model=args.doc_model,
                aggregate_model=args.aggregate_model,
                logger=logger
            )
            results_summary[ticker] = results
            print(f"\n🎉 Successfully completed processing for {ticker}!")

        except Exception as e:
            print(f"\n❌ Error processing {ticker}: {str(e)}")
            logger.error(f"Failed to process ticker {ticker}", error=str(e), exc_info=True)
            failed_tickers.append(ticker)
            continue

    # Final summary
    print("\n\n🏁 PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Successfully processed: {len(results_summary)} companies")
    print(f"Failed: {len(failed_tickers)} companies")
    if failed_tickers:
        print(f"Failed tickers: {failed_tickers}")

    # Display detailed results
    display_results_summary(results_summary, failed_tickers)

    # Exit with appropriate code
    sys.exit(0 if not failed_tickers else 1)


if __name__ == "__main__":
    main()
