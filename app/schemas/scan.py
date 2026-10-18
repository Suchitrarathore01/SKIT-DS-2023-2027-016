from pydantic import BaseModel, HttpUrl


class ScanRequest(BaseModel):

    url: HttpUrl


class ScanResponse(BaseModel):

    url: str
    status: str
    message: str
    protocol: str
    domain: str
    path: str
    https: bool
    uses_ip: bool
    risk_level: str
    findings: list[str]