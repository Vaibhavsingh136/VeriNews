"""
firebase_auth.py — Firebase Admin SDK integration for VeriNews
Verifies Firebase ID tokens and provides a @login_required decorator.
"""
import os
import json
import logging
from functools import wraps
from flask import session, redirect, url_for, request

logger = logging.getLogger(__name__)

# ── Initialise Firebase Admin SDK ─────────────────────────────────────────────
_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        service_account_path = os.environ.get(
            "FIREBASE_SA_PATH",
            os.path.join(os.path.dirname(__file__), "firebase_service_account.json")
        )

        if not os.path.exists(service_account_path):
            logger.warning(
                "[Auth] firebase_service_account.json not found. "
                "Download it from Firebase Console → Project Settings → Service Accounts."
            )
            return

        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)

        _firebase_initialized = True
        logger.info("[Auth] Firebase Admin SDK initialised.")

    except Exception:
        logger.exception("[Auth] Failed to initialise Firebase Admin SDK.")


_init_firebase()


# ── Token verification ────────────────────────────────────────────────────────

def verify_token(id_token: str) -> dict | None:
    """
    Verify a Firebase ID token.

    Returns decoded token dict (contains uid, email, etc.) on success,
    or None on failure.
    """
    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.warning(f"[Auth] Token verification failed: {e}")
        return None


# ── login_required decorator ──────────────────────────────────────────────────

def login_required(f):
    """
    Decorator: redirects to /login if the user is not authenticated.
    Stores the originally requested URL so we can redirect back after login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("uid"):
            session["next"] = request.url
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Session helpers ───────────────────────────────────────────────────────────

def set_user_session(decoded_token: dict):
    """Store user info in Flask session after successful auth."""
    session["uid"]   = decoded_token.get("uid")
    session["email"] = decoded_token.get("email", "")
    session["name"]  = decoded_token.get("name", decoded_token.get("email", "User"))
    session["photo"] = decoded_token.get("picture", "")


def clear_session():
    """Remove all auth-related keys from session."""
    for key in ("uid", "email", "name", "photo", "next"):
        session.pop(key, None)


def current_user() -> dict | None:
    """Return dict of current user info or None if not logged in."""
    if session.get("uid"):
        return {
            "uid":   session["uid"],
            "email": session.get("email", ""),
            "name":  session.get("name", "User"),
            "photo": session.get("photo", ""),
        }
    return None
