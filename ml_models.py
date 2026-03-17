"""
ml_models.py — VeriNews ML Prediction Engine
TF-IDF + Logistic Regression + Naive Bayes + Ensemble (majority voting)
"""
import os
import logging
import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
TFIDF_PATH = os.path.join(MODELS_DIR, "tfidf.pkl")
LR_PATH    = os.path.join(MODELS_DIR, "lr_model.pkl")
NB_PATH    = os.path.join(MODELS_DIR, "nb_model.pkl")

_tfidf = None
_lr    = None
_nb    = None


def models_exist() -> bool:
    return all(os.path.exists(p) for p in [TFIDF_PATH, LR_PATH, NB_PATH])


def load_models():
    global _tfidf, _lr, _nb
    if _tfidf is None:
        if not models_exist():
            raise FileNotFoundError(
                "Trained models not found. Run train_models.py first."
            )
        _tfidf = joblib.load(TFIDF_PATH)
        _lr    = joblib.load(LR_PATH)
        _nb    = joblib.load(NB_PATH)
        logger.info("[ML] Models loaded successfully.")


def predict(text: str) -> dict:
    """
    Full prediction pipeline: vectorise → LR + NB → ensemble.

    Returns:
        {
            "label":      "REAL" | "FAKE",
            "confidence": float (0-100),
            "lr_pred":    "REAL" | "FAKE",
            "nb_pred":    "REAL" | "FAKE",
            "lr_prob":    float,
            "nb_prob":    float,
        }
    """
    load_models()

    # Vectorise
    vec = _tfidf.transform([text])

    # Logistic Regression
    lr_label    = _lr.predict(vec)[0]
    lr_proba    = _lr.predict_proba(vec)[0]
    lr_conf     = float(np.max(lr_proba))

    # Naive Bayes
    nb_label    = _nb.predict(vec)[0]
    nb_proba    = _nb.predict_proba(vec)[0]
    nb_conf     = float(np.max(nb_proba))

    # Ensemble — majority vote (tie → LR wins as it's the stronger model)
    votes = [lr_label, nb_label]
    real_votes = votes.count("REAL")
    fake_votes = votes.count("FAKE")

    if real_votes > fake_votes:
        final_label = "REAL"
    elif fake_votes > real_votes:
        final_label = "FAKE"
    else:
        final_label = lr_label  # tiebreak

    # Average confidence of models that agreed with final label
    agreeing_confs = []
    if lr_label == final_label:
        agreeing_confs.append(lr_conf)
    if nb_label == final_label:
        agreeing_confs.append(nb_conf)
    ensemble_conf = round(float(np.mean(agreeing_confs)) * 100, 1) if agreeing_confs else 50.0

    logger.info(
        f"[ML] LR={lr_label}({lr_conf:.2f}) NB={nb_label}({nb_conf:.2f}) "
        f"→ Ensemble={final_label} ({ensemble_conf}%)"
    )

    return {
        "label":      final_label,
        "confidence": ensemble_conf,
        "lr_pred":    lr_label,
        "nb_pred":    nb_label,
        "lr_prob":    round(lr_conf * 100, 1),
        "nb_prob":    round(nb_conf * 100, 1),
    }
