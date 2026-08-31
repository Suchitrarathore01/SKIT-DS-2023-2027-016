from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class ScanRequest(BaseModel):
    url: HttpUrl


@app.get("/")
def home():
    return {"message": "ChainShield Backend is Running!"}


@app.post("/scan")
def scan_url(request: ScanRequest):
    return {
        "url": request.url,
        "status": "received",
        "message": "URL received successfully"
    }