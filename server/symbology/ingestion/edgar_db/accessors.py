from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

from edgar import Filing, set_identity
from symbology.database.documents import DocumentType

# from edgar.xbrl import XBRL
# import pandas as pd
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

def edgar_login(edgar_contact: str) -> None:
    """
    Set the identity for accessing EDGAR database.

    The SEC EDGAR system requires a valid email contact for API access.

    Args:
        edgar_contact: Email address to identify requests to SEC
    """
    set_identity(edgar_contact)


class FormSection(Enum):
    """Enumeration of standardized form sections across different filing types."""
    BUSINESS_DESCRIPTION = "business_description"
    RISK_FACTORS = "risk_factors"
    MANAGEMENT_DISCUSSION = "management_discussion"
    CONTROLS_PROCEDURES = "controls_procedures" # "Evaluation of the effectiveness of the design and operation of the company’s disclosure controls and procedur
    LEGAL_PROCEEDINGS = "legal_proceedings"
    MARKET_RISK = "market_risk"
    EXECUTIVE_COMPENSATION = "executive_compensation"
    DIRECTORS_OFFICERS = "directors_officers"


class SectionAccessor:
    """Defines how to access a section from a filing object."""

    def __init__(self, property_name: Optional[str] = None, item_key: Optional[str] = None,
                 part: Optional[str] = None, fallback_fn: Optional[Callable] = None):
        """
        Initialize section accessor.

        Args:
            property_name: Direct property on the filing object (e.g., 'business')
            item_key: Item key for section access (e.g., 'Item 1')
            part: Part identifier (e.g., 'PART I')
            fallback_fn: Fallback function to extract content
        """
        self.property_name = property_name
        self.item_key = item_key
        self.part = part
        self.fallback_fn = fallback_fn

    def extract(self, filing: Filing) -> Optional[str]:
        """Extract content using the defined access method."""
        filing_obj = filing.obj()

        logger.debug("start_extract_section")
        # Try direct property access first
        if self.property_name and hasattr(filing_obj, self.property_name):
            content = getattr(filing_obj, self.property_name)
            if content:
                return content

        logger.debug("attempt_section_lookup_by_item")
        # Try item/part access if available
        if self.item_key:
            try:
                if self.part:
                    logger.debug("attempt_section_lookup_by_part")
                    content = filing_obj.get_item_with_part(self.part, self.item_key)
                else:
                    content = filing_obj[self.item_key]

                if content:
                    return content
            except (AttributeError, KeyError):
                logger.error("section_extraction_error")
                pass

        # Try fallback function
        logger.warn("no_section_found")

        return None


