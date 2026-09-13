"""Clean the PhiUSIIL phishing URL dataset."""

from pathlib import Path

import pandas as pd

from src.data.load_url_data import load_url_data


RAW_PATH = Path("data/raw/PhiUSIIL_Phishing_URL_Dataset.csv")
OUTPUT_PATH = Path("data/processed/cleaned_url.csv")


def clean_url_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply basic cleaning to the phishing URL dataset."""

    df = df.copy()

    # ---------------------------------------------------------
    # 1. Remove identifier column
    # ---------------------------------------------------------
    if "FILENAME" in df.columns:
        df = df.drop(columns=["FILENAME"])

    # ---------------------------------------------------------
    # 2. Remove rows with missing URL or label
    # ---------------------------------------------------------
    df = df.dropna(subset=["URL", "label"])

    # ---------------------------------------------------------
    # 3. Remove exact duplicate URLs
    # ---------------------------------------------------------
    before = len(df)

    df = df.drop_duplicates(
        subset=["URL"],
        keep="first"
    )

    removed = before - len(df)

    print(f"Duplicate URLs removed: {removed}")

    # ---------------------------------------------------------
    # 4. Normalize URL and Domain whitespace
    # ---------------------------------------------------------
    df["URL"] = df["URL"].astype(str).str.strip()

    if "Domain" in df.columns:
        df["Domain"] = df["Domain"].astype(str).str.strip()

    # ---------------------------------------------------------
    # 5. Validate labels
    # ---------------------------------------------------------
    valid_labels = {0, 1}

    invalid_labels = set(df["label"].unique()) - valid_labels

    if invalid_labels:
        raise ValueError(
            f"Unexpected label values found: {invalid_labels}"
        )

    df["label"] = df["label"].astype(int)

    return df


def main():
    """Load, clean and save the URL dataset."""

    df = load_url_data(RAW_PATH)

    print("Original shape:", df.shape)

    cleaned_df = clean_url_data(df)

    print("Cleaned shape:", cleaned_df.shape)

    print("\nLabel distribution:")
    print(cleaned_df["label"].value_counts())

    print("\nLabel proportions:")
    print(cleaned_df["label"].value_counts(normalize=True))

    print("\nDuplicate URLs after cleaning:",
          cleaned_df["URL"].duplicated().sum())

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cleaned_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(f"\nSaved cleaned dataset to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()