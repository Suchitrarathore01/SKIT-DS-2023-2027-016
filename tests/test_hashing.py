"""Comprehensive unit tests for deterministic Keccak-256 threat hashing in ChainShield.

Tests cover:
1. Output format: 0x-prefixed, lowercase, exactly 64 hex characters (32 bytes / bytes32).
2. Determinism: Idempotent across multiple runs.
3. Case & whitespace normalization invariance.
4. Added word sensitivity: 'your account is blocked' vs 'your account is blocked is'.
5. Removed word sensitivity: 'your account is blocked' vs 'your account blocked'.
6. Reordered words sensitivity: 'your account is blocked' vs 'blocked is your account'.
7. Stopwords sensitivity: Retaining vs omitting stopwords changes hash.
8. Punctuation sensitivity: 'account blocked!' vs 'account blocked?'.
9. Equivalent canonical URLs produce identical hashes.
10. Distinct URLs produce different hashes.
11. Message hashing vs URL hashing separation and domain separation.
12. Empty, None, and whitespace-only inputs raise ValueError.
13. Avalanche-style sanity check (Hamming distance on single-token difference).
14. Standard Ethereum Keccak-256 known test vectors (empty string, hello, etc.).
"""

import re
import pytest

from src.blockchain.hashing import (
    generate_message_hash,
    generate_url_hash,
    keccak256,
    MESSAGE_DOMAIN_PREFIX,
    URL_DOMAIN_PREFIX,
)

HEX_PATTERN = re.compile(r"^0x[0-9a-f]{64}$")


class TestKeccakKnownVectors:
    """Verifies that the underlying Keccak-256 algorithm matches Ethereum specification exactly."""

    def test_keccak_empty_string_standard_vector(self):
        """Standard Ethereum Keccak-256 digest for empty byte string b''."""
        expected = "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
        digest = keccak256(b"")
        assert digest == expected

    def test_keccak_hello_vector(self):
        """Standard Ethereum Keccak-256 digest for b'hello'."""
        expected = "0x1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
        digest = keccak256(b"hello")
        assert digest == expected

    def test_keccak_type_error(self):
        """Passing non-bytes to keccak256 must raise TypeError."""
        with pytest.raises(TypeError):
            keccak256("string not allowed")  # type: ignore[arg-type]


class TestMessageHashing:
    """Test suite for generate_message_hash(message)."""

    def test_return_format_bytes32(self):
        """Must return 0x + 64 lowercase hex characters (32 bytes)."""
        h = generate_message_hash("your account is blocked")
        assert h.startswith("0x")
        assert len(h) == 66  # '0x' + 64 hex chars
        assert HEX_PATTERN.match(h) is not None

    def test_determinism_and_idempotence(self):
        """Same input must always produce the identical hash across runs."""
        msg = "URGENT: Click http://bank.com now!"
        hashes = [generate_message_hash(msg) for _ in range(50)]
        assert all(h == hashes[0] for h in hashes)

    def test_case_and_whitespace_normalization(self):
        """Casing and whitespace variations produce identical hashes."""
        h1 = generate_message_hash("Your Account Is Blocked")
        h2 = generate_message_hash("your   account   is   blocked")
        h3 = generate_message_hash("  your\taccount\nis  blocked  ")
        assert h1 == h2 == h3

    def test_added_word_changes_hash(self):
        """EXPLICIT SPEC: 'your account is blocked' != 'your account is blocked is'."""
        h1 = generate_message_hash("your account is blocked")
        h2 = generate_message_hash("your account is blocked is")
        assert h1 != h2

    def test_removed_word_changes_hash(self):
        """EXPLICIT SPEC: 'your account is blocked' != 'your account blocked'."""
        h1 = generate_message_hash("your account is blocked")
        h2 = generate_message_hash("your account blocked")
        assert h1 != h2

    def test_reordered_words_changes_hash(self):
        """Token order changes must produce different hashes."""
        h1 = generate_message_hash("your account is blocked")
        h2 = generate_message_hash("blocked is your account")
        assert h1 != h2

    def test_stopword_preservation_affects_hash(self):
        """Preserving vs removing stopwords produces distinct hashes."""
        h_with_stopword = generate_message_hash("your account is blocked at bank")
        h_without_stopword = generate_message_hash("account blocked bank")
        assert h_with_stopword != h_without_stopword

    def test_punctuation_affects_hash(self):
        """Distinct punctuation produces distinct hashes."""
        h_exclamation = generate_message_hash("account blocked!")
        h_question = generate_message_hash("account blocked?")
        h_none = generate_message_hash("account blocked")
        assert h_exclamation != h_question
        assert h_exclamation != h_none

    def test_empty_input_raises_value_error(self):
        """Empty, None, and whitespace-only inputs must raise ValueError."""
        with pytest.raises(ValueError):
            generate_message_hash(None)
        with pytest.raises(ValueError):
            generate_message_hash("")
        with pytest.raises(ValueError):
            generate_message_hash("     ")
        with pytest.raises(ValueError):
            generate_message_hash("\t\n")

    def test_avalanche_sanity_check(self):
        """Changing one token produces a drastically different digest (different bits/hex characters)."""
        h1 = generate_message_hash("your account is blocked")
        h2 = generate_message_hash("your account is locked")
        assert h1 != h2
        # Verify hex character difference between digests
        diff_chars = sum(c1 != c2 for c1, c2 in zip(h1[2:], h2[2:]))
        # In a 64-char hex digest, changing one input word typically flips ~30-34 characters
        assert diff_chars > 20


