from sqlalchemy import Boolean, Column, Integer, JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    cik = Column(Integer, index=True, unique=True)
    name = Column(String(255), nullable=False)
    tickers = Column(JSON)  # List of ticker symbols
    exchanges = Column(JSON)  # List of exchanges
    sic = Column(String(10))
    sic_description = Column(String(255))
    category = Column(String(100))
    fiscal_year_end = Column(String(4))
    entity_type = Column(String(50))
    phone = Column(String(20))
    flags = Column(String(100))
    business_address = Column(Text)
    mailing_address = Column(Text)
    insider_transaction_for_owner_exists = Column(Boolean, default=False)
    insider_transaction_for_issuer_exists = Column(Boolean, default=False)
    ein = Column(String(20))
    description = Column(Text)
    website = Column(String(255))
    investor_website = Column(String(255))
    state_of_incorporation = Column(String(2))
    state_of_incorporation_description = Column(String(50))
    former_names = Column(JSON)  # List of former company names

    def __repr__(self):
        return f"<Company(name='{self.name}', cik={self.cik}, tickers={self.tickers})>"

    def to_dict(self):
        """Convert Company object to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def to_json(self):
        """Convert Company object to JSON string"""
        import json

        return json.dumps(self.to_dict(), default=str)
