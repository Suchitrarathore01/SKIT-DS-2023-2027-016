# ChainShield ML Pipeline & EDA Report

This report summarizes the exploratory data analysis (EDA), data cleaning results, and dataset split for the ChainShield smishing detection pipeline.

---

## Exploratory Data Analysis (EDA)

### Class Balance

Initial raw dataset consists of 5,574 total rows distributed across two classes:

| Class | Count | Percentage |
|---|---|---|
| ham | 4,827 | 86.60% |
| spam | 747 | 13.40% |
| **Total** | **5,574** | **100.0%** |

```
label
ham     4827
spam     747
Name: count, dtype: int64
Total rows: 5574
```

![Class Balance](class_balance.png)

### Message Length Distribution

Summary statistics for message character length by class:

| Class | Count | Mean | Std | Min | 25% | 50% | 75% | Max |
|---|---|---|---|---|---|---|---|---|
| ham | 4827.0 | 71.440232 | 58.321812 | 2.0 | 33.0 | 52.0 | 93.0 | 910.0 |
| spam | 747.0 | 138.634538 | 28.854103 | 13.0 | 133.0 | 149.0 | 157.0 | 223.0 |

Detailed statistics table:
```
        count        mean        std   min    25%    50%    75%    max
label                                                                 
ham    4827.0   71.440232  58.321812   2.0   33.0   52.0   93.0  910.0
spam    747.0  138.634538  28.854103  13.0  133.0  149.0  157.0  223.0
```

Raw pandas summary from initial EDA run:
```
        count  ...    max
label          ...       
ham    4827.0  ...  910.0
spam    747.0  ...  223.0

[2 rows x 8 columns]
```

![Message Length Distribution](length_distribution.png)

### URL Presence Rate

Proportion of messages containing a URL (`http[s]?://` or `www.`):

| Class | URL Presence Rate |
|---|---|
| ham | 0.000414 (0.04%) |
| spam | 0.139224 (13.92%) |

```
label
ham     0.000414
spam    0.139224
Name: has_url, dtype: float64
```

### Duplicate Messages

- Exact duplicate messages: 415

```
=== Exact duplicate messages: 415 ===
```

### Top 15 Words per Class

Most frequent words per class after filtering punctuation and standard stopwords:

#### Ham Top 15 Words

| Rank | Word | Frequency |
|---|---|---|
| 1 | u | 982 |
| 2 | me | 760 |
| 3 | my | 746 |
| 4 | *(empty string / stripped punctuation)* | 739 |
| 5 | that | 486 |
| 6 | have | 439 |
| 7 | but | 424 |
| 8 | so | 411 |
| 9 | not | 411 |
| 10 | are | 410 |
| 11 | at | 379 |
| 12 | do | 378 |
| 13 | can | 376 |
| 14 | i'm | 369 |
| 15 | if | 351 |

```
-- ham --
u       982
me      760
my      746
        739
that    486
have    439
but     424
so      411
not     411
are     410
at      379
do      378
can     376
i'm     369
if      351
Name: count, dtype: int64
```

#### Spam Top 15 Words

| Rank | Word | Frequency |
|---|---|---|
| 1 | call | 345 |
| 2 | free | 214 |
| 3 | now | 189 |
| 4 | or | 188 |
| 5 | 2 | 171 |
| 6 | txt | 147 |
| 7 | u | 147 |
| 8 | ur | 144 |
| 9 | have | 135 |
| 10 | from | 128 |
| 11 | mobile | 123 |
| 12 | text | 120 |
| 13 | stop | 115 |
| 14 | claim | 113 |
| 15 | with | 109 |

```
-- spam --
call      345
free      214
now       189
or        188
2         171
txt       147
u         147
ur        144
have      135
from      128
mobile    123
text      120
stop      115
claim     113
with      109
Name: count, dtype: int64
```

---

## Cleaning Results

The raw dataset underwent text normalization (lowercasing, whitespace collapse), label standardization (`ham` -> `benign`, `spam` -> `malicious`), exact deduplication, and near-duplicate removal:

- **Exact duplicates removed:** 416
- **Near-duplicates removed:** 20
- **Final row count:** 5,138
- **Class distribution:**
  - benign: 4,512 (87.8%)
  - malicious: 626 (12.2%)

| Label | Count | Percentage |
|---|---|---|
| benign | 4,512 | 87.8% |
| malicious | 626 | 12.2% |
| **Total** | **5,138** | **100.0%** |

---

## Train/Val/Test Split

The cleaned dataset was partitioned using a stratified 70/15/15 split:

- **Split Configuration:** Stratified 70/15/15 split with `random_state=42`
- **Partitions:**
  - train: 3,596 (70%)
  - val: 771 (15%)
  - test: 771 (15%)
- **Leakage check:** Passed with no overlapping messages across splits (verified via MD5 hashes across train, val, and test).

| Split | Rows | Percentage |
|---|---|---|
| Train | 3,596 | 70.0% |
| Validation | 771 | 15.0% |
| Test | 771 | 15.0% |
| **Total** | **5,138** | **100.0%** |
