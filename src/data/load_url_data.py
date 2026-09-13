"""Load and inspect the phishing URL dataset."""

from pathlib import Path
import pandas as pd
import numpy as np


RAW_PATH = Path("data/raw/PhiUSIIL_Phishing_URL_Dataset.csv")


def load_url_data(path: Path = RAW_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Place the PhiUSIIL dataset in data/raw/."
        )

    df = pd.read_csv(path)

    # Standardize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    return df


if __name__ == "__main__":
    df = load_url_data()

    print("Dataset shape:", df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes)

    print("\nMissing values:")
    print(df.isnull().sum())

    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    print("\nFirst 5 rows:")
    print(df.head())

    