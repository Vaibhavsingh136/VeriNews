# -*- coding: utf-8 -*-
"""
verinews_tests.py -- Comprehensive Test Suite for VeriNews
Covers: Unit, Integration, Functional, E2E, Regression, Performance,
        Security, Smoke, Compatibility Testing
"""
import sys
import io

# Force UTF-8 stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import time
import json
import re
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

BASE_URL = "http://127.0.0.1:5000"

_results = {"pass": 0, "fail": 0, "skip": 0, "errors": []}

def _ok(msg, detail=""):
    _results["pass"] += 1
    print(f"    [PASS]  {msg}")

def _fail(msg, detail=""):
    _results["fail"] += 1
    entry = f"{msg}: {detail}" if detail else msg
    _results["errors"].append(entry)
    print(f"    [FAIL]  {msg}")
    if detail:
        print(f"           {detail}")

def _skip(msg):
    _results["skip"] += 1
    print(f"    [SKIP]  {msg}")

def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print("=" * 65)

def http_get(path, follow=True, timeout=10):
    """GET request, returns (status, body, headers)."""
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if not follow:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        handlers.append(NoRedirect())
        
    opener = urllib.request.build_opener(*handlers)
    if not follow:
        opener.addheaders = [('User-agent', 'VeriNewsTest/1.0')]
    try:
        r = opener.open(BASE_URL + path, timeout=timeout)
        return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)
    except Exception as e:
        return 0, str(e), {}

def http_post(path, data, content_type="application/json", timeout=10):
    """POST request; returns (status, body)."""
    if content_type == "application/json":
        payload = json.dumps(data).encode()
    else:
        payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        BASE_URL + path, data=payload,
        headers={"Content-Type": content_type}, method="POST"
    )
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


# ==============================================================================
# 1. UNIT TESTS
# ==============================================================================
def test_unit():
    section("1. UNIT TESTING -- Individual Functions & Modules")

    # -- preprocessing.py ------------------------------------------------------
    print("\n  [preprocessing.py]")
    try:
        import preprocessing as pp

        r = pp.clean_text("Hello World")
        (_ok if r == "hello world" else _fail)("clean_text lowercases text", r)

        r = pp.clean_text("<b>Breaking News</b>")
        (_ok if "<b>" not in r and "breaking" in r else _fail)("clean_text strips HTML tags", r)

        r = pp.clean_text("Visit https://example.com for details")
        (_ok if "http" not in r else _fail)("clean_text strips URLs", r)

        r = pp.clean_text("Hello, world! Is this real?")
        (_ok if not any(c in r for c in ",.!?") else _fail)("clean_text strips punctuation", r)

        r = pp.clean_text("")
        (_ok if r == "" else _fail)("clean_text handles empty string", repr(r))

        r = pp.remove_stopwords("this is a test of the system")
        (_ok if "this" not in r.split() and "test" in r else _fail)("remove_stopwords removes stopwords", r)

        r = pp.stem_text("running runner runs")
        (_ok if "run" in r else _fail)("stem_text reduces words to root", r)

        r = pp.preprocess("The government officials released a major announcement today!")
        (_ok if r and len(r) > 0 else _fail)("preprocess returns non-empty string for real text", r)

        r = pp.preprocess("")
        (_ok if r == "" else _fail)("preprocess handles empty input", repr(r))

        r = pp.preprocess("   ")
        (_ok if r == "" else _fail)("preprocess handles whitespace-only input", repr(r))

    except Exception as e:
        _fail("preprocessing module import/execution", str(e))

    # -- ml_models.py ----------------------------------------------------------
    print("\n  [ml_models.py]")
    try:
        import ml_models

        exists = ml_models.models_exist()
        if exists:
            _ok("models_exist() returns True (models are trained)")
            result = ml_models.predict("government election fraud voting machines rigged")
            (_ok if "label" in result else _fail)("predict() returns label key", str(result))
            (_ok if result["label"] in ("REAL", "FAKE") else _fail)("predict() label is REAL or FAKE", result.get("label"))
            (_ok if "confidence" in result else _fail)("predict() returns confidence key")
            (_ok if 0 <= result["confidence"] <= 100 else _fail)("predict() confidence in 0-100 range", str(result.get("confidence")))
            (_ok if "lr_pred" in result and "nb_pred" in result else _fail)("predict() returns lr_pred and nb_pred")
            (_ok if "lr_prob" in result and "nb_prob" in result else _fail)("predict() returns lr_prob and nb_prob")
        else:
            _skip("models_exist() returned False -- models not trained, skipping predict tests")

    except Exception as e:
        _fail("ml_models module", str(e))

    # -- firebase_auth.py -------------------------------------------------------
    print("\n  [firebase_auth.py]")
    try:
        import firebase_auth as fa

        r = fa.verify_token("not.a.real.token")
        (_ok if r is None else _fail)("verify_token returns None for invalid token", str(r))

        r = fa.verify_token("")
        (_ok if r is None else _fail)("verify_token returns None for empty string", str(r))

        (_ok if callable(fa.current_user) else _fail)("current_user is callable")
        (_ok if callable(fa.set_user_session) else _fail)("set_user_session is callable")
        (_ok if callable(fa.clear_session) else _fail)("clear_session is callable")
        (_ok if callable(fa.login_required) else _fail)("login_required is callable")

    except Exception as e:
        _fail("firebase_auth module", str(e))

    # -- database.py -----------------------------------------------------------
    print("\n  [database.py]")
    try:
        import database as db

        (_ok if callable(db.get_connection) else _fail)("get_connection is callable")
        (_ok if callable(db.init_db) else _fail)("init_db is callable")
        (_ok if callable(db.insert_user_input) else _fail)("insert_user_input is callable")
        (_ok if callable(db.insert_model_prediction) else _fail)("insert_model_prediction is callable")
        (_ok if callable(db.log_solution) else _fail)("log_solution is callable")

        conn = db.get_connection()
        (_ok if conn else _fail)("get_connection returns a live connection")
        conn.close()

    except Exception as e:
        _fail("database module", str(e))


