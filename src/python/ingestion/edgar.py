import json

from edgar import Company, set_identity


def edgar_login(edgar_contact):
    set_identity(edgar_contact)

def get_company(ticker):
    return Company(ticker)

def debug(company):
    filtered = { k: v for k, v in company.__dict__.items() if k != "filings" }
    print(json.dumps(filtered, indent=2, default=str))
