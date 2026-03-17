"""
train_models.py — VeriNews Model Training Script

Uses JSONL dataset from Dataset/ folder.
Strategy:
  - Load headlines + reasons from JSONL files
  - importance_score >= 40  → REAL  (credible/verifiable content)
  - importance_score < 40   → FAKE  (noise, low-value, unverifiable)
  - Supplement with a hardcoded seed set for robustness
  - Train TF-IDF (max_features=10000, ngram(1,2)) + LR + NB
  - Save to models/
"""
import os
import json
import glob
import re
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")
MODELS_DIR  = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Seed data for binary classifier (balanced representative samples) ─────────
SEED_REAL = [
    "Scientists confirm new vaccine shows 95% efficacy in Phase 3 clinical trials",
    "Central bank raises interest rates by 0.25% to curb inflation",
    "Court documents reveal financial transactions between defendants",
    "Government releases quarterly GDP growth report showing 2.1% increase",
    "Hospital reports breakthrough surgery using robotic assistance",
    "Election results certified after independent audit confirms accuracy",
    "Pharmaceutical company recalls batch of medication citing contamination risk",
    "United Nations approves humanitarian aid package for conflict region",
    "Environmental agency records highest CO2 levels in a decade",
    "Police arrest suspect in connection with series of bank robberies",
    "Local council votes to approve new public transport infrastructure",
    "University research published in Nature journal confirms earlier findings",
    "Stock market closes at record high following positive earnings reports",
    "Health authority confirms outbreak contained with vaccination campaign",
    "Treaty signed between two nations to reduce trade tariffs",
    "Technology firm announces layoffs affecting 5% of global workforce",
    "Athletes break world record at international championship",
    "City mayor announces infrastructure investment plan worth billions",
    "Weather service issues flood warning for multiple counties",
    "Report shows literacy rates improved by 8% over five years",
]

SEED_FAKE = [
    "Doctors don't want you to know about this miracle cure that reverses aging overnight",
    "The government is hiding alien contact from Area 51 confirmed by insider",
    "Bill Gates microchips confirmed in COVID vaccines according to anonymous whistleblower",
    "Eating chocolate cures cancer says secret study suppressed by big pharma",
    "5G towers cause coronavirus experts reveal the hidden truth",
    "The moon landing was staged in a Hollywood studio leaked documents show",
    "Drinking bleach kills COVID-19 virus says viral social media post",
    "Celebrities are secretly lizard people reveals former bodyguard",
    "Deep state controls weather using HAARP technology insider exposes truth",
    "Flat earth proven by NASA whistleblower who escaped to tell all",
    "Vaccines cause autism the truth big health companies hide from parents",
    "Chemtrails confirmed as mind control program by intelligence defector",
    "Mainstream media is entirely scripted paid actor reveals backstage footage",
    "Drinking alkaline water at pH 9.5 cures all known diseases",
    "Secret society controls all world governments revealed by ex-member on deathbed",
    "New world order plot to reduce global population to 500 million exposed",
    "Pyramids built by aliens carbon dating proves timeline impossible",
    "Famous celebrity faked death and living in secret island retirement",
    "Common household spice destroys cancer cells doctors trying to suppress fact",
    "Election machines pre-programmed to flip votes whistleblower says in interview",
]


def load_jsonl_dataset():
    """Load and label data from JSONL files in Dataset/."""
    texts  = []
    labels = []

    pattern = os.path.join(DATASET_DIR, "*.jsonl")
    files   = sorted(glob.glob(pattern))

    if not files:
        print("[Train] No JSONL files found in Dataset/ — using seed data only.")
        return texts, labels

    print(f"[Train] Loading {len(files)} JSONL files...")
    loaded = 0
    errors = 0

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    score   = obj.get("importance_score", 0)
                    headline = obj.get("headline", "")
                    reason   = obj.get("reason", "")

                    # Combine headline + reason for richer text
                    combined = f"{headline} {reason}".strip()
                    if not combined or len(combined) < 20:
                        continue

                    # Label: high importance = REAL (credible verifiable)
                    #        low importance  = FAKE (noise/unverifiable)
                    label = "REAL" if score >= 40 else "FAKE"

                    texts.append(combined)
                    labels.append(label)
                    loaded += 1

                except (json.JSONDecodeError, KeyError, TypeError):
                    errors += 1

    print(f"[Train] Loaded {loaded} samples ({errors} errors skipped).")
    real_count = labels.count("REAL")
    fake_count = labels.count("FAKE")
    print(f"[Train] Distribution — REAL: {real_count}, FAKE: {fake_count}")
    return texts, labels


def train():
    # ── Load JSONL data ───────────────────────────────────────────────────────
    texts, labels = load_jsonl_dataset()

    # ── Append seed data ──────────────────────────────────────────────────────
    seed_texts  = SEED_REAL + SEED_FAKE
    seed_labels = ["REAL"] * len(SEED_REAL) + ["FAKE"] * len(SEED_FAKE)

    # Repeat seed data to ensure it has meaningful weight
    repeat = max(1, len(texts) // (len(seed_texts) * 2)) if texts else 10
    texts  = texts  + seed_texts * repeat
    labels = labels + seed_labels * repeat

    print(f"[Train] Total samples (with seed): {len(texts)}")

    # ── Train/test split ──────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.15, random_state=42, stratify=labels
    )

    # ── TF-IDF Vectorisation ──────────────────────────────────────────────────
    print("[Train] Fitting TF-IDF vectoriser...")
    tfidf = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2
    )
    X_train_vec = tfidf.fit_transform(X_train)
    X_test_vec  = tfidf.transform(X_test)

    # ── Logistic Regression ───────────────────────────────────────────────────
    print("[Train] Training Logistic Regression...")
    lr = LogisticRegression(
        max_iter=1000,
        C=1.0,
        class_weight="balanced",
        random_state=42
    )
    lr.fit(X_train_vec, y_train)
    lr_preds = lr.predict(X_test_vec)
    print("[Train] LR eval:\n", classification_report(y_test, lr_preds))

    # ── Naive Bayes ───────────────────────────────────────────────────────────
    print("[Train] Training Naive Bayes...")
    nb = MultinomialNB(alpha=0.1)
    nb.fit(X_train_vec, y_train)
    nb_preds = nb.predict(X_test_vec)
    print("[Train] NB eval:\n", classification_report(y_test, nb_preds))

    # ── Save models ───────────────────────────────────────────────────────────
    joblib.dump(tfidf, os.path.join(MODELS_DIR, "tfidf.pkl"))
    joblib.dump(lr,    os.path.join(MODELS_DIR, "lr_model.pkl"))
    joblib.dump(nb,    os.path.join(MODELS_DIR, "nb_model.pkl"))
    print(f"[Train] Models saved to {MODELS_DIR}/")

    # ── Ensemble eval ─────────────────────────────────────────────────────────
    ensemble_preds = []
    for lr_p, nb_p in zip(lr_preds, nb_preds):
        votes = [lr_p, nb_p]
        ensemble_preds.append("REAL" if votes.count("REAL") >= votes.count("FAKE") else "FAKE")
    print("[Train] Ensemble eval:\n", classification_report(y_test, ensemble_preds))


if __name__ == "__main__":
    train()
