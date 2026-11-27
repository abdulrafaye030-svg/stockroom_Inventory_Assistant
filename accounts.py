"""Registered accounts, stored in the shop database next to the inventory.

SQLite keeps them in a `users` table and MongoDB in a `users` collection. Passwords are
never stored: each one is hashed with PBKDF2-SHA256 and its own random salt (standard
library only, no extra packages). Usernames are not case-sensitive, so "Rafay" and
"rafay" are the same account.

Set STOCKROOM_ALLOW_SIGNUP=false to turn registration off; existing accounts can still
sign in.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_.-]{3,32}")
MIN_PASSWORD = 8
MAX_PASSWORD = 256
ITERATIONS = 600_000
COLLECTION = "users"


class AccountExists(Exception):
    """The username is already taken."""


def signup_enabled():
    return os.environ.get("STOCKROOM_ALLOW_SIGNUP", "true").strip().lower() not in ("0", "false", "no", "off")


def username_key(username):
    return username.strip().lower()


def validation_error(username, password):
    """Return a message explaining what is wrong with the new account, or None if it is fine."""
    if not USERNAME_PATTERN.fullmatch(username.strip()):
        return "Usernames are 3 to 32 characters: letters, numbers, dots, dashes or underscores."
    if len(password) < MIN_PASSWORD:
        return f"Use a password of at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Passwords can be at most {MAX_PASSWORD} characters."
    if password.strip().lower() == username_key(username):
        return "Choose a password that is different from your username."
    return None


def hash_password(password, salt=None, iterations=None):
    iterations = iterations or ITERATIONS
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored):
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        expected = hash_password(password, salt, int(iterations))
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(expected, stored)


# A real hash to check against when the username does not exist, so a missing account
# takes as long to reject as a wrong password.
_DUMMY_HASH = None


def _dummy_hash():
    global _DUMMY_HASH
    if _DUMMY_HASH is None or int(_DUMMY_HASH.split("$")[1]) != ITERATIONS:
        _DUMMY_HASH = hash_password(secrets.token_hex(16))
    return _DUMMY_HASH


def _ensure_sqlite_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username_key TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)


def find_user(shop, username):
    """Return {"username", "password_hash"} for the account, or None."""
    db, mongo = shop
    key = username_key(username)
    if mongo:
        row = db[COLLECTION].find_one({"username_key": key}, {"username": 1, "password_hash": 1})
    else:
        _ensure_sqlite_table(db)
        row = db.execute("SELECT username, password_hash FROM users WHERE username_key = ?", (key,)).fetchone()
    return {"username": row["username"], "password_hash": row["password_hash"]} if row else None


def create_user(shop, username, password):
    """Store a new account and return its username. Raises AccountExists if the name is taken."""
    db, mongo = shop
    username = username.strip()
    record = {
        "username_key": username_key(username),
        "username": username,
        "password_hash": hash_password(password),
        "created_at": int(time.time()),
    }
    if mongo:
        from pymongo.errors import DuplicateKeyError
        users = db[COLLECTION]
        users.create_index("username_key", unique=True)
        try:
            users.insert_one(record)
        except DuplicateKeyError as error:
            raise AccountExists(username) from error
    else:
        _ensure_sqlite_table(db)
        try:
            with db:
                db.execute(
                    "INSERT INTO users (username_key, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (record["username_key"], username, record["password_hash"], record["created_at"]),
                )
        except sqlite3.IntegrityError as error:
            raise AccountExists(username) from error
    return username


def authenticate(shop, username, password):
    """Return the account's username if the password is right, otherwise None."""
    user = find_user(shop, username)
    if user is None:
        verify_password(password, _dummy_hash())
        return None
    return user["username"] if verify_password(password, user["password_hash"]) else None
