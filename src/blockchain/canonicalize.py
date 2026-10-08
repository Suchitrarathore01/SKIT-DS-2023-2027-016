"""Deterministic threat message and URL canonicalization pipeline.

This module provides off-chain deterministic canonicalization for messages and URLs
prior to Keccak-256 threat hashing in ChainShield.

Architecture Note:
- Canonicalization and NLP processing MUST run strictly OFF-CHAIN.
- Solidity smart contracts NEVER perform tokenization, string parsing, or NLP.
- The blockchain serves only as an immutable, tamper-evident registry of bytes32
  threat hashes.
"""

from __future__ import annotations

import posixpath
import re
import unicodedata
import urllib.parse
from typing import Optional

from nltk.tokenize import WordPunctTokenizer

# NLTK WordPunctTokenizer splits text on whitespace and separates all sequences
# of alphanumeric characters from punctuation sequences (\w+|[^\w\s]+).
# It does NOT require any external downloaded corpus/model (pure rule-based),
# making it completely deterministic and reproducible across environments.
_TOKENIZER = WordPunctTokenizer()

# Regex matching percent-encoded octets: %XX
_PERCENT_HEX_PATTERN = re.compile(r"%([0-9a-fA-F]{2})")

# Default network ports for common web schemes
_DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "ftp": 21,
}


def _normalize_percent_encoding(s: str) -> str:
    """Normalize percent-encoding according to RFC 3986.

    - Decodes unreserved characters: ALPHA, DIGIT, '-', '.', '_', '~'.
    - Normalizes hex digits of reserved percent-encoded octets to uppercase (e.g. %2f -> %2F).
    """
    if not s or "%" not in s:
        return s

    def _replace(match: re.Match[str]) -> str:
        hex_val = match.group(1)
        byte_val = int(hex_val, 16)
        # RFC 3986 Section 2.3 Unreserved Characters:
        # 0-9 (48-57), A-Z (65-90), a-z (97-122), '-' (45), '.' (46), '_' (95), '~' (126)
        if (
            (48 <= byte_val <= 57)
            or (65 <= byte_val <= 90)
            or (97 <= byte_val <= 122)
            or byte_val in (45, 46, 95, 126)
        ):
            return chr(byte_val)
        return f"%{hex_val.upper()}"

    return _PERCENT_HEX_PATTERN.sub(_replace, s)


def _normalize_netloc(scheme: str, netloc: str) -> str:
    """Normalize network location (authority) component of a URL.

    - Lowercases hostname.
    - Strips trailing DNS root dot from hostname.
    - Removes default port for the scheme (:80 for http, :443 for https, :21 for ftp).
    - Preserves userinfo (credentials) if present.
    - Handles IPv6 literal addresses correctly.
    """
    if not netloc:
        return ""

    userinfo = ""
    hostport = netloc

    # Extract userinfo if present
    if "@" in hostport:
        userinfo, hostport = hostport.split("@", 1)
        userinfo += "@"

    # Separate host and port
    if hostport.startswith("["):
        # IPv6 literal
        closing_idx = hostport.find("]")
        if closing_idx != -1:
            host = hostport[: closing_idx + 1].lower()
            port = hostport[closing_idx + 1 :]
        else:
            host = hostport.lower()
            port = ""
    elif ":" in hostport:
        host, port_str = hostport.split(":", 1)
        host = host.lower()
        port = f":{port_str}"
    else:
        host = hostport.lower()
        port = ""

    # Strip trailing DNS root dot from hostname (except IPv6)
    if host.endswith(".") and not host.startswith("["):
        host = host.rstrip(".")

    # Remove default port if present
    if port and port.startswith(":"):
        try:
            port_num = int(port[1:])
            default_port = _DEFAULT_PORTS.get(scheme.lower())
            if default_port is not None and port_num == default_port:
                port = ""
        except ValueError:
            pass

    return f"{userinfo}{host}{port}"


