from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database.database import Base


class Scan(Base):

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)

    url = Column(String)
    status = Column(String)
    message = Column(String)

    protocol = Column(String)
    domain = Column(String)
    path = Column(String)

    https = Column(Boolean)
    uses_ip = Column(Boolean)

    risk_level = Column(String)

    findings = Column(Text)