import json

from sqlalchemy.orm import Session

from app.database.models import Scan


def save_scan(db: Session, result: dict):

    scan = Scan(
        url=result["url"],
        status=result["status"],
        message=result["message"],
        protocol=result["protocol"],
        domain=result["domain"],
        path=result["path"],
        https=result["https"],
        uses_ip=result["uses_ip"],
        risk_level=result["risk_level"],
        findings=json.dumps(result["findings"])
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    return scan


def get_scans(db: Session):

    scans = db.query(Scan).all()

    results = []

    for scan in scans:

        results.append({
            "id": scan.id,
            "url": scan.url,
            "status": scan.status,
            "message": scan.message,
            "protocol": scan.protocol,
            "domain": scan.domain,
            "path": scan.path,
            "https": scan.https,
            "uses_ip": scan.uses_ip,
            "risk_level": scan.risk_level,
            "findings": json.loads(scan.findings)
        })

    return results