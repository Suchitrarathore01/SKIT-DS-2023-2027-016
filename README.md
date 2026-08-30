# Smish — Smishing Detection: EDA + ML Pipeline

Dataset: `data/raw/smish.csv` (place your file here — not committed, see `.gitignore`).
Expected columns: `text` (the SMS content) and `label` (spam/ham or category — see `src/data/load_data.py`).

## Setup
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Place `smish.csv` into `data/raw/`.

## Run order
```bash
python -m src.eda.run_eda
python -m src.data.clean
python -m src.data.split
python -m src.training.train_baseline
# DistilBERT fine-tuning: run src/training/train_distilbert.py on Kaggle (GPU),
# then place the downloaded models/model_v1/ folder back here.
python -m src.evaluate.evaluate
```

## Structure
```
src/data/       -> load, clean, split
src/eda/        -> exploratory data analysis, reports
src/training/   -> baseline + DistilBERT training
src/evaluate/   -> comparison report
reports/        -> EDA charts + evaluation report (generated, not committed if large)
models/         -> trained model folders + metadata.json (weights not committed)
```

## Status
- [ ] EDA complete
- [ ] Cleaning complete
- [ ] Split + leakage check complete
- [ ] Baseline trained
- [ ] DistilBERT trained (Kaggle)
- [ ] Evaluation report complete
