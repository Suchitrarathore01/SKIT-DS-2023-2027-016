"""Train baseline models (LogisticRegression and LinearSVC) on category prediction.

Features:
- Scales handcrafted features with MaxAbsScaler (fit on train, applied to val).
- Evaluates raw text vs NLP-preprocessed text combined with TF-IDF (1, 2) and handcrafted features.
- Trains LogisticRegression and LinearSVC with max_iter=5000 and class_weight='balanced'.
- Runs single train/val evaluation with per-category reports (zero_division=0).
- Runs 5-fold Stratified Cross-Validation on train+val combined (never test.csv).
- Computes binary benign-vs-malicious metrics (collapsing scam categories to 'malicious').
- Logs all results to experiments.csv.
"""
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import MaxAbsScaler
from sklearn.svm import LinearSVC

from src.features import extract_text_features, extract_url_features, preprocess_text

DATA_DIR = Path("data/processed")
EXPERIMENTS_PATH = Path("experiments.csv")
RANDOM_STATE = 42


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load train.csv and val.csv from data/processed."""
    train_df = pd.read_csv(DATA_DIR / "train.csv")
    val_df = pd.read_csv(DATA_DIR / "val.csv")
    return train_df, val_df


def extract_handcrafted_features(texts: Iterable[str]) -> np.ndarray:
    """Extract 7-dimensional handcrafted features for a sequence of texts."""
    feature_rows = []
    for text in texts:
        url_feats = extract_url_features(text)
        text_feats = extract_text_features(text)
        row = [
            int(url_feats["has_url"]),
            int(url_feats["shortener_used"]),
            int(url_feats["ip_as_domain"]),
            int(url_feats["https_present"]),
            float(text_feats["length"]),
            int(text_feats["has_urgent_word"]),
            int(text_feats["has_money_word"]),
        ]
        feature_rows.append(row)
    return np.array(feature_rows, dtype=float)


def to_binary_labels(series: pd.Series) -> pd.Series:
    """Collapse 4 scam categories into 'malicious', keeping 'benign'."""
    return series.apply(lambda c: "benign" if c == "benign" else "malicious")


def log_experiment(row_data: Dict[str, Any]) -> None:
    """Append one row to experiments.csv, writing headers if newly created."""
    df = pd.DataFrame([row_data])
    if EXPERIMENTS_PATH.exists():
        existing_cols = list(pd.read_csv(EXPERIMENTS_PATH, nrows=0).columns)
        if existing_cols == list(df.columns):
            df.to_csv(EXPERIMENTS_PATH, mode="a", header=False, index=False)
            return
    df.to_csv(EXPERIMENTS_PATH, index=False)


def run_stratified_cv(
    combined_texts: pd.Series,
    combined_hc: np.ndarray,
    combined_y: pd.Series,
    model_template: Any,
    n_splits: int = 5,
) -> Tuple[float, float, float, float]:
    """Run 5-fold Stratified Cross-Validation on train+val combined."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    fold_accs = []
    fold_macro_f1s = []

    for fold_train_idx, fold_val_idx in skf.split(combined_texts, combined_y):
        # 1. TF-IDF
        vec = TfidfVectorizer(ngram_range=(1, 2))
        X_tr_tfidf = vec.fit_transform(combined_texts.iloc[fold_train_idx])
        X_val_tfidf = vec.transform(combined_texts.iloc[fold_val_idx])

        # 2. Scale handcrafted features using MaxAbsScaler (fit on train only)
        scaler = MaxAbsScaler()
        X_tr_hc = scaler.fit_transform(combined_hc[fold_train_idx])
        X_val_hc = scaler.transform(combined_hc[fold_val_idx])

        # 3. Combine
        X_tr = hstack([X_tr_tfidf, X_tr_hc])
        X_val = hstack([X_val_tfidf, X_val_hc])

        # 4. Train & Evaluate
        clf = clone(model_template)
        clf.fit(X_tr, combined_y.iloc[fold_train_idx])
        preds = clf.predict(X_val)

        fold_accs.append(accuracy_score(combined_y.iloc[fold_val_idx], preds))
        fold_macro_f1s.append(
            f1_score(
                combined_y.iloc[fold_val_idx],
                preds,
                average="macro",
                zero_division=0,
            )
        )

    return (
        float(np.mean(fold_accs)),
        float(np.std(fold_accs)),
        float(np.mean(fold_macro_f1s)),
        float(np.std(fold_macro_f1s)),
    )


