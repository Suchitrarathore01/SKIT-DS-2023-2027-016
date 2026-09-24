from pydantic import BaseModel, HttpUrl


class ScanRequest(BaseModel):
    url: HttpUrl