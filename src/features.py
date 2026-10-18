"""Feature extraction utilities for phishing and smishing text analysis."""

import re
from typing import Any, Dict, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer

# Known URL shortener domains commonly observed in smishing/phishing
SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
    "rebrand.ly",
    "tiny.cc",
    "shorturl.at",
    "adf.ly",
    "bl.ink",
    "lnkd.in",
    "tr.im",
    "tiny.pl",
    "qr.net",
    "v.gd",
    "soo.gd",
    "s.id",
    "trib.al",
    "bc.vc",
    "rb.gy",
    "clck.ru",
    "rotf.lol",
    "smarturl.it",
    "linktr.ee",
}

SHORTENER_PATTERN = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?(?:"
    + "|".join(re.escape(d) for d in sorted(SHORTENER_DOMAINS, key=len, reverse=True))
    + r")(?=[/?#\s]|$)"
)

# IPv4 regex matching valid octets (0-255)
_IPV4_OCTET = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
_IPV4_ADDR = rf"(?:{_IPV4_OCTET}\.){{3}}{_IPV4_OCTET}"

IP_DOMAIN_PATTERN = re.compile(
    rf"(?i)(?:https?://)?\b{_IPV4_ADDR}(?::\d{{1,5}})?(?=[/?#\s]|$)"
)

HTTPS_PATTERN = re.compile(r"(?i)\bhttps://")

# General URL pattern matching http(s), www, or common domain patterns
URL_GENERAL_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>{}\"']+|"
    r"\b[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|io|co|xyz|info|biz|cc|tv|me|site|online|top|club|vip|app|dev|tech)(?:/[^\s<>{}\"']*)?"
)

# Urgent keywords indicative of smishing pressure/urgency
URGENT_WORDS = [
    "urgent",
    "urgently",
    "immediate",
    "immediately",
    "asap",
    "hurry",
    "alert",
    "warning",
    "critical",
    "suspended",
    "suspension",
    "suspend",
    "expire",
    "expires",
    "expired",
    "expiring",
    "deadline",
    "attention",
    "action",
    "important",
    "now",
    "instant",
    "instantly",
    "final notice",
    "last chance",
    "act now",
]