def train_baseline():
    train_df, val_df = load_data()
    combined_df = pd.concat([train_df, val_df], ignore_index=True)

    y_train = train_df["category"]
    y_val = val_df["category"]
    y_combined = combined_df["category"]

    majority_class = y_val.mode()[0]
    majority_acc = (y_val == majority_class).mean()
    print(f"Majority-class baseline ('{majority_class}') accuracy: {majority_acc:.4f}\n")

    # Clear previous experiments.csv to log fresh complete run
    if EXPERIMENTS_PATH.exists():
        EXPERIMENTS_PATH.unlink()

    experiments = [
        ("raw", train_df["text"], val_df["text"], combined_df["text"]),
        (
            "nlp",
            train_df["text"].apply(preprocess_text),
            val_df["text"].apply(preprocess_text),
            combined_df["text"].apply(preprocess_text),
        ),
    ]

    models = {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=5000, random_state=RANDOM_STATE
        ),
        "linear_svc": LinearSVC(
            class_weight="balanced", max_iter=5000, random_state=RANDOM_STATE
        ),
    }

    for prep_name, X_train_text, X_val_text, X_comb_text in experiments:
        print(f"\n{'='*70}")
        print(f">>> Preprocessing: {prep_name.upper()} <<<")
        print(f"{'='*70}")

        # 1. Build TF-IDF (ngram_range=(1, 2))
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        X_train_tfidf = vectorizer.fit_transform(X_train_text)
        X_val_tfidf = vectorizer.transform(X_val_text)

        # 2. Extract handcrafted features
        X_train_hc_raw = extract_handcrafted_features(X_train_text)
        X_val_hc_raw = extract_handcrafted_features(X_val_text)
        X_comb_hc_raw = extract_handcrafted_features(X_comb_text)

        # 3. Scale handcrafted features with MaxAbsScaler (fit on train only)
        scaler = MaxAbsScaler()
        X_train_hc_scaled = scaler.fit_transform(X_train_hc_raw)
        X_val_hc_scaled = scaler.transform(X_val_hc_raw)

        # 4. Hstack TF-IDF and scaled handcrafted features
        X_train = hstack([X_train_tfidf, X_train_hc_scaled])
        X_val = hstack([X_val_tfidf, X_val_hc_scaled])

        for model_name, model in models.items():
            print(f"\n-------------------------------------------------------")
            print(f"Evaluating Model: {model_name} | Preprocessing: {prep_name}")
            print(f"-------------------------------------------------------")

            # --- A. Single Train / Val Evaluation ---
            model.fit(X_train, y_train)
            preds = model.predict(X_val)

            acc = accuracy_score(y_val, preds)
            macro_f1 = f1_score(y_val, preds, average="macro", zero_division=0)
            weighted_f1 = f1_score(y_val, preds, average="weighted", zero_division=0)
            report = classification_report(y_val, preds, zero_division=0)

            # --- B. Binary Benign vs Malicious Evaluation ---
            y_val_bin = to_binary_labels(y_val)
            preds_bin = to_binary_labels(pd.Series(preds, index=y_val.index))
            bin_prec = precision_score(y_val_bin, preds_bin, pos_label="malicious", zero_division=0)
            bin_rec = recall_score(y_val_bin, preds_bin, pos_label="malicious", zero_division=0)
            bin_f1 = f1_score(y_val_bin, preds_bin, pos_label="malicious", zero_division=0)

            # --- C. 5-Fold Stratified Cross-Validation on train+val combined ---
            cv_acc_mean, cv_acc_std, cv_f1_mean, cv_f1_std = run_stratified_cv(
                combined_texts=X_comb_text,
                combined_hc=X_comb_hc_raw,
                combined_y=y_combined,
                model_template=model,
                n_splits=5,
            )

            # Print All Metrics
            print(f"Validation Accuracy:    {acc:.4f}")
            print(f"Validation Macro-F1:    {macro_f1:.4f}")
            print(f"Validation Weighted-F1: {weighted_f1:.4f}")
            print(f"\nBinary (Benign vs Malicious) Metrics:")
            print(f"  Precision: {bin_prec:.4f}")
            print(f"  Recall:    {bin_rec:.4f}")
            print(f"  F1-Score:  {bin_f1:.4f}")
            print(f"\n5-Fold Stratified Cross-Validation (train+val combined):")
            print(f"  CV Accuracy: {cv_acc_mean:.4f} \u00b1 {cv_acc_std:.4f}")
            print(f"  CV Macro-F1: {cv_f1_mean:.4f} \u00b1 {cv_f1_std:.4f}")
            print("\nPer-Category Classification Report:")
            print(report)

            # Log to experiments.csv
            log_experiment(
                {
                    "model": model_name,
                    "preprocessing": prep_name,
                    "accuracy": acc,
                    "macro_f1": macro_f1,
                    "weighted_f1": weighted_f1,
                    "cv_accuracy_mean": cv_acc_mean,
                    "cv_accuracy_std": cv_acc_std,
                    "cv_macro_f1_mean": cv_f1_mean,
                    "cv_macro_f1_std": cv_f1_std,
                    "binary_precision": bin_prec,
                    "binary_recall": bin_rec,
                    "binary_f1": bin_f1,
                }
            )

    print(f"\nAll experiments successfully logged to {EXPERIMENTS_PATH}")


if __name__ == "__main__":
    train_baseline()

