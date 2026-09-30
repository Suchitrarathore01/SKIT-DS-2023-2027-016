import logging

from fastapi import APIRouter
from app.schemas.scan import ScanRequest, ScanResponse
from app.services.url_processor import process_url
from app.services.security_checker import (
    check_url_security,
    calculate_risk_level
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/scan", response_model=ScanResponse)
def scan_url(request: ScanRequest):
    logger.info("Scan request received")

    try:
        url = str(request.url)

        # Process URL
        processed_url = process_url(url)

        # Security checks
        security_result = check_url_security(url)

        # Calculate risk level
        risk_level = calculate_risk_level(
            security_result["findings"]
        )

        return {
            "url": url,
            "status": "processed",
            "message": "URL processed successfully",
            "protocol": processed_url["protocol"],
            "domain": processed_url["domain"],
            "path": processed_url["path"],
            "https": security_result["https"],
            "uses_ip": security_result["uses_ip"],
            "risk_level": risk_level,
            "findings": security_result["findings"]
        }

    except Exception:
        logger.exception("Error while processing URL")

        return {
            "url": str(request.url),
            "status": "error",
            "message": "An error occurred while processing the URL",
            "protocol": "",
            "domain": "",
            "path": "",
            "https": False,
            "uses_ip": False,
            "risk_level": "UNKNOWN",
            "findings": []
        }