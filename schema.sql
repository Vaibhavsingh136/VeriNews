-- VeriNews Database Schema
-- Based on systeminteraction.md §5

CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login  DATETIME
);

CREATE TABLE IF NOT EXISTS media_upload (
    media_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name   TEXT NOT NULL,
    file_type   TEXT NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_size   INTEGER
);

CREATE TABLE IF NOT EXISTS ocr_result (
    ocr_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id        INTEGER REFERENCES media_upload(media_id),
    extracted_text  TEXT,
    confidence_score REAL,
    processed_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS url_fetch (
    url_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    original_url TEXT NOT NULL,
    author       TEXT,
    post_date    TEXT,
    fetched_text TEXT,
    fetch_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS user_input (
    input_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(user_id),
    input_type   TEXT NOT NULL CHECK(input_type IN ('text','image','url')),
    media_id     INTEGER REFERENCES media_upload(media_id),
    news_text    TEXT,
    url_id       INTEGER REFERENCES url_fetch(url_id),
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preprocessing (
    preprocessing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type      TEXT NOT NULL,
    cleaned_text     TEXT NOT NULL,
    processed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_vector (
    vector_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    preprocessing_id INTEGER REFERENCES preprocessing(preprocessing_id),
    tfidf_vector     TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_prediction (
    prediction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id       TEXT NOT NULL,
    vector_id      INTEGER REFERENCES feature_vector(vector_id),
    predicted_label TEXT NOT NULL,
    probability    REAL,
    predicted_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ensemble_result (
    ensemble_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    vector_id    INTEGER REFERENCES feature_vector(vector_id),
    final_label  TEXT NOT NULL,
    confidence   REAL,
    decided_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solution_log (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    input_id     INTEGER REFERENCES user_input(input_id),
    media_id     INTEGER REFERENCES media_upload(media_id),
    url_id       INTEGER REFERENCES url_fetch(url_id),
    fetch_status TEXT,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata     TEXT
);