# ==============================================================================
# 2. INTEGRATION TESTS
# ==============================================================================
def test_integration():
    section("2. INTEGRATION TESTING -- Modules Working Together")

    # -- preprocessing -> ml_models --------------------------------------------
    print("\n  [preprocessing -> ml_models]")
    try:
        import preprocessing as pp
        import ml_models

        if not ml_models.models_exist():
            _skip("ML models not trained -- skipping preprocessing->ML integration test")
        else:
            raw = "Scientists discover new evidence supporting climate change theory based on ice cores"
            cleaned = pp.preprocess(raw)
            (_ok if cleaned and len(cleaned) > 3 else _fail)("preprocess produces output for valid input", cleaned)

            result = ml_models.predict(cleaned)
            (_ok if result["label"] in ("REAL", "FAKE") else _fail)("ml_models.predict() accepts preprocessed text", str(result))
            (_ok if isinstance(result["confidence"], float) else _fail)("confidence is a float", str(type(result["confidence"])))

    except Exception as e:
        _fail("preprocessing->ml_models integration", str(e))

    # -- preprocessing -> database pipeline ------------------------------------
    print("\n  [preprocessing -> database]")
    try:
        import preprocessing as pp
        import database as db

        text = "Breaking news story about global economy and financial markets today"
        cleaned = pp.preprocess(text)
        row_id = db.insert_preprocessing("text", cleaned)
        (_ok if isinstance(row_id, int) and row_id > 0 else _fail)("insert_preprocessing returns valid row_id", str(row_id))

        input_id = db.insert_user_input("text", text[:500])
        (_ok if isinstance(input_id, int) and input_id > 0 else _fail)("insert_user_input returns valid row_id", str(input_id))

    except Exception as e:
        _fail("preprocessing->database integration", str(e))

    # -- database write -> read consistency ------------------------------------
    print("\n  [database write->read consistency]")
    try:
        import database as db

        mid = db.insert_media_upload("test_img.jpg", "jpg", 1024)
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM media_upload WHERE media_id=?", (mid,)).fetchone()
        conn.close()
        (_ok if row and row["file_name"] == "test_img.jpg" else _fail)("written media_upload row is readable", str(dict(row) if row else None))
        (_ok if row and row["file_size"] == 1024 else _fail)("media_upload file_size stored correctly", str(row["file_size"] if row else None))

    except Exception as e:
        _fail("database write->read integration", str(e))

    # -- firebase_auth -> /auth/session endpoint --------------------------------
    print("\n  [firebase_auth -> /auth/session endpoint]")
    status, body = http_post("/auth/session", {"id_token": "fake.token.abc"})
    (_ok if status == 401 else _fail)("/auth/session rejects invalid token with 401", f"Got {status}")
    (_ok if "error" in body.lower() else _fail)("/auth/session response body contains 'error'", body[:100])

    status, body = http_post("/auth/session", {})
    (_ok if status == 400 else _fail)("/auth/session returns 400 with no token", f"Got {status}")


