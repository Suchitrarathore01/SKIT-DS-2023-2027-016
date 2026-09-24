"""Clean the smish dataset: normalize text, dedupe, standardize labels."""
import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

from src.data.load_data import load_raw

PROCESSED_PATH = Path("data/processed/cleaned.csv")

LABEL_MAP = {
    "ham": "benign", "spam": "malicious", "smishing": "malicious",
    "phishing": "malicious", "0": "benign", "1": "malicious",
}


def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def standardize_label(label: str) -> str:
    key = str(label).strip().lower()
    return LABEL_MAP.get(key, key)


def near_duplicate_mask(texts: pd.Series, threshold: int = 92) -> pd.Series:
    """Flags near-duplicate rows (keeps the first occurrence)."""
    seen = []
    flags = []
    for t in texts:
        is_dupe = any(fuzz.ratio(t, s) >= threshold for s in seen[-200:])  # window for speed
        flags.append(is_dupe)
        if not is_dupe:
            seen.append(t)
    return pd.Series(flags, index=texts.index)


def clean():
    df = load_raw()
    df["text"] = df["text"].apply(normalize_text)
    df["label"] = df["label"].apply(standardize_label)

    before = len(df)
    df = df.drop_duplicates(subset=["text"])
    exact_removed = before - len(df)

    dupe_mask = near_duplicate_mask(df["text"])
    df = df[~dupe_mask].reset_index(drop=True)

    df = df[df["text"].str.len() > 0].reset_index(drop=True)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Exact duplicates removed: {exact_removed}")
    print(f"Near-duplicates removed: {dupe_mask.sum()}")
    print(f"Final row count: {len(df)}")
    print(df["label"].value_counts())
    print(f"Saved to {PROCESSED_PATH}")


if __name__ == "__main__":
    clean()
