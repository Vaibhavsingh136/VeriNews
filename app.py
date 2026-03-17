"""
app.py — VeriNews Flask Application Entry Point
Routes: / (home), /analyze (POST), /history
"""
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

import database as db
import preprocessing
import ml_models
import ocr_module
import firebase_auth as fauth
from ocr_module import extract_text as ocr_extract
from url_fetcher import fetch_url

# ── App Config ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "verinews-dev-secret-2024")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
@fauth.login_required
def index():
    models_ready = ml_models.models_exist()
    return render_template("index.html", models_ready=models_ready,
                           user=fauth.current_user())


@app.route("/analyze", methods=["POST"])
@fauth.login_required
def analyze():
    input_type = request.form.get("input_type", "text")
    raw_text   = ""
    media_id   = None
    url_id     = None
    ocr_conf   = None
    url_meta   = {}
    error      = None

    # ── 1. Acquire input ──────────────────────────────────────────────────────
    try:
        if input_type == "text":
            raw_text = request.form.get("news_text", "").strip()
            if not raw_text:
                flash("Please enter some text to analyze.", "error")
                return redirect(url_for("index"))

        elif input_type == "image":
            if "image_file" not in request.files:
                flash("No file selected.", "error")
                return redirect(url_for("index"))

            file = request.files["image_file"]
            if file.filename == "" or not allowed_file(file.filename):
                flash("Please upload a valid image file (PNG, JPG, etc.).", "error")
                return redirect(url_for("index"))

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Log media upload
            file_size = os.path.getsize(filepath)
            media_id = db.insert_media_upload(filename, filename.rsplit(".", 1)[1], file_size)

            # OCR extraction
            ocr_result = ocr_extract(filepath)
            if not ocr_result["success"]:
                db.log_solution(0, media_id=media_id, fetch_status="ocr_failed",
                                metadata={"error": ocr_result["error"]})
                flash(f"OCR extraction failed: {ocr_result['error']}", "error")
                return redirect(url_for("index"))

            db.insert_ocr_result(media_id, ocr_result["extracted_text"], ocr_result["confidence_score"])
            raw_text = ocr_result["extracted_text"]
            ocr_conf = ocr_result["confidence_score"]

        elif input_type == "url":
            submitted_url = request.form.get("news_url", "").strip()
            if not submitted_url:
                flash("Please enter a URL to analyze.", "error")
                return redirect(url_for("index"))

            fetch_result = fetch_url(submitted_url)
            url_id = db.insert_url_fetch(
                submitted_url,
                fetch_result["author"],
                fetch_result["post_date"],
                fetch_result["fetched_text"],
                fetch_result["fetch_status"]
            )

            if fetch_result["fetch_status"] == "failed":
                db.log_solution(0, url_id=url_id, fetch_status="failed",
                                metadata={"error": fetch_result.get("error")})
                flash(f"Could not retrieve content from that URL: {fetch_result.get('error', 'Unknown error')}", "error")
                return redirect(url_for("index"))

            raw_text = fetch_result["fetched_text"]
            url_meta = {
                "author": fetch_result["author"],
                "post_date": fetch_result["post_date"],
                "url": submitted_url
            }

        if not raw_text or len(raw_text.strip()) < 10:
            flash("Not enough text content to analyze. Please try a different input.", "error")
            return redirect(url_for("index"))

        # ── 2. Log user input ─────────────────────────────────────────────────
        news_text_preview = raw_text[:500]
        input_id = db.insert_user_input(input_type, news_text_preview, media_id, url_id)

        # ── 3. Preprocessing ──────────────────────────────────────────────────
        cleaned = preprocessing.preprocess(raw_text)
        preprocessing_id = db.insert_preprocessing(input_type, cleaned)

        # ── 4. Feature vector record ──────────────────────────────────────────
        vector_id = db.insert_feature_vector(preprocessing_id)

        # ── 5. ML Prediction ──────────────────────────────────────────────────
        if not ml_models.models_exist():
            flash("ML models are not trained yet. Please run train_models.py first.", "error")
            return redirect(url_for("index"))

        result = ml_models.predict(cleaned)

        # ── 6. Log individual model predictions ───────────────────────────────
        db.insert_model_prediction("logistic_regression", vector_id, result["lr_pred"], result["lr_prob"] / 100)
        db.insert_model_prediction("naive_bayes",         vector_id, result["nb_pred"], result["nb_prob"] / 100)

        # ── 7. Log ensemble result ────────────────────────────────────────────
        db.insert_ensemble_result(vector_id, result["label"], result["confidence"] / 100)

        # ── 8. Full solution log ──────────────────────────────────────────────
        log_meta = {
            "input_type":   input_type,
            "label":        result["label"],
            "confidence":   result["confidence"],
            "lr_pred":      result["lr_pred"],
            "nb_pred":      result["nb_pred"],
            "ocr_conf":     ocr_conf,
            **url_meta
        }
        db.log_solution(input_id, media_id=media_id, url_id=url_id,
                        fetch_status="success", metadata=log_meta)

        return render_template(
            "result.html",
            label=result["label"],
            confidence=result["confidence"],
            lr_pred=result["lr_pred"],
            lr_prob=result["lr_prob"],
            nb_pred=result["nb_pred"],
            nb_prob=result["nb_prob"],
            input_type=input_type,
            raw_text=raw_text[:300],
            ocr_conf=ocr_conf,
            url_meta=url_meta,
        )

    except Exception as e:
        logger.exception("[APP] Unhandled error in /analyze")
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for("index"))


# ── Auth routes ────────────────────────────────────────────────────────────────
@app.route("/login")
def login():
    if fauth.current_user():
        return redirect(url_for("index"))
    return render_template("login.html", user=None)


@app.route("/auth/session", methods=["POST"])
def auth_session():
    """Receive Firebase ID token from JS, verify it, set server session."""
    data     = request.get_json(silent=True) or {}
    id_token = data.get("id_token", "")

    if not id_token:
        return jsonify({"error": "No token provided."}), 400

    decoded = fauth.verify_token(id_token)
    if not decoded:
        return jsonify({"error": "Invalid or expired token."}), 401

    fauth.set_user_session(decoded)
    next_url = session.pop("next", None) or url_for("index")
    logger.info(f"[Auth] User signed in: {decoded.get('email')}")
    return jsonify({"ok": True, "next": next_url})


@app.route("/logout")
def logout():
    email = session.get("email", "")
    fauth.clear_session()
    logger.info(f"[Auth] User signed out: {email}")
    return redirect(url_for("login"))


# ── OCR status check ──────────────────────────────────────────────────────────
@app.route("/ocr-status")
def ocr_status():
    ready = ocr_module._reader_ready
    return jsonify({"ocr_ready": ready})


# ── Health check (useful for deployment monitoring) ────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "models_ready": ml_models.models_exist(),
        "ocr_ready": ocr_module._reader_ready
    })


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db.init_db()
    # ocr_module auto-warms on import; explicit call here ensures it fires
    # even in Flask's debug reloader child process
    ocr_module.warmup()
    app.run(debug=True, port=5000)