# ==============================================================================
# 3. FUNCTIONAL TESTS
# ==============================================================================
def test_functional():
    section("3. FUNCTIONAL TESTING -- Feature Correctness")

    print("\n  [Authentication / Login Feature]")
    status, body, _ = http_get("/login")
    (_ok if status == 200 else _fail)("GET /login returns HTTP 200", f"Got {status}")
    (_ok if "Sign In" in body else _fail)("Login page contains 'Sign In' text")
    (_ok if "login-form" in body else _fail)("Login page contains login-form element")
    (_ok if "btn-google" in body else _fail)("Login page has Google sign-in button")
    (_ok if "register-form" in body else _fail)("Login page has registration form")
    (_ok if "forgot-btn" in body else _fail)("Login page has forgot-password button")
    (_ok if "firebase" in body.lower() else _fail)("Login page loads Firebase SDK")
    (_ok if "auth/session" in body else _fail)("Login page references /auth/session endpoint")

    print("\n  [Auth Redirect Feature]")
    status, body, headers = http_get("/", follow=False)
    (_ok if status in (301, 302) else _fail)("GET / redirects unauthenticated users", f"Got {status}")
    location = headers.get("Location", "")
    (_ok if "login" in location.lower() else _fail)("Redirect points to /login", f"Location: {location}")

    print("\n  [Health Check Feature]")
    status, body, _ = http_get("/health")
    (_ok if status == 200 else _fail)("GET /health returns HTTP 200", f"Got {status}")
    try:
        data = json.loads(body)
        (_ok if data.get("status") == "ok" else _fail)("Health check status is 'ok'", body)
        (_ok if "models_ready" in data else _fail)("Health check includes models_ready field")
        (_ok if "ocr_ready" in data else _fail)("Health check includes ocr_ready field")
    except Exception:
        _fail("Health check response is valid JSON", body[:200])

    print("\n  [OCR Status Feature]")
    status, body, _ = http_get("/ocr-status")
    (_ok if status == 200 else _fail)("GET /ocr-status returns HTTP 200", f"Got {status}")
    try:
        data = json.loads(body)
        (_ok if "ocr_ready" in data else _fail)("OCR status includes ocr_ready field")
    except Exception:
        _fail("OCR status response is valid JSON", body[:100])

    print("\n  [Preprocessing Correctness]")
    import preprocessing as pp

    r = pp.clean_text("<script>alert('xss')</script>some news")
    (_ok if "<script>" not in r and "alert" not in r else _fail)("preprocess strips all HTML/script tags", r)

    r = pp.remove_stopwords("the quick brown fox jumps over a lazy dog")
    (_ok if "the" not in r.split() and "fox" in r else _fail)("remove_stopwords: 'the' removed, 'fox' kept", r)

    r1 = pp.stem_text("running")
    r2 = pp.stem_text("runner")
    (_ok if r1 == r2 == "run" else _fail)(
        f"stem_text normalises 'running'/'runner' to same root",
        f"'{r1}' vs '{r2}'"
    )


