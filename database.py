"""
database.py — VeriNews DB connection and helpers
Uses SQLite for local development (PostgreSQL-ready for production)
"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "verinews.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print("[DB] Database initialised.")


# ── Helpers ──────────────────────────────────────────────────────────────────

def insert_user_input(input_type: str, news_text: str = None,
                      media_id: int = None, url_id: int = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO user_input (input_type, news_text, media_id, url_id) VALUES (?,?,?,?)",
        (input_type, news_text, media_id, url_id)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_media_upload(file_name: str, file_type: str, file_size: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO media_upload (file_name, file_type, file_size) VALUES (?,?,?)",
        (file_name, file_type, file_size)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_ocr_result(media_id: int, extracted_text: str, confidence_score: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO ocr_result (media_id, extracted_text, confidence_score) VALUES (?,?,?)",
        (media_id, extracted_text, confidence_score)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_url_fetch(original_url: str, author: str, post_date: str,
                     fetched_text: str, fetch_status: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO url_fetch (original_url, author, post_date, fetched_text, fetch_status) VALUES (?,?,?,?,?)",
        (original_url, author, post_date, fetched_text, fetch_status)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_preprocessing(source_type: str, cleaned_text: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO preprocessing (source_type, cleaned_text) VALUES (?,?)",
        (source_type, cleaned_text)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_feature_vector(preprocessing_id: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO feature_vector (preprocessing_id) VALUES (?)",
        (preprocessing_id,)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_model_prediction(model_id: str, vector_id: int,
                             predicted_label: str, probability: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO model_prediction (model_id, vector_id, predicted_label, probability) VALUES (?,?,?,?)",
        (model_id, vector_id, predicted_label, probability)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def insert_ensemble_result(vector_id: int, final_label: str, confidence: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO ensemble_result (vector_id, final_label, confidence) VALUES (?,?,?)",
        (vector_id, final_label, confidence)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def log_solution(input_id: int, media_id: int = None, url_id: int = None,
                 fetch_status: str = None, metadata: dict = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO solution_log (input_id, media_id, url_id, fetch_status, metadata) VALUES (?,?,?,?,?)",
        (input_id, media_id, url_id, fetch_status, json.dumps(metadata or {}))
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id