# Form section mappings - defines how to access sections across different form types
FORM_SECTION_MAPPINGS: Dict[str, Dict[FormSection, SectionAccessor]] = {
    "10-K": {
        FormSection.BUSINESS_DESCRIPTION: SectionAccessor(
            property_name="business",
            item_key="Item 1",
            part="PART I"
        ),
        FormSection.RISK_FACTORS: SectionAccessor(
            property_name="risk_factors",
            item_key="Item 1A",
            part="PART I"
        ),
        FormSection.MANAGEMENT_DISCUSSION: SectionAccessor(
            property_name="management_discussion",
            item_key="Item 7",
            part="PART II"
        ),
        FormSection.CONTROLS_PROCEDURES: SectionAccessor(
            item_key="Item 9A",
            part="PART II"
        ),
        FormSection.LEGAL_PROCEEDINGS: SectionAccessor(
            item_key="Item 3",
            part="PART I"
        ),
        FormSection.MARKET_RISK: SectionAccessor(
            item_key="Item 7A",
            part="PART II"
        ),
        FormSection.EXECUTIVE_COMPENSATION: SectionAccessor(
            item_key="Item 11",
            part="PART III"
        ),
        FormSection.DIRECTORS_OFFICERS: SectionAccessor(
            property_name="directors_officers_and_governance",
            item_key="Item 10",
            part="PART III"
        ),
    },
    "10-K/A": {
        # Same as 10-K for amended filings
        FormSection.BUSINESS_DESCRIPTION: SectionAccessor(
            property_name="business",
            item_key="Item 1",
            part="PART I"
        ),
        FormSection.RISK_FACTORS: SectionAccessor(
            property_name="risk_factors",
            item_key="Item 1A",
            part="PART I"
        ),
        FormSection.MANAGEMENT_DISCUSSION: SectionAccessor(
            property_name="management_discussion",
            item_key="Item 7",
            part="PART II"
        ),
        FormSection.CONTROLS_PROCEDURES: SectionAccessor(
            item_key="Item 9A",
            part="PART II"
        ),
        FormSection.LEGAL_PROCEEDINGS: SectionAccessor(
            item_key="Item 3",
            part="PART I"
        ),
        FormSection.MARKET_RISK: SectionAccessor(
            item_key="Item 7A",
            part="PART II"
        ),
        FormSection.EXECUTIVE_COMPENSATION: SectionAccessor(
            item_key="Item 11",
            part="PART III"
        ),
        FormSection.DIRECTORS_OFFICERS: SectionAccessor(
            property_name="directors_officers_and_governance",
            item_key="Item 10",
            part="PART III"
        ),
    },
    "10-Q": {
        FormSection.MANAGEMENT_DISCUSSION: SectionAccessor(
            item_key="Item 2",
            part="PART I"
        ),
        FormSection.MARKET_RISK: SectionAccessor(
            item_key="Item 3",
            part="PART I"
        ),
        FormSection.CONTROLS_PROCEDURES: SectionAccessor(
            item_key="Item 4",
            part="PART I"
        ),
        FormSection.LEGAL_PROCEEDINGS: SectionAccessor(
            item_key="Item 1",
            part="PART II"
        ),
        FormSection.RISK_FACTORS: SectionAccessor(
            item_key="Item 1A",
            part="PART II"
        ),
    },
    "10-Q/A": {
        # Same as 10-Q for amended filings
        FormSection.MANAGEMENT_DISCUSSION: SectionAccessor(
            item_key="Item 2",
            part="PART I"
        ),
        FormSection.MARKET_RISK: SectionAccessor(
            item_key="Item 3",
            part="PART I"
        ),
        FormSection.CONTROLS_PROCEDURES: SectionAccessor(
            item_key="Item 4",
            part="PART I"
        ),
        FormSection.LEGAL_PROCEEDINGS: SectionAccessor(
            item_key="Item 1",
            part="PART II"
        ),
        FormSection.RISK_FACTORS: SectionAccessor(
            item_key="Item 1A",
            part="PART II"
        ),
    },
}

# Mapping from FormSection to DocumentType for consistency
SECTION_TO_DOCUMENT_TYPE: Dict[FormSection, DocumentType] = {
    FormSection.BUSINESS_DESCRIPTION: DocumentType.DESCRIPTION,
    FormSection.RISK_FACTORS: DocumentType.RISK_FACTORS,
    FormSection.MANAGEMENT_DISCUSSION: DocumentType.MDA,
    FormSection.CONTROLS_PROCEDURES: DocumentType.CONTROLS_PROCEDURES,
    FormSection.LEGAL_PROCEEDINGS: DocumentType.LEGAL_PROCEEDINGS,
    FormSection.MARKET_RISK: DocumentType.MARKET_RISK,
    FormSection.EXECUTIVE_COMPENSATION: DocumentType.EXECUTIVE_COMPENSATION,
    FormSection.DIRECTORS_OFFICERS: DocumentType.DIRECTORS_OFFICERS,
}


