import logging

from fastapi import APIRouter
from app.schemas.scan import ScanRequest

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/scan")
def scan_url(request: ScanRequest):
    logger.info("Scan request received")

    try:
        return {
            "url": str(request.url),
            "status": "received",
            "message": "URL received successfully"
        }

    except Exception:
        logger.exception("Error while processing URL")

        return {
            "status": "error",
            "message": "An error occurred while processing the URL"
        }