"""Exploratory data analysis for the PhiUSIIL URL dataset."""

from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/processed/cleaned_url.csv")


def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run clean_url.py first."
        )

    return pd.read_csv(DATA_PATH)


def main():
    df = load_data()

    print("=" * 60)
    print("PHIUSIIL URL DATASET - EDA")
    print("=" * 60)

    # ---------------------------------------------------------
    # Dataset overview
    # ---------------------------------------------------------
    print("\nDataset shape:")
    print(df.shape)

    print("\nNumber of columns:")
    print(len(df.columns))

    # ---------------------------------------------------------
    # Data types
    # ---------------------------------------------------------
    print("\nData types:")
    print(df.dtypes.value_counts())

    # ---------------------------------------------------------
    # Label distribution
    # ---------------------------------------------------------
    print("\nLabel distribution:")
    print(df["label"].value_counts())

    print("\nLabel proportions:")
    print(
        df["label"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    # ---------------------------------------------------------
    # Missing values
    # ---------------------------------------------------------
    print("\nTotal missing values:")
    print(df.isnull().sum().sum())

    # ---------------------------------------------------------
    # Duplicate checks
    # ---------------------------------------------------------
    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    print("\nDuplicate URLs:")
    print(df["URL"].duplicated().sum())

    # ---------------------------------------------------------
    # Unique values
    # ---------------------------------------------------------
    print("\nUnique values:")
    for column in ["URL", "Domain", "TLD", "Title"]:
        print(
            f"{column}: "
            f"{df[column].nunique():,}"
        )

    # ---------------------------------------------------------
    # Numerical features
    # ---------------------------------------------------------
    numerical_columns = df.select_dtypes(
        include="number"
    ).columns

    print("\nNumerical features:")
    print(list(numerical_columns))

    # ---------------------------------------------------------
    # Descriptive statistics
    # ---------------------------------------------------------
    print("\nDescriptive statistics:")
    print(
        df[numerical_columns]
        .describe()
        .T
        .to_string()
    )

    # ---------------------------------------------------------
    # Constant columns
    # ---------------------------------------------------------
    print("\nConstant columns:")

    constant_columns = [
        column
        for column in df.columns
        if df[column].nunique() <= 1
    ]

    if constant_columns:
        print(constant_columns)
    else:
        print("None")

    # ---------------------------------------------------------
    # Low-cardinality columns
    # ---------------------------------------------------------
    print("\nLow-cardinality columns:")

    for column in df.columns:
        unique_count = df[column].nunique()

        if unique_count <= 10:
            print(
                f"{column}: "
                f"{unique_count} unique values"
            )

    # ---------------------------------------------------------
    # Feature correlation with label
    # ---------------------------------------------------------
    print("\nCorrelation with label:")

    correlations = (
        df[numerical_columns]
        .corr()["label"]
        .drop("label")
        .sort_values(
            key=abs,
            ascending=False
        )
    )

    print(correlations.to_string())

    # ---------------------------------------------------------
    # Phishing vs legitimate means
    # ---------------------------------------------------------
    print("\nMean feature values by label:")

    means = (
        df[numerical_columns]
        .groupby(df["label"])
        .mean()
        .T
    )

    print(means.to_string())

    # ---------------------------------------------------------
    # Save numerical summary
    # ---------------------------------------------------------
    output_path = Path("reports/url_eda_summary.csv")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    correlations.to_csv(
        output_path,
        header=["correlation_with_label"]
    )

    print(
        f"\nCorrelation summary saved to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()