def _normalize_path(path: str) -> str:
    """Normalize URL path component.

    - Resolves dot segments ('.' and '..') via posixpath.normpath.
    - Normalizes percent-encoding (decodes unreserved chars, capitalizes hex digits).
    - Preserves trailing slash for non-empty paths.
    - Empty or bare root path normalizes to '/'.
    - Encodes illegal unencoded characters while preserving valid path delimiters.
    """
    if not path or path == "/":
        return "/"

    ends_with_slash = path.endswith("/")

    # Encode any raw illegal characters (e.g. unencoded spaces, square brackets)
    safe_path_chars = "/:@!$&'()*+,;=-_.~%"
    encoded_path = urllib.parse.quote(path, safe=safe_path_chars)

    # Normalize percent-encoded sequences
    normalized_enc = _normalize_percent_encoding(encoded_path)

    # Resolve dot segments
    resolved = posixpath.normpath(normalized_enc)
    if not resolved.startswith("/"):
        resolved = f"/{resolved}"

    # Retain trailing slash if original path ended with one
    if ends_with_slash and not resolved.endswith("/"):
        resolved += "/"

    return resolved


def _normalize_query(query: str) -> str:
    """Normalize URL query string.

    - Parses query parameters into (key, value) pairs, preserving blank values.
    - Sorts query parameters deterministically by key, then value.
    - Preserves duplicate parameter keys.
    - Re-encodes with RFC 3986 percent-encoding.
    """
    if not query:
        return ""

    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return ""

    pairs.sort()
    encoded = urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)
    return _normalize_percent_encoding(encoded)


def _normalize_fragment(fragment: str) -> str:
    """Normalize URL fragment.

    - Normalizes percent-encoding.
    - Strips whitespace.
    """
    if not fragment:
        return ""
    safe_fragment_chars = "/?#:@!$&'()*+,;=-_.~%"
    encoded = urllib.parse.quote(fragment.strip(), safe=safe_fragment_chars)
    return _normalize_percent_encoding(encoded)


# Smart quote translation map standardizing mobile/OS typographic quotes to ASCII quotes
_SMART_QUOTE_MAP = str.maketrans({
    "\u2018": "'",  # Left single quotation mark
    "\u2019": "'",  # Right single quotation mark
    "\u201c": '"',  # Left double quotation mark
    "\u201d": '"',  # Right double quotation mark
    "\u201a": "'",  # Single low-9 quotation mark
    "\u201e": '"',  # Double low-9 quotation mark
    "`": "'",       # Backtick to apostrophe
    "´": "'",       # Acute accent to apostrophe
})


