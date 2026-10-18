"""Comprehensive unit tests for deterministic canonicalization in ChainShield.

Tests cover:
1. Capitalization normalization
2. Whitespace normalization
3. Repeated words preservation
4. Numbers and numerical tokens preservation
5. Explicit punctuation policy
6. URLs embedded inside messages
7. Stopwords preservation (never removed)
8. Token order preservation (never sorted)
9. Added word sensitivity
10. Removed word sensitivity
11. Reordered words sensitivity
12. Explicit: 'your account is blocked' vs 'your account is blocked is'
13. Explicit: 'your account is blocked' vs 'your account blocked'
14. Normalization invariance (identical canonical output for semantically identical formatting)
15. Meaningful differences preservation
16. Representative URL canonicalization cases (scheme, host, port, path, query, fragment)
17. Malformed and edge-case inputs (None, empty, whitespace, special characters)
18. Verification that URL canonicalization does NOT use message tokenization
19. Determinism across repeated executions
"""

import pytest

from src.blockchain.canonicalize import canonicalize_message, canonicalize_url


class TestMessageCanonicalization:
    """Test suite for canonicalize_message(text)."""

    def test_capitalization_normalization(self):
        """Upper, lower, and mixed case should normalize to identical lowercase."""
        msg1 = "YOUR ACCOUNT IS BLOCKED"
        msg2 = "your account is blocked"
        msg3 = "Your Account Is Blocked"
        assert canonicalize_message(msg1) == "your account is blocked"
        assert canonicalize_message(msg2) == "your account is blocked"
        assert canonicalize_message(msg3) == "your account is blocked"
        assert canonicalize_message(msg1) == canonicalize_message(msg2) == canonicalize_message(msg3)

    def test_whitespace_normalization(self):
        """Insignificant whitespace (tabs, newlines, multiple spaces) must normalize to single spaces."""
        standard = "your account is blocked"
        variations = [
            "your   account   is   blocked",
            "  your account is blocked  ",
            "your\taccount\tis\tblocked",
            "your\naccount\nis\nblocked",
            "your  \t\n  account  is   blocked",
        ]
        for var in variations:
            assert canonicalize_message(var) == standard

    def test_repeated_words_preservation(self):
        """Repeated tokens must be preserved in full and NOT collapsed or deduplicated."""
        msg = "win win win now"
        assert canonicalize_message(msg) == "win win win now"
        assert canonicalize_message(msg) != canonicalize_message("win now")
        assert canonicalize_message("free free free") != canonicalize_message("free")

    def test_numbers_preservation(self):
        """Numbers, phone numbers, and monetary figures must be preserved as exact tokens."""
        msg = "Call 1800123456 to claim $500 reward"
        canonical = canonicalize_message(msg)
        assert "1800123456" in canonical
        assert "500" in canonical
        assert canonicalize_message("code 1234") != canonicalize_message("code 1235")
        assert canonicalize_message("loss $100") != canonicalize_message("loss $200")

    def test_punctuation_policy(self):
        """Every punctuation mark is preserved as a distinct token and not silently stripped."""
        assert canonicalize_message("urgent: action required") == "urgent : action required"
        assert canonicalize_message("account blocked!") == "account blocked !"
        assert canonicalize_message("account blocked?") == "account blocked ?"
        assert canonicalize_message("account blocked.") == "account blocked ."

        # Different punctuation marks must not collide
        assert canonicalize_message("blocked!") != canonicalize_message("blocked?")
        assert canonicalize_message("blocked!") != canonicalize_message("blocked")
        assert canonicalize_message("hello, world") != canonicalize_message("hello world")

    def test_urls_inside_messages(self):
        """URLs inside messages must be preserved as constituent tokens within the message sequence."""
        msg = "Verify your account at https://secure-bank.com/login immediately!"
        canonical = canonicalize_message(msg)
        assert canonical == "verify your account at https :// secure - bank . com / login immediately !"
        assert "https" in canonical
        assert "secure" in canonical
        assert "login" in canonical

        # Changing the URL inside the message must change the canonical output
        msg_diff = "Verify your account at https://other-bank.com/login immediately!"
        assert canonicalize_message(msg) != canonicalize_message(msg_diff)

    def test_stopword_preservation(self):
        """Stopwords ('is', 'the', 'at', 'your', 'to') must NEVER be removed."""
        with_stopwords = "your account is blocked at the bank"
        without_stopwords = "account blocked bank"
        assert canonicalize_message(with_stopwords) != canonicalize_message(without_stopwords)
        assert "is" in canonicalize_message(with_stopwords)
        assert "at" in canonicalize_message(with_stopwords)
        assert "the" in canonicalize_message(with_stopwords)

    def test_token_order_preservation(self):
        """Token order must be strictly preserved; tokens must NOT be sorted."""
        msg1 = "your account is blocked"
        msg2 = "blocked is your account"
        msg3 = "account your blocked is"
        c1 = canonicalize_message(msg1)
        c2 = canonicalize_message(msg2)
        c3 = canonicalize_message(msg3)
        assert c1 != c2
        assert c1 != c3
        assert c2 != c3

    def test_added_word(self):
        """Adding any token must change the canonical representation."""
        base = "your account is blocked"
        added = "your account is blocked now"
        assert canonicalize_message(base) != canonicalize_message(added)

    def test_removed_word(self):
        """Removing any token must change the canonical representation."""
        base = "your account is blocked"
        removed = "your account blocked"
        assert canonicalize_message(base) != canonicalize_message(removed)

    def test_explicit_blocked_vs_blocked_is(self):
        """EXPLICIT SPEC: 'your account is blocked' != 'your account is blocked is'."""
        m1 = "your account is blocked"
        m2 = "your account is blocked is"
        c1 = canonicalize_message(m1)
        c2 = canonicalize_message(m2)
        assert c1 == "your account is blocked"
        assert c2 == "your account is blocked is"
        assert c1 != c2

    def test_explicit_blocked_vs_account_blocked(self):
        """EXPLICIT SPEC: 'your account is blocked' != 'your account blocked'."""
        m1 = "your account is blocked"
        m2 = "your account blocked"
        assert canonicalize_message(m1) != canonicalize_message(m2)

    def test_explicit_blocked_now_vs_blocked(self):
        """EXPLICIT SPEC: 'your account is blocked now' != 'your account is blocked'."""
        assert canonicalize_message("your account is blocked now") != canonicalize_message("your account is blocked")

    def test_same_normalized_produces_identical_output(self):
        """Semantically identical formatting variations produce byte-for-byte identical output."""
        a = "Your   Account   Is   Blocked"
        b = "your account is blocked"
        assert canonicalize_message(a) == canonicalize_message(b)

    def test_unicode_normalization(self):
        """Unicode variants (fullwidth ASCII, curly apostrophes) normalize deterministically."""
        # Smart apostrophe vs standard apostrophe
        msg1 = "don’t click this"
        msg2 = "don't click this"
        assert canonicalize_message(msg1) == canonicalize_message(msg2)

        # Fullwidth characters vs standard
        msg_fullwidth = "ＡＣＣＯＵＮＴ"
        assert canonicalize_message(msg_fullwidth) == "account"

    def test_edge_cases_and_malformed_inputs(self):
        """Edge cases: empty string, whitespace only, None, non-string."""
        assert canonicalize_message("") == ""
        assert canonicalize_message("   ") == ""
        assert canonicalize_message(None) == ""
        assert canonicalize_message(12345) == "12345"

    def test_determinism_across_multiple_runs(self):
        """Canonicalization must be strictly idempotent and deterministic across repeated executions."""
        msg = "URGENT: Click http://phish.net/claim?u=123 now to prevent suspension!"
        results = [canonicalize_message(msg) for _ in range(50)]
        assert all(r == results[0] for r in results)


