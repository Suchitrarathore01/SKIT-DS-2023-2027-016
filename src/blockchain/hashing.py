"""Deterministic Keccak-256 threat hashing module.

This module provides cryptographic fingerprinting for canonicalized threat messages
and URLs for ChainShield.

Architecture Note:
- Computes Ethereum-compatible Keccak-256 digests matching Solidity `bytes32`.
- Hashes the complete canonicalized representation as ONE UTF-8 byte sequence.
- Employs explicit domain separation ('message:' and 'url:') to guarantee that
  canonical messages and canonical URLs cannot collide.
- Empty or invalid inputs raise a ValueError, preventing creation of accidental
  zero-value or empty-string threat fingerprints.
"""

from __future__ import annotations

import re
from typing import Optional

try:
    from Crypto.Hash import keccak
except ImportError:  # pragma: no cover
    from Cryptodome.Hash import keccak  # type: ignore[no-redef]

from src.blockchain.canonicalize import canonicalize_message, canonicalize_url

# Domain separation prefixes
MESSAGE_DOMAIN_PREFIX = "message:"
URL_DOMAIN_PREFIX = "url:"

# Regular expression matching a standard 32-byte Ethereum hex string (0x + 64 hex chars)
_BYTES32_HEX_PATTERN = re.compile(r"^0x[0-9a-f]{64}$")


def keccak256(data: bytes) -> str:
    """Compute Ethereum-compatible Keccak-256 digest of arbitrary bytes.

    Args:
        data: Raw byte sequence to hash.

    Returns:
        0x-prefixed 64-character lowercase hex string representing bytes32.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"Data must be bytes or bytearray, got {type(data).__name__}")

    hasher = keccak.new(digest_bits=256)
    hasher.update(data)
    return f"0x{hasher.hexdigest()}"


def generate_message_hash(message: Optional[str]) -> str:
    """Generate a deterministic Keccak-256 threat fingerprint for a message.

    Workflow:
    1. Input Validation: Raises ValueError if message is None, empty, or whitespace.
    2. Canonicalization: Uses `canonicalize_message` (Unicode NFKC, lowercase, smart quote
       normalization, NLTK tokenization preserving exact token order, repetition, stopwords,
       numbers, and punctuation).
    3. Empty Canonical Guard: Raises ValueError if the canonicalized result is empty.
    4. Domain Separation: Prepends 'message:' prefix to prevent collision with URLs.
    5. UTF-8 Encoding: Encodes the domain-prefixed canonical string to UTF-8 bytes.
    6. Keccak-256 Hashing: Hashes the complete byte sequence as a single digest.

    Args:
        message: The raw input message string.

    Returns:
        0x-prefixed 64-character lowercase hex string (Solidity bytes32).

    Raises:
        ValueError: If message is None, empty, whitespace-only, or produces an empty canonical string.
    """
    if message is None or not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be None, empty, or contain only whitespace.")

    canonical = canonicalize_message(message)
    if not canonical:
        raise ValueError("Canonicalized message is empty and cannot be hashed.")

    payload = f"{MESSAGE_DOMAIN_PREFIX}{canonical}".encode("utf-8")
    digest = keccak256(payload)

    return digest


def generate_url_hash(url: Optional[str]) -> str:
    """Generate a deterministic Keccak-256 threat fingerprint for a URL.

    Workflow:
    1. Input Validation: Raises ValueError if url is None, empty, or whitespace.
    2. Canonicalization: Uses `canonicalize_url` (RFC 3986 normalization: lowercased scheme/host,
       default port stripping, dot-segment resolution, trailing slash preservation, sorted queries,
       and fragment normalization).
    3. Empty Canonical Guard: Raises ValueError if the canonicalized result is empty.
    4. Domain Separation: Prepends 'url:' prefix to prevent collision with messages.
    5. UTF-8 Encoding: Encodes the domain-prefixed canonical URL to UTF-8 bytes.
    6. Keccak-256 Hashing: Hashes the complete byte sequence as a single digest.

    Args:
        url: The raw input URL string.

    Returns:
        0x-prefixed 64-character lowercase hex string (Solidity bytes32).

    Raises:
        ValueError: If url is None, empty, whitespace-only, or produces an empty canonical URL.
    """
    if url is None or not isinstance(url, str) or not url.strip():
        raise ValueError("URL cannot be None, empty, or contain only whitespace.")

    canonical = canonicalize_url(url)
    if not canonical:
        raise ValueError("Canonicalized URL is empty and cannot be hashed.")

    payload = f"{URL_DOMAIN_PREFIX}{canonical}".encode("utf-8")
    digest = keccak256(payload)

    return digest