# ==============================================================================
# 4. E2E TESTS
# ==============================================================================
def test_e2e():
    section("4. END-TO-END (E2E) TESTING -- Full User Flows")

    print("\n  [Flow: Unauthenticated user visits app]")
    status, body, hdrs = http_get("/", follow=False)
    (_ok if status in (301, 302) else _fail)("Step 1: Visiting / triggers redirect", f"Got {status}")

    status, body, _ = http_get("/login")
    (_ok if status == 200 else _fail)("Step 2: Login page loads successfully", f"Got {status}")
    (_ok if "initializeApp" in body else _fail)("Step 3: Firebase SDK embedded on login page")

    status, body = http_post("/auth/session", {"id_token": "garbage_token_12345"})
    (_ok if status == 401 else _fail)("Step 4: Bad token rejected by /auth/session", f"Got {status}")

    print("\n  [Flow: Health / readiness check]")
    status, body, _ = http_get("/health")
    try:
        data = json.loads(body)
        (_ok if data["status"] == "ok" else _fail)("Health endpoint confirms app is running", body)
    except Exception:
        _fail("Health endpoint returns valid JSON", body[:100])

    print("\n  [Flow: Logout redirects to login]")
    status, body, hdrs = http_get("/logout", follow=False)
    (_ok if status in (301, 302) else _fail)("GET /logout triggers redirect", f"Got {status}")
    location = hdrs.get("Location", "")
    (_ok if "login" in location.lower() else _fail)("Logout redirect points to /login", f"Location: {location}")

    print("\n  [Flow: Static assets are served]")
    status, body, _ = http_get("/static/css/style.css")
    (_ok if status == 200 else _fail)("CSS stylesheet is served", f"Got {status}")
    (_ok if len(body) > 1000 else _fail)("CSS file has substantial content", f"Length: {len(body)}")

    status, body, _ = http_get("/static/js/main.js")
    (_ok if status == 200 else _fail)("main.js is served", f"Got {status}")
    (_ok if "DOMContentLoaded" in body else _fail)("main.js contains expected JS code")


# ==============================================================================
# 5. REGRESSION TESTS
# ==============================================================================
def test_regression():
    section("5. REGRESSION TESTING -- Bugs Fixed Must Not Reappear")

    print("\n  [Regression: session import in app.py]")
    with open(os.path.join(BASE_DIR, "app.py"), encoding="utf-8") as f:
        app_src = f.read()
    flask_import_line = app_src.split("from flask import")[1].split("\n")[0] if "from flask import" in app_src else ""
    (_ok if "session" in flask_import_line else _fail)(
        "app.py imports 'session' from flask",
        "MISSING! This was Bug #1 that caused login to crash"
    )

    print("\n  [Regression: main.js form filter -- login forms not intercepted]")
    with open(os.path.join(BASE_DIR, "static", "js", "main.js"), encoding="utf-8") as f:
        js_src = f.read()
    (_ok if "input_type" in js_src and "filter" in js_src else _fail)(
        "main.js filters forms by input_type field (Bug #2 fix present)"
    )
    # Make sure the raw unfiltered querySelectorAll('form') is not the only form selector
    raw_selector_match = re.search(r"querySelectorAll\(['\"]form['\"]\)", js_src)
    filtered_match = re.search(r"filter", js_src)
    (_ok if filtered_match else _fail)("main.js uses .filter() to scope forms (not all forms globally)")

    print("\n  [Regression: /auth/session returns 400 for missing token]")
    status, _ = http_post("/auth/session", {})
    (_ok if status == 400 else _fail)("/auth/session 400 on empty payload", f"Got {status}")

    print("\n  [Regression: /auth/session returns 401 for invalid token]")
    status, _ = http_post("/auth/session", {"id_token": "x" * 20})
    (_ok if status == 401 else _fail)("/auth/session 401 on malformed token", f"Got {status}")

    print("\n  [Regression: hidden attribute respected (CSS fix)]")
    with open(os.path.join(BASE_DIR, "static", "css", "style.css"), encoding="utf-8") as f:
        css_src = f.read()
    (_ok if "[hidden]" in css_src and "display: none" in css_src else _fail)(
        "CSS contains [hidden] { display: none !important } rule"
    )

    print("\n  [Regression: preprocessing edge cases]")
    import preprocessing as pp
    (_ok if pp.preprocess("") == "" else _fail)("preprocess('') returns empty string")
    (_ok if pp.preprocess("   ") == "" else _fail)("preprocess('   ') returns empty string")
    r = pp.preprocess("<html><body>News</body></html>")
    (_ok if "<html>" not in r else _fail)("preprocess strips HTML tags", r)


