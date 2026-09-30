from urllib.parse import urlparse
import ipaddress


def check_url_security(url: str):
    parsed_url = urlparse(url)

    findings = []

    # 1. HTTPS check
    if parsed_url.scheme != "https":
        findings.append("URL is not using HTTPS")

    # 2. IP address check
    domain = parsed_url.netloc

    try:
        ipaddress.ip_address(domain)
        findings.append("URL uses an IP address instead of a domain name")
    except ValueError:
        pass

    # 3. Suspicious characters
    suspicious_characters = ["@", "%", "\\"]

    for character in suspicious_characters:
        if character in url:
            findings.append(
                f"URL contains suspicious character: {character}"
            )

    # 4. Suspicious keywords
    suspicious_keywords = [
        "login",
        "verify",
        "password",
        "account",
        "update",
        "secure"
    ]

    url_lower = url.lower()

    for keyword in suspicious_keywords:
        if keyword in url_lower:
            findings.append(
                f"URL contains suspicious keyword: {keyword}"
            )

    return {
        "https": parsed_url.scheme == "https",
        "uses_ip": _is_ip_address(domain),
        "findings": findings
    }


def _is_ip_address(domain: str):
    try:
        ipaddress.ip_address(domain)
        return True
    except ValueError:
        return False
def calculate_risk_level(findings: list[str]):
    if len(findings) == 0:
        return "SAFE"
    elif len(findings) <= 2:
        return "MEDIUM"
    else:
        return "HIGH"