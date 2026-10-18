"""Unit tests for feature extraction functions in src/features.py."""

import pytest
from src.features import (
    extract_url_features,
    extract_text_features,
    build_tfidf_features,
    preprocess_text,
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


class TestPreprocessText:
    """Tests for preprocess_text(text: str) -> str."""

    def test_empty_and_non_string_inputs(self):
        assert preprocess_text("") == ""
        assert preprocess_text("   ") == ""
        assert preprocess_text(None) == ""
        assert preprocess_text(12345) == ""

    def test_lowercasing(self):
        res = preprocess_text("URGENT ALERT NOW")
        assert "URGENT" not in res
        assert "ALERT" not in res
        assert "urgent" in res
        assert "now" in res

    @pytest.mark.parametrize(
        "url_text",
        [
            "Visit https://example.com/login today",
            "Go to http://phishing-portal.com/account",
            "Check www.fake-bank.org immediately",
            "Claim prize at bit.ly/prize2026 now",
            "Link cutt.ly/discount for rewards",
            "Access http://192.168.1.1:8080/admin",
            "Visit tinyurl.com/free-card immediately",
        ],
    )
    def test_url_replacement(self, url_text):
        res = preprocess_text(url_text)
        assert "urltoken" in res
        assert "http" not in res
        assert "www" not in res
        assert ".com" not in res
        assert ".org" not in res

    def test_url_with_parameters_and_digits(self):
        text = "Visit https://secure.bank.com/verify?id=12345678&token=abcdef now"
        res = preprocess_text(text)
        assert "urltoken" in res
        assert "12345678" not in res

    @pytest.mark.parametrize(
        "phone_text",
        [
            "Call 800-555-0199 for assistance",
            "Call +1-800-555-0199 immediately",
            "Reach us at (800) 555-0199 today",
            "Call +1 (800) 555-0199 right now",
            "Dial 800.555.0199 now",
            "Call +44 7911 123456 for free advice",
            "Call 0800 123 4567 today",
        ],
    )
    def test_phone_number_replacement(self, phone_text):
        res = preprocess_text(phone_text)
        assert "numtoken" in res
        assert "555" not in res
        assert "0199" not in res
        assert "123456" not in res

    @pytest.mark.parametrize(
        "digits_text",
        [
            "Your verification code is 12345",
            "Account number 9876543210 is flagged",
            "Reference id 99999999",
        ],
    )
    def test_digit_runs_replacement_5_or_more(self, digits_text):
        res = preprocess_text(digits_text)
        assert "numtoken" in res
        assert "12345" not in res
        assert "9876543210" not in res
        assert "99999999" not in res

    def test_short_digits_not_replaced(self):
        text = "Your pin is 1234 and year is 2026"
        res = preprocess_text(text)
        assert "numtoken" not in res
        assert "1234" in res
        assert "2026" in res

    def test_punctuation_removal(self):
        text = "Urgent: call now! Free prizes, rewards & bonus money... win-win?!"
        res = preprocess_text(text)
        for char in ":!.,&?":
            assert char not in res

    def test_stopword_removal(self):
        text = "This is a message from the system in the office with information"
        res = preprocess_text(text)
        tokens = res.split()
        for sw in ["this", "is", "a", "from", "the", "in", "with"]:
            assert sw not in tokens
        assert "message" in tokens
        assert "system" in tokens
        assert "information" in tokens

    def test_free_and_now_kept(self):
        text = "Claim your free prize now! It is free right now."
        res = preprocess_text(text)
        tokens = set(res.split())
        assert "free" in tokens
        assert "now" in tokens
        assert "is" not in tokens
        assert "it" not in tokens

    def test_all_scam_signals_kept(self):
        text = "Urgent! You should call and stop immediately to win your free gift now."
        res = preprocess_text(text)
        tokens = set(res.split())
        for signal in ["now", "free", "win", "call", "stop", "urgent", "your", "you"]:
            assert signal in tokens
        assert "and" not in tokens
        assert "to" not in tokens

    def test_lemmatization(self):
        text = "Users received multiple prizes, cars, and alerts"
        res = preprocess_text(text)
        tokens = res.split()
        assert "user" in tokens
        assert "prize" in tokens
        assert "car" in tokens
        assert "alert" in tokens

    def test_combined_phishing_message(self):
        text = "URGENT: Win $50000 cash now! Call 1-800-555-0199 or click https://bank-scam.com/claim for free gift."
        res = preprocess_text(text)
        assert "urltoken" in res
        assert "numtoken" in res
        assert "urgent" in res
        assert "win" in res
        assert "now" in res
        assert "call" in res
        assert "free" in res
        assert "or" not in res.split()
