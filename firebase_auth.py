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

        logger.info(f"[Auth] Attempting to load service account from: {service_account_path}")

        if not os.path.exists(service_account_path):
            logger.error(
                f"[Auth] Firebase service account NOT FOUND at: {service_account_path}. "
                "Ensure you have uploaded it as a 'Secret File' on Render and set FIREBASE_SA_PATH."
            )
            return

        # Check if file is empty
        if os.path.getsize(service_account_path) == 0:
            logger.error(f"[Auth] Firebase service account file is EMPTY at: {service_account_path}")
            return

        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)

        _firebase_initialized = True
        logger.info("[Auth] Firebase Admin SDK successfully initialised.")

    except Exception as e:
        logger.error(f"[Auth] Failed to initialise Firebase Admin SDK: {str(e)}")


_init_firebase()


# ── Token verification ────────────────────────────────────────────────────────

def verify_token(id_token: str) -> dict | None:
    """
    Verify a Firebase ID token.
    """
    if not _firebase_initialized:
        # Try initializing one last time if it failed at startup
        _init_firebase()
        if not _firebase_initialized:
            logger.error("[Auth] Cannot verify token: Firebase Admin SDK not initialised.")
            return None

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.warning(f"[Auth] Token verification failed: {str(e)}")
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
