"""Categorize messages into scam subcategories and benign."""
import re
import sys
from pathlib import Path
import pandas as pd

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

INPUT_PATH = Path("data/processed/cleaned.csv")
OUTPUT_PATH = Path("data/processed/categorized.csv")

# Scam categories and their associated keywords
CATEGORY_KEYWORDS = {
    "prize_premium_scam": [
        "ringtone",
        "tone",
        "chat",
        "dating",
        "admirer",
        "txt",
        "reply",
        "club",
        "per msg",
        "rcvd",
        "landline",
        "win",
        "won",
        "winner",
        "prize",
        "draw",
        "congratulations",
        "claim",
    ],
    "free_offer_scam": [
        "free",
        "upgrade",
        "upto",
        "mobile",
        "camera",
        "minutes",
        "entitled",
    ],
    "payment_scam": [
        "gov",
        "payment",
        "covid",
        "tap here",
        "apply",
        "bank",
        "account",
        "verify",
        "suspended",
    ],
}

# Compile regex patterns with word boundaries for accurate matching
CATEGORY_PATTERNS = {
    category: re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b",
        re.IGNORECASE,
    )
    for category, keywords in CATEGORY_KEYWORDS.items()
}


def assign_category(text: str, label: str) -> str:
    """Assign a category based on label and keyword/regex matching."""
    norm_label = str(label).strip().lower()
    if norm_label != "malicious":
        return "benign"

    text_str = str(text)
    for category, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(text_str):
            return category

    return "other_scam"


def categorize(
    input_path: Path = INPUT_PATH, output_path: Path = OUTPUT_PATH
) -> pd.DataFrame:
    """Load cleaned dataset, categorize messages, save, and print distribution."""
    if not input_path.exists():
        raise FileNotFoundError(
            f"{input_path} not found. Run cleaning/splitting first."
        )

    df = pd.read_csv(input_path)

    df["category"] = [
        assign_category(t, l) for t, l in zip(df["text"], df["label"])
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print("Category distribution:")
    print(df["category"].value_counts())
    print(f"\nSaved categorized dataset to: {output_path}")

    return df


if __name__ == "__main__":
    categorize()