def get_form_section(filing: Filing, section: FormSection) -> Optional[str]:
    """
    Extract a standardized section from any supported filing type.

    Args:
        filing: A Filing object from the edgar package
        section: The standardized section to extract

    Returns:
        The section content as a string or None if not found/supported
    """
    form_type = filing.form

    logger.debug("get_form_section", section=section)

    # Get the mapping for this form type
    form_mapping = FORM_SECTION_MAPPINGS.get(form_type)
    if not form_mapping:
        logger.warn("no_section_found")
        return None

    # Get the accessor for this section
    accessor = form_mapping.get(section)
    if not accessor:
        logger.warn("no_accessor_found")
        return None

    return accessor.extract(filing)


def get_available_sections(filing: Filing) -> List[FormSection]:
    """
    Get list of sections available for a given filing type.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        List of FormSection enums available for this filing type
    """
    form_type = filing.form
    form_mapping = FORM_SECTION_MAPPINGS.get(form_type, {})
    return list(form_mapping.keys())


# def _process_xbrl_dataframe(df: pd.DataFrame, filing: Filing, columns_to_drop: Optional[List[str]] = None) -> pd.DataFrame:
#     """
#     Process XBRL dataframe by filtering rows and columns based on common criteria.

#     Args:
#         df: DataFrame from XBRL statement
#         filing: Filing object to extract year information
#         columns_to_drop: List of columns to exclude from the result

#     Returns:
#         Processed DataFrame
#     """
#     if columns_to_drop is None:
#         columns_to_drop = ['level', 'has_values', 'is_abstract', 'original_label', 'abstract', 'dimension']

#     # Apply filters for existing columns
#     mask = True  # Start with all rows selected
#     if 'is_abstract' in df.columns:
#         mask = mask & (~df['is_abstract'])
#     if 'has_values' in df.columns:
#         mask = mask & df['has_values']

#     # Apply the filter mask only if we've actually set conditions
#     if not isinstance(mask, bool):
#         df = df.loc[mask]

#     # Drop specified columns if they exist
#     df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

#     # Filter columns based on year
#     fiscal_date = filing.period_of_report

#     # Build a list of columns to keep
#     filtered_columns: List[str] = []
#     for col in df.columns:
#         try:
#             # Try to parse as a date and match by year
#             _ = datetime.strptime(col, '%Y-%m-%d')
#             if col == fiscal_date:
#                 filtered_columns.append(col)
#         except ValueError:
#             # Keep non-date columns (metadata)
#             filtered_columns.append(col)

#     df = df[filtered_columns]

#     # Remove rows where 'year' column is blank (NaN or empty string)
#     if fiscal_date in df.columns:
#         df = df[df[fiscal_date].notna() & (df[fiscal_date] != '')]

#     return df

# def get_balance_sheet_values(filing: Filing) -> pd.DataFrame:
#     """
#     Extract balance sheet values from a filing.

#     Args:
#         filing: Filing object from edgar package

#     Returns:
#         DataFrame containing balance sheet data for the filing's year
#     """
#     xbrl = XBRL.from_filing(filing)
#     df = xbrl.statements.balance_sheet().to_dataframe()
#     return _process_xbrl_dataframe(df, filing)

# def get_income_statement_values(filing: Filing) -> pd.DataFrame:
#     """
#     Extract income statement values from a filing.

#     Args:
#         filing: Filing object from edgar package

#     Returns:
#         DataFrame containing income statement data for the filing's year
#     """
#     xbrl = XBRL.from_filing(filing)
#     df = xbrl.statements.income_statement().to_dataframe()
#     # Income statement uses slightly different columns to drop
#     return _process_xbrl_dataframe(df, filing, columns_to_drop=['level', 'abstract', 'dimension'])

# def get_cash_flow_statement_values(filing: Filing) -> pd.DataFrame:
#     """
#     Extract cash flow statement values from a filing.

#     The cash flow statement shows how changes in balance sheet accounts and
#     income affect cash and cash equivalents, categorized by operating, investing,
#     and financing activities.

#     Args:
#         filing: Filing object from edgar package