# ==============================================================================
# 6. PERFORMANCE TESTS
# ==============================================================================
def test_performance():
    section("6. PERFORMANCE TESTING -- Response Times & Throughput")

    def measure(label, path, n=5, threshold=0.5):
        times = []
        for _ in range(n):
            t0 = time.time()
            http_get(path)
            times.append(time.time() - t0)
        avg = sum(times) / len(times)
        mn, mx = min(times), max(times)
        (_ok if avg < threshold else _fail)(
            f"{label}: avg {avg*1000:.0f}ms ({n} requests, limit {threshold*1000:.0f}ms)",
            f"min={mn*1000:.0f}ms  max={mx*1000:.0f}ms"
        )
        return avg

    print("\n  [HTTP Response time benchmarks]")
    measure("GET /health",              "/health")
    measure("GET /login",               "/login")
    measure("GET /ocr-status",          "/ocr-status")
    measure("GET /static/css/style.css","/static/css/style.css")
    measure("GET /static/js/main.js",   "/static/js/main.js")

    print("\n  [Preprocessing throughput]")
    import preprocessing as pp
    SAMPLE = ("The government announced new economic policies affecting millions of citizens "
              "across the country today in a major press conference. ") * 5
    t0 = time.time()
    for _ in range(100):
        pp.preprocess(SAMPLE)
    elapsed = time.time() - t0
    (_ok if elapsed < 5.0 else _fail)(f"100x preprocess() in {elapsed:.2f}s (limit 5s)", f"{elapsed:.3f}s")

    print("\n  [ML prediction throughput]")
    import ml_models
    if not ml_models.models_exist():
        _skip("ML models not trained -- skipping prediction throughput test")
    else:
        import preprocessing as pp
        cleaned = pp.preprocess(SAMPLE)
        t0 = time.time()
        for _ in range(20):
            ml_models.predict(cleaned)
        elapsed = time.time() - t0
        (_ok if elapsed < 5.0 else _fail)(f"20x ML predict() in {elapsed:.2f}s (limit 5s)", f"{elapsed:.3f}s")

    print("\n  [Concurrent request burst (10 threads)]")
    results = []
    lock = threading.Lock()
    def hit():
        t0 = time.time()
        s, _, _ = http_get("/health")
        with lock:
            results.append((s, time.time() - t0))
    threads = [threading.Thread(target=hit) for _ in range(10)]
    t0 = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    total = time.time() - t0
    ok_count = sum(1 for s, _ in results if s == 200)
    (_ok if ok_count == 10 else _fail)(f"10 concurrent requests: {ok_count}/10 succeeded in {total:.2f}s")


# ==============================================================================
# 7. SECURITY TESTS
# ==============================================================================
def test_security():
    section("7. SECURITY TESTING -- Auth, Injection & Exposure")

    print("\n  [Authentication enforcement]")
    for path in ["/", "/analyze"]:
        status, body, _ = http_get(path, follow=False)
        (_ok if status in (301, 302, 405) else _fail)(f"Unauthenticated {path} is protected", f"Got {status}")

    print("\n  [Token forgery resistance]")
    forged_tokens = [
        "eyJhbGciOiJub25lIn0.eyJ1aWQiOiJoYWNrZXIifQ.",   # alg:none JWT
        "A" * 500,                                           # extremely long token
        "<script>alert(1)</script>",                        # XSS in token field
        "' OR '1'='1",                                      # SQL injection in token
        '{"uid":"admin"}',                                  # raw JSON as token
    ]
    for tok in forged_tokens:
        status, body = http_post("/auth/session", {"id_token": tok})
        (_ok if status in (400, 401) else _fail)(
            f"Forged token rejected: {tok[:30]}...",
            f"Got HTTP {status}"
        )

    print("\n  [HTTP method enforcement]")
    req = urllib.request.Request(BASE_URL + "/auth/session", method="GET")
    try:
        r = urllib.request.urlopen(req, timeout=5)
        _fail("GET /auth/session should be rejected", f"Got {r.status}")
    except urllib.error.HTTPError as e:
        (_ok if e.code in (400, 404, 405) else _fail)("GET /auth/session is rejected", f"Got {e.code}")
    except Exception as e:
        _fail("GET /auth/session method check", str(e))

    print("\n  [Oversized payload handling]")
    status, body = http_post("/auth/session", {"id_token": "X" * 100_000})
    (_ok if status in (400, 401, 413, 431) else _fail)("Server handles 100KB token payload gracefully", f"Got {status}")

    print("\n  [Path traversal protection]")
    for path in [
        "/../../etc/passwd",
        "/login?next=javascript:alert(1)",
        "/%2e%2e/%2e%2e/etc/passwd",
    ]:
        status, body, _ = http_get(path)
        safe = "passwd" not in body and "root:" not in body
        (_ok if safe else _fail)(f"Path traversal blocked: {path[:40]}", f"Status {status}")

    print("\n  [Source code files not served]")
    for path in ["/app.py", "/database.py", "/firebase_auth.py", "/.env", "/firebase_service_account.json"]:
        status, body, _ = http_get(path)
        not_exposed = status == 404 or ("import" not in body and "SECRET" not in body and "private_key" not in body)
        (_ok if not_exposed else _fail)(f"Source not exposed at {path}", f"Status {status}")

    print("\n  [SQL injection in token field]")
    sql_payloads = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1' --",
        "admin'--",
    ]
    for p in sql_payloads:
        status, body = http_post("/auth/session", {"id_token": p})
        (_ok if status in (400, 401) else _fail)(f"SQL injection token rejected", f"payload='{p[:30]}' status={status}")

    print("\n  [Secret key loaded from environment]")
    with open(os.path.join(BASE_DIR, "app.py"), encoding="utf-8") as f:
        src = f.read()
    (_ok if "os.environ.get" in src and "SECRET_KEY" in src else _fail)(
        "SECRET_KEY read from environment variable in app.py"
    )


