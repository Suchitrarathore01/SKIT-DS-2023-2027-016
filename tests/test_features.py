"""Unit tests for feature extraction functions in src/features.py."""

import pytest
from src.features import (
    extract_url_features,
    extract_text_features,
    build_tfidf_features,
)


class TestExtractUrlFeatures:
    """Tests for extract_url_features(text) -> dict."""

    def test_default_empty_or_none(self):
        expected = {
            "has_url": False,
            "shortener_used": False,
            "ip_as_domain": False,
            "https_present": False,
        }
        assert extract_url_features("") == expected
        assert extract_url_features("   ") == expected
        assert extract_url_features(None) == expected
        assert extract_url_features(123) == expected

    def test_benign_text_without_url(self):
        text = "Hey are we still meeting for lunch today at the cafe?"
        res = extract_url_features(text)
        assert res == {
            "has_url": False,
            "shortener_used": False,
            "ip_as_domain": False,
            "https_present": False,
        }
        for k, v in res.items():
            assert isinstance(v, bool)

    def test_http_url(self):
        text = "Please check your statement at http://mybank-portal.com/login"
        res = extract_url_features(text)
        assert res["has_url"] is True
        assert res["https_present"] is False
        assert res["shortener_used"] is False
        assert res["ip_as_domain"] is False

    def test_https_url(self):
        text = "Secure portal: https://secure.bank.com/account/verify"
        res = extract_url_features(text)
        assert res["has_url"] is True
        assert res["https_present"] is True
        assert res["shortener_used"] is False
        assert res["ip_as_domain"] is False

    def test_www_url_without_scheme(self):
        text = "Visit www.example.org to see updates"
        res = extract_url_features(text)
        assert res["has_url"] is True
        assert res["https_present"] is False
        assert res["shortener_used"] is False
        assert res["ip_as_domain"] is False

    @pytest.mark.parametrize(
        "url_text, expected_https",
        [
            ("Claim your reward at bit.ly/prize2026 now!", False),
            ("Check https://tinyurl.com/free-card immediately", True),
            ("Click t.co/xyz99 for verification", False),
            ("Discount voucher: http://goo.gl/special", False),
            ("Visit https://is.gd/deal today", True),
            ("Link: cutt.ly/discount", False),
        ],
    )
    def test_shortener_detection(self, url_text, expected_https):
        res = extract_url_features(url_text)
        assert res["has_url"] is True
        assert res["shortener_used"] is True
        assert res["https_present"] is expected_https
        assert res["ip_as_domain"] is False

    @pytest.mark.parametrize(
        "ip_text, expected_https",
        [
            ("Login at http://192.168.1.1/admin to restore service", False),
            ("Access portal https://10.0.0.1:8080/auth immediately", True),
            ("Malicious link 192.168.0.50/login.php", False),
            ("Connect to http://127.0.0.1:3000/api", False),
        ],
    )
    def test_ip_as_domain_detection(self, ip_text, expected_https):
        res = extract_url_features(ip_text)
        assert res["has_url"] is True
        assert res["ip_as_domain"] is True
        assert res["https_present"] is expected_https
        assert res["shortener_used"] is False


class TestExtractTextFeatures:
    """Tests for extract_text_features(text) -> dict."""

    def test_default_empty_or_none(self):
        res_none = extract_text_features(None)
        assert res_none == {
            "length": 0,
            "has_urgent_word": False,
            "has_money_word": False,
        }

        res_empty = extract_text_features("")
        assert res_empty == {
            "length": 0,
            "has_urgent_word": False,
            "has_money_word": False,
        }

    def test_length_calculation(self):
        text = "Hello world!"
        res = extract_text_features(text)
        assert res["length"] == len(text)
        assert isinstance(res["length"], int)

    def test_benign_text_no_flags(self):
        text = "Are you available for a quick sync this afternoon?"
        res = extract_text_features(text)
        assert res["length"] == len(text)
        assert res["has_urgent_word"] is False
        assert res["has_money_word"] is False

    @pytest.mark.parametrize(
        "urgent_msg",
        [
            "URGENT: Your account has been suspended.",
            "Immediate action required regarding your policy.",
            "Warning: suspicious activity detected on your profile.",
            "Please respond asap to prevent account closure.",
            "Attention: your session will expire in 10 minutes.",
            "Hurry! Final notice on your pending order.",
        ],
    )
    def test_urgent_words_detection(self, urgent_msg):
        res = extract_text_features(urgent_msg)
        assert res["has_urgent_word"] is True

    @pytest.mark.parametrize(
        "money_msg",
        [
            "Congratulations! You won a $1,000 cash prize!",
            "Claim your £500 tax refund today.",
            "Transfer 200 euro to receive your bonus.",
            "Your loan application has been approved.",
            "Deposit funds into your bitcoin crypto wallet.",
            "Receive 100 dollars immediately upon survey completion.",
            "Winner! You have won £1000 in the weekly lottery.",
        ],
    )
    def test_money_words_detection(self, money_msg):
        res = extract_text_features(money_msg)
        assert res["has_money_word"] is True

    def test_combined_urgent_and_money_words(self):
        text = "URGENT: Claim your $500 cash prize immediately before it expires!"
        res = extract_text_features(text)
        assert res["length"] == len(text)
        assert res["has_urgent_word"] is True
        assert res["has_money_word"] is True

    def test_case_insensitivity(self):
        lower_res = extract_text_features("urgent cash")
        upper_res = extract_text_features("URGENT CASH")
        assert lower_res["has_urgent_word"] is True
        assert lower_res["has_money_word"] is True
        assert upper_res["has_urgent_word"] is True
        assert upper_res["has_money_word"] is True


class TestBuildTfidfFeatures:
    """Tests for build_tfidf_features(texts, max_features=5000) -> tuple."""

    def test_build_tfidf_output_types_and_defaults(self):
        sample_texts = [
            "Urgent: claim your lottery prize now",
            "Are we meeting for lunch today",
            "Suspicious login alert on your banking account",
            "Win $500 cash today by clicking the link",
        ]
        features, vectorizer = build_tfidf_features(sample_texts)

        # Check tuple return
        assert hasattr(features, "shape")
        assert features.shape[0] == len(sample_texts)

        # Check vectorizer settings
        assert vectorizer.ngram_range == (1, 2)
        assert vectorizer.max_features == 5000

        # Check ngrams are created
        feature_names = vectorizer.get_feature_names_out()
        assert any(" " in name for name in feature_names)  # contains bigrams

    def test_build_tfidf_custom_max_features(self):
        sample_texts = [
            "Free cash award won today",
            "Call immediately for your prize",
        ]
        features, vectorizer = build_tfidf_features(sample_texts, max_features=10)
        assert vectorizer.max_features == 10
        assert features.shape[1] <= 10