#     Returns:
#         DataFrame containing cash flow data for the filing's year
#     """
#     xbrl = XBRL.from_filing(filing)
#     df = xbrl.statements.cash_flow_statement().to_dataframe()
#     # Cash flow statement uses slightly different columns to drop
#     return _process_xbrl_dataframe(df, filing, columns_to_drop=['level', 'abstract', 'dimension'])

# def get_cover_page_values(filing: Filing) -> pd.DataFrame:
#     """
#     Extract cover page information from a filing.

#     The cover page contains summary information about the filing and company,
#     such as the company name, fiscal year end, filing date, and other
#     identifying information.

#     Args:
#         filing: Filing object from edgar package

#     Returns:
#         DataFrame containing cover page data for the filing
#     """
#     xbrl = XBRL.from_filing(filing)
#     df = xbrl.statements["CoverPage"].to_dataframe()

#     # Remove level, abstract, dimension columns
#     columns_to_drop = ['level', 'abstract', 'dimension']
#     df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

#     # Identify the date column (typically the last column)
#     date_columns = [col for col in df.columns if col not in ['concept', 'label']]

#     if date_columns:
#         # Rename the date column to filing.period_of_report
#         df = df.rename(columns={date_columns[0]: filing.period_of_report})

#         # Remove rows where the date column is empty or NA
#         df = df[df[filing.period_of_report].notna() & (df[filing.period_of_report] != '')]

#     return df

def get_business_description(filing: Filing) -> Optional[str]:
    """
    Extract the business description section from a filing.

    This function now uses the standardized form section mapping system
    and works across different filing types (10-K, 10-Q, etc.).

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The business description text as a string or None if not found
    """
    return get_form_section(filing, FormSection.BUSINESS_DESCRIPTION)


def get_risk_factors(filing: Filing) -> Optional[str]:
    """
    Extract the risk factors section from a filing.

    Risk factors typically discuss significant risks that could adversely affect
    the company's business, financial condition, or future results.

    This function now uses the standardized form section mapping system
    and works across different filing types (10-K, 10-Q, etc.).

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The risk factors text as a string or None if not found
    """
    return get_form_section(filing, FormSection.RISK_FACTORS)


def get_management_discussion(filing: Filing) -> Optional[str]:
    """
    Extract the management's discussion and analysis (MD&A) section from a filing.

    MD&A provides information about the company's financial condition,
    changes in financial condition, and results of operations from management's perspective.

    This function now uses the standardized form section mapping system
    and works across different filing types (10-K, 10-Q, etc.).

    Args:
        filing: A Filing object from the edgar package

    Returns:
        The MD&A text as a string or None if not found
    """
    return get_form_section(filing, FormSection.MANAGEMENT_DISCUSSION)

def _year_from_period_of_report(filing: Filing) -> int:
    """
    Extract the calendar year from a filing's period of report date.

    Args:
        filing: A Filing object containing period_of_report date in 'YYYY-MM-DD' format

    Returns:
        The year as an integer
    """
    date = datetime.strptime(filing.period_of_report, '%Y-%m-%d')
    return date.year


def get_all_available_sections(filing: Filing) -> Dict[FormSection, Optional[str]]:
    """
    Extract all available sections from a filing.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        Dictionary mapping FormSection to extracted content (None if not available)
    """
    result = {}
    available_sections = get_available_sections(filing)

    for section in available_sections:
        result[section] = get_form_section(filing, section)

    return result


def get_sections_for_document_types(filing: Filing) -> Dict[DocumentType, Optional[str]]:
    """
    Extract sections that map to our DocumentType enum for database storage.

    Args:
        filing: A Filing object from the edgar package

    Returns:
        Dictionary mapping DocumentType to extracted content (None if not available)
    """
    result = {}

    for section, doc_type in SECTION_TO_DOCUMENT_TYPE.items():
        content = get_form_section(filing, section)
        if content:
            result[doc_type] = content

    return result


# TODO: Look for other documents,
#   - letter from CEO
#   - auditors notes