class TestUrlCanonicalization:
    """Test suite for canonicalize_url(url)."""

    def test_scheme_and_hostname_lowercasing(self):
        """Scheme and hostname must be lowercased."""
        u1 = "HTTPS://EXAMPLE.COM/login"
        u2 = "https://example.com/login"
        assert canonicalize_url(u1) == canonicalize_url(u2)
        assert canonicalize_url(u1) == "https://example.com/login"

    def test_root_path_normalization(self):
        """Bare domain without path normalizes to have root '/' path."""
        assert canonicalize_url("http://example.com") == "http://example.com/"
        assert canonicalize_url("HTTP://EXAMPLE.COM") == "http://example.com/"
        assert canonicalize_url("https://example.com/") == "https://example.com/"

    def test_trailing_slash_preservation(self):
        """Trailing slash on non-empty paths is preserved to prevent endpoint collision."""
        with_slash = canonicalize_url("https://example.com/login/")
        without_slash = canonicalize_url("https://example.com/login")
        assert with_slash == "https://example.com/login/"
        assert without_slash == "https://example.com/login"
        assert with_slash != without_slash

    def test_default_port_removal(self):
        """Default ports (80 for http, 443 for https) are removed, custom ports kept."""
        assert canonicalize_url("http://example.com:80/path") == "http://example.com/path"
        assert canonicalize_url("https://example.com:443/path") == "https://example.com/path"
        assert canonicalize_url("http://example.com:8080/path") == "http://example.com:8080/path"
        assert canonicalize_url("https://example.com:8443/path") == "https://example.com:8443/path"

    def test_trailing_dns_dot_removal(self):
        """Trailing DNS root dot from hostname is removed."""
        assert canonicalize_url("https://example.com./path") == "https://example.com/path"

    def test_dot_segment_resolution(self):
        """Dot segments ('.' and '..') in path are resolved."""
        assert canonicalize_url("https://example.com/a/b/../c") == "https://example.com/a/c"
        assert canonicalize_url("https://example.com/a/./b/c") == "https://example.com/a/b/c"
        assert canonicalize_url("https://example.com/a/b/../c/") == "https://example.com/a/c/"

    def test_query_parameter_sorting(self):
        """Query parameters must be sorted deterministically by key, then value."""
        u1 = "https://example.com/search?b=2&a=1&c=3"
        u2 = "https://example.com/search?c=3&a=1&b=2"
        expected = "https://example.com/search?a=1&b=2&c=3"
        assert canonicalize_url(u1) == expected
        assert canonicalize_url(u2) == expected

    def test_duplicate_query_parameter_preservation(self):
        """Duplicate query parameter keys are preserved in sorted order."""
        u = "https://example.com/api?tag=python&tag=crypto&page=1"
        assert canonicalize_url(u) == "https://example.com/api?page=1&tag=crypto&tag=python"

    def test_percent_encoding_normalization(self):
        """Unreserved characters are decoded, reserved characters keep uppercase hex."""
        u = "http://example.com/%7Ealice/%61bc/%2f/%2F"
        assert canonicalize_url(u) == "http://example.com/~alice/abc/%2F/%2F"

    def test_fragment_policy(self):
        """Fragments are preserved when present and omitted when absent."""
        with_frag = "https://example.com/dapp#/claim?u=1"
        without_frag = "https://example.com/dapp"
        assert canonicalize_url(with_frag) == "https://example.com/dapp#/claim?u=1"
        assert canonicalize_url(without_frag) == "https://example.com/dapp"
        assert canonicalize_url(with_frag) != canonicalize_url(without_frag)

        # Empty fragment or trailing '#' is omitted
        assert canonicalize_url("https://example.com/page#") == "https://example.com/page"

    def test_schemeless_url_handling(self):
        """Schemeless URL input defaults to http."""
        assert canonicalize_url("example.com/test") == "http://example.com/test"
        assert canonicalize_url("www.phish-bank.com") == "http://www.phish-bank.com/"

    def test_userinfo_preservation(self):
        """User credentials in netloc are preserved while host is lowercased."""
        u = "https://admin:secret@MYBANK.COM/dashboard"
        assert canonicalize_url(u) == "https://admin:secret@mybank.com/dashboard"

    def test_edge_cases_url(self):
        """Edge cases: None, empty string, whitespace."""
        assert canonicalize_url(None) == ""
        assert canonicalize_url("") == ""
        assert canonicalize_url("   ") == ""

    def test_distinct_urls_do_not_collide(self):
        """Distinct paths, query values, schemes, or ports MUST NOT collapse."""
        assert canonicalize_url("http://example.com/") != canonicalize_url("https://example.com/")
        assert canonicalize_url("http://example.com/a") != canonicalize_url("http://example.com/b")
        assert canonicalize_url("http://example.com/?x=1") != canonicalize_url("http://example.com/?x=2")
        assert canonicalize_url("http://example.com:8080/") != canonicalize_url("http://example.com:8081/")

    def test_url_canonicalization_does_not_use_message_tokenization(self):
        """Verify URL canonicalization is completely separate from message tokenization."""
        raw_url = "https://example.com/login?b=2&a=1#token"

        url_canonical = canonicalize_url(raw_url)
        msg_canonical = canonicalize_message(raw_url)

        # url_canonical is a valid RFC 3986 URL with sorted query parameters
        assert url_canonical == "https://example.com/login?a=1&b=2#token"

        # msg_canonical is whitespace-separated NLTK tokens
        assert msg_canonical == "https :// example . com / login ? b = 2 & a = 1 # token"

        # They must be entirely distinct representations
        assert url_canonical != msg_canonical