class TestUrlHashing:
    """Test suite for generate_url_hash(url)."""

    def test_return_format_bytes32(self):
        """Must return 0x + 64 lowercase hex characters."""
        h = generate_url_hash("https://example.com/login")
        assert h.startswith("0x")
        assert len(h) == 66
        assert HEX_PATTERN.match(h) is not None

    def test_equivalent_urls_produce_identical_hash(self):
        """URLs that canonicalize identically must produce the identical hash."""
        u1 = "HTTPS://EXAMPLE.COM:443/login?b=2&a=1#token"
        u2 = "https://example.com/login?a=1&b=2#token"
        assert generate_url_hash(u1) == generate_url_hash(u2)

    def test_root_slash_and_default_port_equivalence(self):
        """Default port removal and root slash normalization result in identical hash."""
        u1 = "http://example.com:80"
        u2 = "http://example.com/"
        assert generate_url_hash(u1) == generate_url_hash(u2)

    def test_distinct_urls_produce_different_hashes(self):
        """Different paths, queries, fragments, or schemes must produce different hashes."""
        assert generate_url_hash("https://example.com/login") != generate_url_hash("http://example.com/login")
        assert generate_url_hash("https://example.com/login/") != generate_url_hash("https://example.com/login")
        assert generate_url_hash("https://example.com/?x=1") != generate_url_hash("https://example.com/?x=2")
        assert generate_url_hash("https://example.com/#a") != generate_url_hash("https://example.com/#b")

    def test_empty_url_raises_value_error(self):
        """Empty, None, or whitespace-only URL must raise ValueError."""
        with pytest.raises(ValueError):
            generate_url_hash(None)
        with pytest.raises(ValueError):
            generate_url_hash("")
        with pytest.raises(ValueError):
            generate_url_hash("   ")


class TestDomainSeparation:
    """Verifies domain separation between message hashes and URL hashes."""

    def test_message_and_url_domain_separation(self):
        """Even if raw message and raw URL have identical canonical text, hashes must not collide."""
        raw_text = "https://example.com/"
        msg_hash = generate_message_hash(raw_text)
        url_hash = generate_url_hash(raw_text)
        assert msg_hash != url_hash
        assert msg_hash.startswith("0x")
        assert url_hash.startswith("0x")

    def test_pipeline_isolation(self):
        """Message hashing uses message canonicalizer, URL hashing uses URL canonicalizer."""
        url = "https://example.com/login?b=2&a=1"
        # URL canonicalizer reorders query params to ?a=1&b=2
        url_hash = generate_url_hash(url)
        # Message canonicalizer tokenizes into 'https :// example ...'
        msg_hash = generate_message_hash(url)
        assert url_hash != msg_hash