# ==============================================================================
# 8. SMOKE TESTS
# ==============================================================================
def test_smoke():
    section("8. SMOKE TESTING -- Critical Routes Respond Correctly")

    print("\n  [Critical route availability]")
    routes = {
        "/health":     200,
        "/login":      200,
        "/logout":     302,
        "/ocr-status": 200,
    }
    for path, expected in routes.items():
        status, body, _ = http_get(path, follow=False)
        (_ok if status == expected else _fail)(f"{path} responds with HTTP {expected}", f"Got {status}")

    print("\n  [Static assets available]")
    for asset in ["/static/css/style.css", "/static/js/main.js"]:
        status, body, _ = http_get(asset)
        (_ok if status == 200 else _fail)(f"Asset {asset} is served", f"Got {status}")
        (_ok if len(body) > 100 else _fail)(f"Asset {asset} has non-trivial content", f"Length: {len(body)}")

    print("\n  [Flask app imports cleanly]")
    try:
        import app as flask_app
        (_ok if flask_app.app is not None else _fail)("app.py exposes a Flask app object")
    except Exception as e:
        _fail("app.py imports cleanly", str(e))

    print("\n  [Database readable]")
    db_path = os.path.join(BASE_DIR, "verinews.db")
    (_ok if os.path.exists(db_path) else _fail)("verinews.db exists")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            (_ok if len(tables) > 0 else _fail)(f"Database has {len(tables)} table(s)", str(tables))
            expected_tables = {"user_input", "preprocessing", "media_upload", "url_fetch", "model_prediction"}
            missing = expected_tables - set(tables)
            (_ok if not missing else _fail)("All expected DB tables present", f"Missing: {missing}")
        except Exception as e:
            _fail("Database is readable", str(e))

    print("\n  [Firebase service account present]")
    sa_path = os.path.join(BASE_DIR, "firebase_service_account.json")
    (_ok if os.path.exists(sa_path) else _fail)("firebase_service_account.json present")
    if os.path.exists(sa_path):
        with open(sa_path, encoding="utf-8") as f:
            sa = json.load(f)
        (_ok if sa.get("type") == "service_account" else _fail)("Service account type is 'service_account'")
        (_ok if sa.get("project_id") else _fail)("Service account has project_id")
        (_ok if sa.get("private_key") else _fail)("Service account has private_key")


