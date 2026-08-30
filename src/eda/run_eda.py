"""Exploratory data analysis on the smish dataset. Outputs charts + a text report to reports/."""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.data.load_data import load_raw

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

URL_PATTERN = re.compile(r"http[s]?://|www\.")


def run_eda():
    df = load_raw()
    lines = []

    # 1. Class balance
    counts = df["label"].value_counts()
    lines.append("=== Class balance ===")
    lines.append(str(counts))
    lines.append(f"Total rows: {len(df)}")

    fig, ax = plt.subplots()
    counts.plot(kind="bar", ax=ax)
    ax.set_title("Class balance")
    fig.savefig(REPORT_DIR / "class_balance.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Message length distribution
    df["msg_len"] = df["text"].str.len()
    lines.append("\n=== Message length by class ===")
    lines.append(str(df.groupby("label")["msg_len"].describe()))

    fig, ax = plt.subplots()
    for label, group in df.groupby("label"):
        ax.hist(group["msg_len"], bins=40, alpha=0.6, label=str(label))
    ax.set_title("Message length distribution by class")
    ax.set_xlabel("characters")
    ax.legend()
    fig.savefig(REPORT_DIR / "length_distribution.png", bbox_inches="tight")
    plt.close(fig)

    # 3. URL presence rate by class
    df["has_url"] = df["text"].str.contains(URL_PATTERN, regex=True, na=False)
    url_rate = df.groupby("label")["has_url"].mean()
    lines.append("\n=== URL presence rate by class ===")
    lines.append(str(url_rate))

    # 4. Duplicate check
    n_exact_dupes = df.duplicated(subset=["text"]).sum()
    lines.append(f"\n=== Exact duplicate messages: {n_exact_dupes} ===")

    # 5. Most common words per class (simple, no stopword removal library dependency)
    stopwords = {"the", "a", "to", "you", "your", "and", "is", "for", "of", "in", "on", "i", "it"}
    lines.append("\n=== Top 15 words per class ===")
    for label, group in df.groupby("label"):
        words = " ".join(group["text"].str.lower()).split()
        words = [w.strip(".,!?:;\"'") for w in words if w.strip(".,!?:;\"'") not in stopwords]
        top = pd.Series(words).value_counts().head(15)
        lines.append(f"\n-- {label} --")
        lines.append(str(top))

    report_text = "\n".join(lines)
    (REPORT_DIR / "eda_report.txt").write_text(report_text)
    print(report_text)
    print(f"\nCharts saved to {REPORT_DIR}/")


if __name__ == "__main__":
    run_eda()
