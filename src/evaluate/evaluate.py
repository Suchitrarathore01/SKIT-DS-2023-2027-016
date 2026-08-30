"""Compare baseline vs DistilBERT results and write a markdown report."""
from pathlib import Path
import pandas as pd

EXPERIMENTS_PATH = Path("experiments.csv")
REPORT_PATH = Path("reports/comparison_report.md")


def evaluate():
    if not EXPERIMENTS_PATH.exists():
        print("No experiments.csv found yet. Run train_baseline.py first.")
        return

    df = pd.read_csv(EXPERIMENTS_PATH)
    df_sorted = df.sort_values("macro_f1", ascending=False)

    lines = ["# Model Comparison Report\n", df_sorted.to_markdown(index=False)]
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved to {REPORT_PATH}")


if __name__ == "__main__":
    evaluate()