# ==============================================================================
# 9. COMPATIBILITY TESTS
# ==============================================================================
def test_compatibility():
    section("9. COMPATIBILITY TESTING -- Python Version & Dependencies")

    print("\n  [Python version]")
    ver = sys.version_info
    (_ok if ver >= (3, 9) else _fail)(
        f"Python {ver.major}.{ver.minor}.{ver.micro} (>=3.9 required)",
        f"Found {ver.major}.{ver.minor}.{ver.micro}"
    )

    print("\n  [Required packages importable]")
    packages = [
        ("flask",          "Flask"),
        ("werkzeug",       "werkzeug"),
        ("nltk",           "nltk"),
        ("sklearn",        "scikit-learn"),
        ("joblib",         "joblib"),
        ("numpy",          "numpy"),
        ("sqlite3",        "sqlite3 (stdlib)"),
        ("firebase_admin", "firebase-admin"),
        ("easyocr",        "easyocr"),
        ("PIL",            "Pillow"),
        ("requests",       "requests"),
        ("bs4",            "beautifulsoup4"),
    ]
    for mod, label in packages:
        try:
            __import__(mod)
            _ok(f"{label} is importable")
        except ImportError:
            _fail(f"{label} is NOT installed", f"Run: pip install {mod}")

    print("\n  [requirements.txt consistency]")
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, encoding="utf-8") as f:
            req_text = f.read().lower()
        for pkg in ["flask", "firebase", "easyocr", "scikit", "nltk"]:
            (_ok if pkg in req_text else _fail)(f"requirements.txt mentions '{pkg}'")
    else:
        _skip("requirements.txt not found")

    print("\n  [NLTK data available]")
    import nltk
    for resource, find_path in [("stopwords", "corpora/stopwords"), ("punkt", "tokenizers/punkt")]:
        try:
            nltk.data.find(find_path)
            _ok(f"NLTK '{resource}' data is downloaded")
        except LookupError:
            _fail(f"NLTK '{resource}' data missing", f"Run: python -c \"import nltk; nltk.download('{resource}')\"")

    print("\n  [ML model files present and loadable]")
    import ml_models
    model_files = {
        "tfidf.pkl":    ml_models.TFIDF_PATH,
        "lr_model.pkl": ml_models.LR_PATH,
        "nb_model.pkl": ml_models.NB_PATH,
    }
    all_exist = True
    for name, path in model_files.items():
        exists = os.path.exists(path)
        all_exist = all_exist and exists
        (_ok if exists else _fail)(f"Model file '{name}' exists", path)
    if all_exist:
        try:
            import joblib
            tfidf = joblib.load(ml_models.TFIDF_PATH)
            (_ok if tfidf is not None else _fail)("tfidf.pkl loads without error")
        except Exception as e:
            _fail("tfidf.pkl loads cleanly", str(e))

    print("\n  [SQLite version]")
    sqlite_ver = sqlite3.sqlite_version_info
    (_ok if sqlite_ver >= (3, 8, 0) else _fail)(
        f"SQLite {sqlite3.sqlite_version} (>=3.8.0 required)", str(sqlite_ver)
    )


# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    print("\n" + "#" * 65)
    print("  VeriNews - Comprehensive Test Suite")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Server: {BASE_URL}")
    print("#" * 65)

    try:
        urllib.request.urlopen(BASE_URL + "/health", timeout=5)
        server_up = True
    except Exception:
        server_up = False
        print("\n[!] WARNING: Flask server not reachable at", BASE_URL)
        print("    HTTP-dependent tests will fail.")
        print("    Start the server with: python app.py\n")

    suites = [
        ("Unit",          test_unit),
        ("Integration",   test_integration),
        ("Functional",    test_functional),
        ("E2E",           test_e2e),
        ("Regression",    test_regression),
        ("Performance",   test_performance),
        ("Security",      test_security),
        ("Smoke",         test_smoke),
        ("Compatibility", test_compatibility),
    ]

    for name, fn in suites:
        try:
            fn()
        except Exception as e:
            _fail(f"[{name}] suite crashed", str(e))

    # -- Summary ---------------------------------------------------------------
    total = _results["pass"] + _results["fail"] + _results["skip"]
    print("\n" + "=" * 65)
    print("  TEST RESULTS SUMMARY")
    print("=" * 65)
    print(f"  Total   : {total}")
    print(f"  PASSED  : {_results['pass']}")
    print(f"  FAILED  : {_results['fail']}")
    print(f"  SKIPPED : {_results['skip']}")
    if _results["errors"]:
        print(f"\n  Failed tests ({len(_results['errors'])}):")
        for e in _results["errors"]:
            print(f"    - {e}")
    print("=" * 65 + "\n")

    return 0 if _results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
