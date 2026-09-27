"""Correlation analysis for URL-level features."""

from pathlib import Path

import pandas as pd


DATA_PATH = Path("data/processed/cleaned_url.csv")


URL_FEATURES = [
    "URLLength",
    "DomainLength",
    "IsDomainIP",
    "TLDLength",
    "NoOfSubDomain",
    "HasObfuscation",
    "NoOfObfuscatedChar",
    "ObfuscationRatio",
    "NoOfLettersInURL",
    "LetterRatioInURL",
    "NoOfDegitsInURL",
    "DegitRatioInURL",
    "NoOfEqualsInURL",
    "NoOfQMarkInURL",
    "NoOfAmpersandInURL",
    "NoOfOtherSpecialCharsInURL",
    "SpacialCharRatioInURL",
    "IsHTTPS",
    "URLSimilarityIndex",
    "CharContinuationRate",
    "TLDLegitimateProb",
    "URLCharProb",
]


def main():
    df = pd.read_csv(DATA_PATH)

    corr = df[URL_FEATURES].corr()

    print("=" * 70)
    print("URL FEATURE CORRELATION MATRIX")
    print("=" * 70)

    print(corr.round(2).to_string())

    print("\n" + "=" * 70)
    print("HIGHLY CORRELATED FEATURE PAIRS (|r| >= 0.80)")
    print("=" * 70)

    pairs = []

    for i in range(len(URL_FEATURES)):
        for j in range(i + 1, len(URL_FEATURES)):

            feature_1 = URL_FEATURES[i]
            feature_2 = URL_FEATURES[j]

            value = corr.loc[
                feature_1,
                feature_2
            ]

            if abs(value) >= 0.80:
                pairs.append(
                    (
                        feature_1,
                        feature_2,
                        value
                    )
                )

    if pairs:
        for feature_1, feature_2, value in sorted(
            pairs,
            key=lambda x: abs(x[2]),
            reverse=True
        ):
            print(
                f"{feature_1:30s} "
                f"{feature_2:30s} "
                f"{value:.3f}"
            )
    else:
        print("No feature pairs found.")


if __name__ == "__main__":
    main()