def canonicalize_message(text: Optional[str]) -> str:
    """Deterministically canonicalize a threat message string using NLTK.

    This function prepares threat message text for exact cryptographic fingerprinting.

    Policy:
    1. Unicode Normalization: Input is normalized using Unicode NFKC (Compatibility
       Decomposition followed by Canonical Composition), standardizing compatibility
       glyphs, fullwidth characters, and combining marks.
    2. Quote Normalization: Typographic smart quotes ('’, ‘', '“', '”') commonly
       inserted by mobile OS keyboards (iOS/Android) are standardized to standard ASCII
       single and double quotes ('\\'' and '\"').
    3. Case Normalization: Lowercases the text.
    4. Tokenization: Tokenized deterministically using NLTK WordPunctTokenizer.
    5. Exact Token Preservation:
       - Every token is preserved in its EXACT original sequence.
       - Token order is strictly preserved (NO sorting).
       - Repeated tokens are preserved (NO set/bag-of-words conversion).
       - Numbers, digits, and financial figures are preserved.
       - Stopwords are strictly PRESERVED (never removed).
       - NO stemming or lemmatization is applied.
       - NO semantic reduction or word dropping is performed.
    6. Punctuation Policy:
       - Every punctuation mark or punctuation sequence recognized by WordPunctTokenizer
         (e.g., '!', '?', ':', '://', '$', '#', '@', ',') is preserved as a distinct token.
       - Punctuation is NOT stripped or discarded; doing so would collapse distinct threats.
    7. Canonical Representation:
       - Tokens are joined by a single ASCII space: " ".join(tokens).
       - Insignificant whitespace variations between tokens are thus normalized,
         while token identity, count, and order remain completely deterministic.

    Args:
        text: The raw input message text.

    Returns:
        The canonicalized message string, or an empty string if input is empty/None.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    stripped = text.strip()
    if not stripped:
        return ""

    # 1. Unicode NFKC normalization
    normalized_unicode = unicodedata.normalize("NFKC", stripped)

    # 2. Smart quotes normalization
    normalized_quotes = normalized_unicode.translate(_SMART_QUOTE_MAP)

    # 3. Lowercase
    lowercased = normalized_quotes.lower()

    # 4. Deterministic NLTK tokenization
    tokens = _TOKENIZER.tokenize(lowercased)

    if not tokens:
        return ""

    # 5. Canonical whitespace-delimited sequence
    return " ".join(tokens)



def canonicalize_url(url: Optional[str]) -> str:
    """Deterministically canonicalize a URL string.

    This function implements a dedicated URL canonicalization pipeline following
    RFC 3986 specifications. It does NOT use NLTK message tokenization.

    Policy:
    1. Whitespace & Unicode: Strips leading/trailing whitespace and applies NFKC normalization.
    2. Scheme:
       - Lowercased (e.g. 'HTTPS://' -> 'https://').
       - If no scheme is provided (e.g. 'example.com/login'), defaults to 'http://'.
       - Protocol-relative URLs (e.g. '//example.com') preserve leading '//'.
    3. Hostname & Port:
       - Hostname is lowercased.
       - Trailing DNS root dots are removed (e.g. 'example.com.' -> 'example.com').
       - Default ports are stripped (:80 for http, :443 for https, :21 for ftp).
       - Non-default ports are preserved (e.g. :8080).
       - Userinfo (user:pass@) is preserved, lowercasing only the host.
    4. Path:
       - Resolves dot segments ('.' and '..') via RFC 3986 section 5.2.4.
       - Empty path for web URLs normalizes to '/'.
       - Trailing slash is PRESERVED on non-empty paths (e.g. '/login' != '/login/').
       - Normalizes percent-encoding: unreserved characters are decoded; reserved
         characters retain uppercase percent-encoding (e.g. %2F).
       - Characters that require encoding are percent-encoded safely.
    5. Query Parameters:
       - Query parameters are parsed into key-value pairs (preserving blank values).
       - Pairs are sorted deterministically by key, then value.
       - Duplicate parameter keys are preserved in sorted order.
       - If query is empty, the '?' delimiter is omitted.
    6. Fragment Policy:
       - Non-empty fragments are normalized and preserved ('#' included).
       - Modern Web3/phishing threats frequently encode malicious payloads or routes
         in URL fragments (e.g. '#/drainer'), so fragments MUST NOT be stripped.
       - Empty fragments or trailing '#' are omitted.

    Args:
        url: The raw input URL string.

    Returns:
        The canonicalized URL string, or an empty string if input is empty/None.
    """
    if url is None:
        return ""

    if not isinstance(url, str):
        url = str(url)

    url_str = url.strip()
    if not url_str:
        return ""

    # 1. Unicode normalization
    url_str = unicodedata.normalize("NFKC", url_str)

    # 2. Scheme parsing
    if "://" in url_str:
        scheme_part, rest = url_str.split("://", 1)
        scheme = scheme_part.lower()
        url_to_parse = f"{scheme}://{rest}"
    elif url_str.startswith("//"):
        scheme = ""
        url_to_parse = url_str
    else:
        # Schemeless input (e.g. "example.com/path") defaults to http
        scheme = "http"
        url_to_parse = f"http://{url_str}"

    parsed = urllib.parse.urlsplit(url_to_parse)

    # 3. Component normalization
    netloc = _normalize_netloc(scheme, parsed.netloc)
    path = _normalize_path(parsed.path)
    query = _normalize_query(parsed.query)
    fragment = _normalize_fragment(parsed.fragment)

    # 4. Canonical assembly
    prefix = f"{scheme}://" if scheme else "//"
    canonical = f"{prefix}{netloc}{path}"

    if query:
        canonical += f"?{query}"
    if fragment:
        canonical += f"#{fragment}"

    return canonical
