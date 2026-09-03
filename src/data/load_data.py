"""Load the raw smish dataset and standardize column names."""
import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw/smish.csv")


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Place your smish.csv into data/raw/ first."
        )
    df = pd.read_csv(path, encoding="utf-8-sig")

    # Strip BOM characters and whitespace from column names
    df.columns = [
        str(c).replace("\ufeff", "").replace("ï»¿", "").strip()
        for c in df.columns
    ]

    # Try to auto-detect text/label columns for common Kaggle SMS formats
    cols_lower = {c.lower(): c for c in df.columns}
    text_col = next((cols_lower[c] for c in ["text", "message", "v2", "sms"] if c in cols_lower), None)
    label_col = next((cols_lower[c] for c in ["label", "category", "v1", "class"] if c in cols_lower), None)

    if text_col is None or label_col is None:
        raise ValueError(
            f"Could not auto-detect text/label columns. Found columns: {list(df.columns)}. "
            f"Edit load_data.py to map them manually."
        )

    df = df[[text_col, label_col]].rename(columns={text_col: "text", label_col: "label"})
    df = df.dropna(subset=["text", "label"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    data = load_raw()
    print(f"Loaded {len(data)} rows")
    print(data["label"].value_counts())
    print(data.head())
