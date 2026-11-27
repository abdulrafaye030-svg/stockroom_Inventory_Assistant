"""Sign-in for the Stockroom API: credential checks and signed session cookies.

The account comes from STOCKROOM_USERNAME / STOCKROOM_PASSWORD, set in the
environment or in a local .env file (see envfile.py and .env.example). If either is
missing, every sign-in is refused. Sessions are stateless HMAC-signed tokens, so they
also work on Vercel, where each request may run in a fresh process. Set STOCKROOM_SECRET
to a long random string; without it the key is derived from the password.
"""
import base64
import hashlib
import hmac
import os
import time

COOKIE_NAME = "stockroom_session"
SESSION_SECONDS = 12 * 60 * 60


def configured_credentials():
    """Return (username, password), or (None, None) when sign-in is not set up."""
    username = os.environ.get("STOCKROOM_USERNAME", "").strip()
    password = os.environ.get("STOCKROOM_PASSWORD", "")
    if not username or not password:
        return None, None
    return username, password


def is_configured():
    return configured_credentials()[0] is not None


def _secret():
    secret = os.environ.get("STOCKROOM_SECRET")
    if secret:
        return secret.encode("utf-8")
    username, password = configured_credentials()
    if username is None:
        return None
    return hashlib.sha256(f"stockroom:{username}:{password}".encode("utf-8")).digest()


def check_credentials(username, password):
    expected_user, expected_password = configured_credentials()
    if expected_user is None:
        return False
    # Compare both values every time so the response time does not reveal which one was wrong.
    user_ok = hmac.compare_digest(username.strip().lower().encode("utf-8"), expected_user.lower().encode("utf-8"))
    password_ok = hmac.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
    return user_ok and password_ok


def _sign(payload):
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(username, now=None):
    expires = int((now or time.time()) + SESSION_SECONDS)
    encoded = base64.urlsafe_b64encode(username.encode("utf-8")).decode("ascii")
    payload = f"{encoded}.{expires}"
    return f"{payload}.{_sign(payload)}"


def read_token(token, now=None):
    """Return the username for a valid, unexpired token, otherwise None."""
    if not token or token.count(".") != 2 or _secret() is None:
        return None
    encoded, expires, signature = token.split(".")
    if not hmac.compare_digest(signature, _sign(f"{encoded}.{expires}")):
        return None
    try:
        if int(expires) < (now or time.time()):
            return None
        return base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def token_from_cookie_header(header):
    for part in (header or "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_NAME:
            return value
    return None


def session_cookie(token, secure):
    flags = "Path=/; HttpOnly; SameSite=Strict" + ("; Secure" if secure else "")
    if token is None:
        return f"{COOKIE_NAME}=; Max-Age=0; {flags}"
    return f"{COOKIE_NAME}={token}; Max-Age={SESSION_SECONDS}; {flags}"
