"""Detailed feature analysis for the PhiUSIIL URL dataset."""

from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/processed/cleaned_url.csv")


def main():
    df = pd.read_csv(DATA_PATH)

    # ---------------------------------------------------------
    # Binary features
    # ---------------------------------------------------------
    binary_features = [
        column
        for column in df.columns
        if df[column].nunique() == 2
        and column != "label"
    ]

    print("=" * 70)
    print("BINARY FEATURE DISTRIBUTION BY CLASS")
    print("=" * 70)

    binary_summary = (
        df.groupby("label")[binary_features]
        .mean()
        .T
    )

    binary_summary.columns = [
        "Phishing_0",
        "Legitimate_1"
    ]

    binary_summary["Difference"] = (
        binary_summary["Legitimate_1"]
        - binary_summary["Phishing_0"]
    )

    print(
        binary_summary
        .sort_values(
            "Difference",
            key=abs,
            ascending=False
        )
        .to_string()
    )

    # ---------------------------------------------------------
    # Numeric feature quantiles by class
    # ---------------------------------------------------------
    numeric_features = [
        column
        for column in df.select_dtypes(
            include="number"
        ).columns
        if column != "label"
    ]

    print("\n" + "=" * 70)
    print("NUMERICAL FEATURE MEDIANS BY CLASS")
    print("=" * 70)

    median_summary = (
        df.groupby("label")[numeric_features]
        .median()
        .T
    )

    median_summary.columns = [
        "Phishing_0",
        "Legitimate_1"
    ]

    print(
        median_summary.to_string()
    )

    # ---------------------------------------------------------
    # Highly skewed numerical features
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("SKEWNESS")
    print("=" * 70)

    skewness = (
        df[numeric_features]
        .skew()
        .sort_values(
            key=abs,
            ascending=False
        )
    )

    print(skewness.to_string())


if __name__ == "__main__":
    main()