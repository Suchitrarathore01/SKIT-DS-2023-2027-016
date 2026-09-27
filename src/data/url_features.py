from __future__ import annotations

import re
from urllib.parse import urlparse

import pandas as pd


# Common URL-shortening services.
# This list is intentionally kept small and explicit so it can be
# version-controlled and updated later.
URL_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
    "shorturl.at",
    "s.id",
    "tiny.cc",
    "rb.gy",
    "lnkd.in",
}


SUSPICIOUS_KEYWORDS = {
    "account",
    "activate",
    "authentication",
    "confirm",
    "credential",
    "login",
    "password",
    "payment",
    "recover",
    "secure",
    "signin",
    "update",
    "verify",
    "verification",
}


def _safe_urlparse(url: str):
    """Parse a URL safely after adding a scheme when necessary."""
    value = str(url).strip()

    if not value:
        return None

    parsed = urlparse(value)

    if not parsed.netloc:
        parsed = urlparse(f"http://{value}")

    return parsed


def calculate_url_depth(url: str) -> int:
    """Return the number of non-empty path segments."""
    parsed = _safe_urlparse(url)

    if parsed is None:
        return 0

    return len(
        [
            segment
            for segment in parsed.path.split("/")
            if segment
        ]
    )


def is_url_shortener(url: str) -> int:
    """Identify whether the URL uses a known shortening service."""
    parsed = _safe_urlparse(url)

    if parsed is None:
        return 0

    hostname = (parsed.hostname or "").lower().rstrip(".")

    return int(
        hostname in URL_SHORTENERS
        or any(hostname.endswith(f".{domain}") for domain in URL_SHORTENERS)
    )


def has_suspicious_keyword(url: str) -> int:
    """
    Identify security-sensitive keywords in the URL.

    This is a lexical heuristic, not a phishing verdict.
    """
    value = str(url).lower()

    return int(
        any(
            re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])", value)
            for keyword in SUSPICIOUS_KEYWORDS
        )
    )


def add_engineered_url_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered URL-level features without modifying existing columns."""
    if "URL" not in df.columns:
        raise ValueError("Input dataframe must contain a 'URL' column.")

    result = df.copy()

    result["IsURLShortener"] = result["URL"].map(is_url_shortener)
    result["URLDepth"] = result["URL"].map(calculate_url_depth)
    result["HasSuspiciousKeyword"] = result["URL"].map(has_suspicious_keyword)

    return result


def main() -> None:
    input_path = "data/processed/cleaned_url.csv"
    output_path = "data/processed/featured_url.csv"

    df = pd.read_csv(input_path)

    print(f"Input shape: {df.shape}")

    df = add_engineered_url_features(df)

    print("\nEngineered features:")
    print(
        df[
            [
                "IsURLShortener",
                "URLDepth",
                "HasSuspiciousKeyword",
            ]
        ].describe()
    )

    df.to_csv(output_path, index=False)

    print(f"\nSaved feature-engineered dataset to: {output_path}")
    print(f"Output shape: {df.shape}")


if __name__ == "__main__":
    main()