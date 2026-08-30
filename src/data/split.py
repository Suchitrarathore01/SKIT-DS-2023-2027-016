"""Stratified train/val/test split with a leakage check."""
import hashlib
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

PROCESSED_PATH = Path("data/processed/cleaned.csv")
OUT_DIR = Path("data/processed")
SEED = 42


def split():
    df = pd.read_csv(PROCESSED_PATH)

    train, temp = train_test_split(
        df, test_size=0.30, stratify=df["label"], random_state=SEED
    )
    val, test = train_test_split(
        temp, test_size=0.50, stratify=temp["label"], random_state=SEED
    )

    train.to_csv(OUT_DIR / "train.csv", index=False)
    val.to_csv(OUT_DIR / "val.csv", index=False)
    test.to_csv(OUT_DIR / "test.csv", index=False)

    print(f"train: {len(train)}  val: {len(val)}  test: {len(test)}")
    leakage_check()


def _hash_set(df: pd.DataFrame) -> set:
    return set(hashlib.md5(t.encode()).hexdigest() for t in df["text"])


def leakage_check():
    train = pd.read_csv(OUT_DIR / "train.csv")
    val = pd.read_csv(OUT_DIR / "val.csv")
    test = pd.read_csv(OUT_DIR / "test.csv")

    h_train, h_val, h_test = _hash_set(train), _hash_set(val), _hash_set(test)
    overlap = (h_train & h_val) | (h_train & h_test) | (h_val & h_test)

    assert len(overlap) == 0, f"Leakage detected: {len(overlap)} overlapping messages across splits!"
    print("Leakage check passed: no overlapping messages across train/val/test.")


if __name__ == "__main__":
    split()
