"""Merge GitHub SMS dataset with UCI smish dataset."""
import sys
from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load_data import load_raw

UCI_PATH = Path("data/raw/smish.csv")
GITHUB_RAW_PATH = Path("data/raw/github_sms_raw.csv")
OUTPUT_PATH = Path("data/raw/smish_combined.csv")


def load_github(path: Path = GITHUB_RAW_PATH) -> pd.DataFrame:
    """Load GitHub dataset, filter English messages, and standardize labels."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")

    df = pd.read_csv(path, low_memory=False)

    # Keep only columns label, text, lang
    df = df[["label", "text", "lang"]]

    # Filter rows where lang equals 'en' OR 'english'
    lang_clean = df["lang"].astype(str).str.strip().str.lower()
    df = df[lang_clean.isin(["en", "english"])].copy()

    # Drop lang column after filtering
    df = df.drop(columns=["lang"])

    # Standardize label column to lowercase (so 'Spam' and 'spam' become the same value)
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df["text"] = df["text"].astype(str)
    df = df.dropna(subset=["text", "label"]).reset_index(drop=True)

    return df


def near_duplicate_mask(texts: pd.Series, threshold: int = 92) -> pd.Series:
    """Flags near-duplicate rows using rapidfuzz ratio (keeps the first occurrence)."""
    seen = []
    flags = []
    for t in texts:
        is_dupe = any(fuzz.ratio(t, s) >= threshold for s in seen[-200:])  # window for speed
        flags.append(is_dupe)
        if not is_dupe:
            seen.append(t)
    return pd.Series(flags, index=texts.index)


def merge_datasets() -> pd.DataFrame:
    # 1. Load GitHub dataset (English-only, standardized)
    df_github = load_github(GITHUB_RAW_PATH)
    count_github = len(df_github)

    # 2. Load UCI source using load_data.py approach
    df_uci = load_raw(UCI_PATH)
    df_uci["label"] = df_uci["label"].astype(str).str.strip().str.lower()
    df_uci["text"] = df_uci["text"].astype(str)
    count_uci = len(df_uci)

    # 3. Concatenate both into one DataFrame with columns text, label
    combined = pd.concat([df_uci[["text", "label"]], df_github[["text", "label"]]], ignore_index=True)

    # 4. Deduplication: exact duplicates and near-duplicates
    deduped = combined.drop_duplicates(subset=["text"]).reset_index(drop=True)

    dupe_mask = near_duplicate_mask(deduped["text"], threshold=92)
    final_df = deduped[~dupe_mask].reset_index(drop=True)
    final_df = final_df[final_df["text"].str.strip().str.len() > 0].reset_index(drop=True)
    count_after_dedup = len(final_df)

    # 5. Save result to data/raw/smish_combined.csv
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(OUTPUT_PATH, index=False)

    # 6. Print required metrics
    print(f"Row count from UCI source: {count_uci}")
    print(f"Row count from GitHub source (English-only, after label standardization): {count_github}")
    print(f"Row count after deduplication: {count_after_dedup}")
    print("Final label balance:")
    print(final_df["label"].value_counts())
    print(f"Saved merged dataset to: {OUTPUT_PATH}")

    return final_df


if __name__ == "__main__":
    merge_datasets()