URGENT_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in sorted(URGENT_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Money keywords and currency symbols indicative of financial incentives/scams
MONEY_WORDS = [
    "cash",
    "dollar",
    "dollars",
    "usd",
    "cent",
    "cents",
    "money",
    "pound",
    "pounds",
    "gbp",
    "euro",
    "euros",
    "eur",
    "prize",
    "prizes",
    "reward",
    "rewards",
    "refund",
    "refunds",
    "win",
    "won",
    "winner",
    "funds",
    "fund",
    "payment",
    "payments",
    "pay",
    "paid",
    "fee",
    "fees",
    "cost",
    "costs",
    "loan",
    "loans",
    "credit",
    "credits",
    "bonus",
    "bonuses",
    "crypto",
    "bitcoin",
    "btc",
    "eth",
    "wallet",
    "cheque",
    "check",
    "checks",
    "salary",
    "deposit",
    "deposits",
    "withdrawal",
    "withdrawals",
    "million",
    "billion",
    "thousand",
    "jackpot",
]

MONEY_PATTERN = re.compile(
    r"[$£€¥₹]|\b(?:"
    + "|".join(re.escape(w) for w in sorted(MONEY_WORDS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def extract_url_features(text: Any) -> Dict[str, bool]:
    """Extract URL-related indicators from input text.

    Args:
        text: Input string or text content.

    Returns:
        dict: {
            "has_url": bool,
            "shortener_used": bool,
            "ip_as_domain": bool,
            "https_present": bool,
        }
    """
    default_result = {
        "has_url": False,
        "shortener_used": False,
        "ip_as_domain": False,
        "https_present": False,
    }

    if text is None or not isinstance(text, str) or not text.strip():
        return default_result

    https_present = bool(HTTPS_PATTERN.search(text))
    shortener_used = bool(SHORTENER_PATTERN.search(text))
    ip_as_domain = bool(IP_DOMAIN_PATTERN.search(text))

    has_url = (
        https_present
        or shortener_used
        or ip_as_domain
        or bool(URL_GENERAL_PATTERN.search(text))
    )

    return {
        "has_url": bool(has_url),
        "shortener_used": bool(shortener_used),
        "ip_as_domain": bool(ip_as_domain),
        "https_present": bool(https_present),
    }


def extract_text_features(text: Any) -> Dict[str, Any]:
    """Extract linguistic and structural text features from input text.

    Args:
        text: Input string or text content.

    Returns:
        dict: {
            "length": int,
            "has_urgent_word": bool,
            "has_money_word": bool,
        }
    """
    if text is None:
        return {
            "length": 0,
            "has_urgent_word": False,
            "has_money_word": False,
        }

    text_str = str(text)
    length = len(text_str)
    has_urgent_word = bool(URGENT_PATTERN.search(text_str))
    has_money_word = bool(MONEY_PATTERN.search(text_str))

    return {
        "length": length,
        "has_urgent_word": has_urgent_word,
        "has_money_word": has_money_word,
    }


def build_tfidf_features(
    texts: List[str], max_features: int = 5000, **kwargs: Any
) -> Tuple[Any, TfidfVectorizer]:
    """Fit a TfidfVectorizer with ngram_range=(1, 2) on the provided texts.

    Args:
        texts: List of text strings to fit and transform.
        max_features: Maximum number of features for the vectorizer (default 5000).
        **kwargs: Optional additional keyword arguments forwarded to TfidfVectorizer.

    Returns:
        tuple: (features_matrix, fitted_vectorizer)
    """
    vectorizer_params = {
        "max_features": max_features,
        "ngram_range": (1, 2),
    }
    vectorizer_params.update(kwargs)

    vectorizer = TfidfVectorizer(**vectorizer_params)
    features = vectorizer.fit_transform(texts)
    return features, vectorizer


URL_REPLACEMENT_PATTERN = re.compile(
    r"(?:https?://|ftp://|www\.)[^\s<>{}\"']+"
    r"|(?:https?://)?(?:"
    + "|".join(re.escape(d) for d in sorted(SHORTENER_DOMAINS, key=len, reverse=True))
    + r")(?:/[^\s<>{}\"']*)?"
    r"|(?:https?://)?\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?:/[^\s<>{}\"']*)?"
    r"|\b[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|io|co|xyz|info|biz|cc|tv|me|site|online|top|club|vip|app|dev|tech)(?:/[^\s<>{}\"']*)?",
    re.IGNORECASE,
)

PHONE_AND_DIGITS_PATTERN = re.compile(
    r"(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}\b"
    r"|\b\d{5,}\b"
    r"|\d{5,}"
)

_NLTK_INITIALIZED = False
_STOPWORDS = None
_LEMMATIZER = None


def _ensure_nltk_resources() -> None:
    """Download required NLTK datasets on first use and initialize stopwords and lemmatizer."""
    global _NLTK_INITIALIZED, _STOPWORDS, _LEMMATIZER
    if _NLTK_INITIALIZED:
        return

    import nltk

    for resource in ("stopwords", "wordnet", "omw-1.4"):
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass

    try:
        from nltk.corpus import stopwords

        sw = set(stopwords.words("english"))
    except Exception:
        sw = set()

    # Scam signals that must be preserved
    scam_signals = {"now", "free", "win", "call", "stop", "urgent", "your", "you"}
    _STOPWORDS = sw - scam_signals

    try:
        from nltk.stem import WordNetLemmatizer

        _LEMMATIZER = WordNetLemmatizer()
    except Exception:
        _LEMMATIZER = None

    _NLTK_INITIALIZED = True


def preprocess_text(text: str) -> str:
    """Preprocess text by cleaning, replacing tokens, removing stopwords, and lemmatizing.

    Processing pipeline:
    1. Lowercase text.
    2. Replace URLs with the token 'urltoken'.
    3. Replace phone numbers and other digit runs of 5+ digits with 'numtoken'.
    4. Remove punctuation.
    5. Remove English stopwords using NLTK, but keep scam signal words:
       ('now', 'free', 'win', 'call', 'stop', 'urgent', 'your', 'you').
    6. Lemmatize remaining tokens using NLTK WordNetLemmatizer.

    Args:
        text: Input string to preprocess.

    Returns:
        str: Preprocessed string.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    _ensure_nltk_resources()

    # 1. Lowercase
    cleaned = text.lower()

    # 2. Replace URLs with 'urltoken'
    cleaned = URL_REPLACEMENT_PATTERN.sub("urltoken", cleaned)

    # 3. Replace phone numbers and digit runs of 5+ digits with 'numtoken'
    cleaned = PHONE_AND_DIGITS_PATTERN.sub("numtoken", cleaned)

    # 4. Remove punctuation
    cleaned = re.sub(r"[\W_]+", " ", cleaned)

    # 5. Remove English stopwords (keeping scam signals)
    tokens = cleaned.split()
    if _STOPWORDS is not None:
        tokens = [w for w in tokens if w not in _STOPWORDS]

    # 6. Lemmatize with WordNetLemmatizer
    if _LEMMATIZER is not None:
        tokens = [_LEMMATIZER.lemmatize(w) for w in tokens]

    return " ".join(tokens)
