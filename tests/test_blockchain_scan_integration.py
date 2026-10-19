from unittest.mock import patch

from app.routes.scan import scan_url
from app.schemas.scan import ScanRequest


def test_blockchain_threat_adds_finding():
    request = ScanRequest(url="https://example.com")

    blockchain_result = {
        "available": True,
        "found": True,
        "verdict": 1,
        "threat_type": 1,
        "confidence": 90,
        "error": None,
    }

    with patch(
        "app.routes.scan.check_blockchain_threat",
        return_value=blockchain_result,
    ), patch("app.routes.scan.save_scan") as mock_save:

        response = scan_url(request, db=None)

    assert response["blockchain_available"] is True
    assert response["blockchain_found"] is True
    assert any(
        "Blockchain registry identifies this URL as a threat" in finding
        for finding in response["findings"]
    )
    assert response["risk_level"] == "MEDIUM"

    mock_save.assert_called_once()


def test_blockchain_unavailable_does_not_break_scan():
    request = ScanRequest(url="https://example.com")

    blockchain_result = {
        "available": False,
        "found": False,
        "verdict": None,
        "threat_type": None,
        "confidence": None,
        "error": "Blockchain lookup failed",
    }

    with patch(
        "app.routes.scan.check_blockchain_threat",
        return_value=blockchain_result,
    ), patch("app.routes.scan.save_scan") as mock_save:

        response = scan_url(request, db=None)

    assert response["status"] == "processed"
    assert response["blockchain_available"] is False
    assert response["blockchain_found"] is False

    mock_save.assert_called_once()

def test_unexpected_blockchain_exception_does_not_break_scan():
    request = ScanRequest(url="https://example.com")

    with patch(
        "app.routes.scan.check_blockchain_threat",
        side_effect=RuntimeError("Unexpected RPC failure"),
    ), patch("app.routes.scan.save_scan") as mock_save:
        response = scan_url(request, db=None)

    assert response["status"] == "processed"
    assert response["blockchain_available"] is False
    assert response["blockchain_found"] is False
    mock_save.assert_called_once()
