import os
import edgar

from returns.result import Result, Success as Ok, Failure as Err
from returns.pipeline import is_successful as is_ok


def edgar_login() -> Result[str, str]:
    contact = os.getenv("EDGAR_CONTACT")
    if not contact:
        return Err("No EDGAR contact email address provided")

    edgar.set_identity(contact)
    return Ok("")


# income statement
income_deets = {
    "revenue": {
        "concept": "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
        "level": 0,
    },
    "cost_of_revenue": {"concept": "us-gaap_CostOfGoodsAndServicesSold", "level": 0},
    "operating_income": {"concept": "us-gaap_OperatingIncomeLoss", "level": 0},
    "net_income": {"concept": "us-gaap_NetIncomeLoss", "level": 0},
    "interest_expense": {"concept": "us-gaap_NonoperatingIncomeExpense", "level": 0},
}


# balance sheet
balance_deets = {
    "cash": {"concept": "", "level": 0},
    "short_term_investments": {"concept": "", "level": 0},
    "accounts_receivable": {"concept": "", "level": 0},
    "current_assets": {"concept": "", "level": 0},
    "current_liabilities": {"concept": "", "level": 0},
    "total_assets": {"concept": "", "level": 0},
    "total_liabilities": {"concept": "", "level": 0},
    "total_shareholder_equity": {"concept": "", "level": 0},
    # # compare last year to current year's total
    # - average_total_assets = (ta1 + ta2) / 2
    # - average_shareholder_equity = (ts1 + ts2) / 2
    "inventory": {"concept": "", "level": 0},
}


# Financials Cover Sheet
cover_sheet = {
    "shares_outstanding": {"concept": "", "level": 0},
}


# Profitability Ratios
# High margins indicate a more profitable and efficient business
def gross_profit_margin(revenue, cost_of_revenue):
    return (revenue - cost_of_revenue) / revenue


def operating_profit_margin(operating_income, revenue):
    return operating_income / revenue


def net_profit_margin(net_income, revenue):
    return net_income / revenue


def return_on_assets(net_income, average_total_assets):
    return net_income / average_total_assets


def return_on_equity(net_income, average_sharehold_equity):
    return net_income / average_sharehold_equity


# Liquidity Ratios
# Higher ratios suggest that a company has enough liquidity to cover its near-term liabilities
def current_liquidity_ratio(current_assets, current_liabilities):
    return current_assets / current_liabilities


def quick_liquidity_ratio(
    cash, short_term_investments, accounts_receivable, current_liabilities
):
    return (cash + short_term_investments + accounts_receivable) / current_liabilities


# Solvency Ratios
# Measure a company's ability to meet its long term debt obligations
# low debt ratios, and high interest coverage ratios generally indicate
# that a company is more financially stable
def debt_to_equity_ratio(total_liabilities, total_shareholder_equity):
    return total_liabilities / total_shareholder_equity


def debt_to_assets_ratio(total_liabilities, total_assets):
    return total_liabilities / total_assets


def interest_coverage_ratio(operating_income, interest_expense):
    return operating_income / interest_expense


# Efficiency Ratios
# High turnover ratios suggest that the company is using its assets efficiently to generate revenue
def asset_turnover_ratio(revenue, average_total_assets):
    return revenue / average_total_assets


def inventory_turnover_ratio(cost_of_goods_sold, average_inventory):
    return cost_of_goods_sold / average_inventory


def receivables_turnover_ratio(revenue, average_accounts_receivables):
    return revenue / average_accounts_receivables


# Valuation Ratios
# Lower ratios may indicate that a stock is undervalued based on the company's assets and revenue


def price_to_earnings_ratio(market_price_per_share, earnings_per_share):
    return market_price_per_share / earnings_per_share


def price_to_book_ratio(market_price_per_share, total_assets, total_liabilities):
    return market_price_per_share / (total_assets - total_liabilities)


def price_to_sales_ratio(market_price_per_share, revenue_per_share):
    return market_price_per_share / revenue_per_share
