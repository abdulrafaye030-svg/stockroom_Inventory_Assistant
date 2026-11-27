"""Local API and production static-file server for the Stockroom React app."""
import argparse
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

from envfile import load_env_file

load_env_file()  # Read .env before anything looks at os.environ.

import accounts  # noqa: E402
import auth  # noqa: E402
from chatbot import get_answer, match_question, small_talk  # noqa: E402
from database import clean, customer_balances, describe_error, mongo_rows, open_shop  # noqa: E402


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "dist"
MAX_REQUEST_BYTES = 16_384


def inventory_products(shop):
    db, mongo = shop
    if mongo:
        rows = mongo_rows(db, "products")
    else:
        rows = db.execute(
            "SELECT name, stock, unit, reorder_level FROM products ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [
        {
            "name": row["name"],
            "stock": row["stock"],
            "unit": row["unit"],
            "reorder_level": row["reorder_level"],
            "status": (
                "out_of_stock" if row["stock"] <= 0 else
                "low_stock" if row["stock"] <= row["reorder_level"] else
                "in_stock"
            ),
        }
        for row in rows
    ]


def chat_reply(shop, text, waiting_for=None):
    message = clean(text)
    if reply := small_talk(message):
        return reply, None
    if waiting_for:
        if not message:
            prompt = "Which product? Type its name." if waiting_for == "product" else "Which customer? Type their name."
            return prompt, waiting_for
        return get_answer(shop, waiting_for, message), None

    intent, name = match_question(message)
    if not intent:
        return "Try a stock question, or type help for more examples.", None
    if intent == "product" and not name:
        return "Which product? Type its name.", intent
    if intent == "balance" and not name:
        return "Which customer? Type their name.", intent
    return get_answer(shop, intent, name), None


class StockroomHandler(SimpleHTTPRequestHandler):
    """Serve the JSON API and, after a build, the React single-page app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BUILD_DIR), **kwargs)

    @property
    def shop(self):
        return self.server.shop

    def _send_json(self, status, payload, headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _api_error(self, error, status=500):
        self._send_json(status, {"error": str(error)})

    def _session_user(self):
        return auth.read_token(auth.token_from_cookie_header(self.headers.get("Cookie")))

    def _secure_request(self):
        return bool(os.environ.get("VERCEL")) or self.headers.get("X-Forwarded-Proto") == "https"

    def _require_user(self):
        """Return the signed-in username, or send a 401 and return None."""
        user = self._session_user()
        if not user:
            self._api_error("Please sign in to continue.", 401)
        return user

    def do_GET(self):
        request = urlparse(self.path)
        if request.path.startswith("/api/"):
            if request.path == "/api/health":
                source = "MongoDB" if self.shop[1] else "SQLite demo"
                self._send_json(200, {"ok": True, "source": source})
            elif request.path == "/api/session":
                user = self._session_user()
                self._send_json(200, {
                    "authenticated": bool(user), "user": user, "signupEnabled": accounts.signup_enabled(),
                })
            elif not self._require_user():
                return
            elif request.path == "/api/customers":
                try:
                    self._send_json(200, {"customers": customer_balances(self.shop)})
                except Exception as error:
                    self._api_error(describe_error(error, self.shop[1]))
            elif request.path == "/api/products":
                try:
                    self._send_json(200, {"products": inventory_products(self.shop)})
                except Exception as error:
                    self._api_error(describe_error(error, self.shop[1]))
            else:
                self._api_error("API endpoint not found.", 404)
            return

        if not BUILD_DIR.is_dir() or not (BUILD_DIR / "index.html").is_file():
            self._api_error(
                "React build not found. Run `npm run dev` for development or `npm run build` first.",
                404,
            )
            return

        relative = unquote(request.path.lstrip("/"))
        candidate = (BUILD_DIR / relative).resolve()
        if request.path == "/" or not candidate.is_relative_to(BUILD_DIR.resolve()) or not candidate.is_file():
            self.path = "/index.html"
        super().do_GET()

    def _read_json(self):
        """Return the request's JSON object, or send an error and return None."""
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._api_error("Invalid request length.", 400)
            return
        if content_length <= 0:
            self._api_error("A JSON request body is required.", 400)
            return None
        if content_length > MAX_REQUEST_BYTES:
            self._api_error("Message is too long.", 413)
            return None

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._api_error("Request body must be valid JSON.", 400)
            return None
        if not isinstance(payload, dict):
            self._api_error("Request body must be a JSON object.", 400)
            return None
        return payload

    def do_POST(self):
        request = urlparse(self.path)
        if request.path == "/api/login":
            self._login()
        elif request.path == "/api/register":
            self._register()
        elif request.path == "/api/logout":
            cookie = auth.session_cookie(None, self._secure_request())
            self._send_json(200, {"authenticated": False}, [("Set-Cookie", cookie)])
        elif request.path == "/api/chat":
            if self._require_user():
                self._chat()
        else:
            self._api_error("API endpoint not found.", 404)

    def _read_credentials(self):
        """Return (username, password) from the JSON body, or send an error and return None."""
        payload = self._read_json()
        if payload is None:
            return None
        username, password = payload.get("username"), payload.get("password")
        if not isinstance(username, str) or not isinstance(password, str) or not username.strip() or not password:
            self._api_error("Enter your username and password.", 400)
            return None
        if not auth.can_sign_sessions():
            self._api_error(
                "Sign-in is not set up. Set STOCKROOM_SECRET (or STOCKROOM_USERNAME and STOCKROOM_PASSWORD) "
                "in .env or the host's settings.",
                503,
            )
            return None
        return username, password

    def _start_session(self, user, status=200):
        cookie = auth.session_cookie(auth.create_token(user), self._secure_request())
        self._send_json(status, {"authenticated": True, "user": user}, [("Set-Cookie", cookie)])

    def _login(self):
        credentials = self._read_credentials()
        if credentials is None:
            return
        username, password = credentials
        if auth.check_credentials(username, password):
            self._start_session(auth.configured_credentials()[0])
            return
        if len(password) > accounts.MAX_PASSWORD:
            self._api_error("Incorrect username or password.", 401)
            return
        try:
            user = accounts.authenticate(self.shop, username, password)
        except Exception as error:
            self._api_error(describe_error(error, self.shop[1]))
            return
        if not user:
            self._api_error("Incorrect username or password.", 401)
            return
        self._start_session(user)

    def _register(self):
        if not accounts.signup_enabled():
            self._api_error("Registration is turned off. Ask the shop owner for an account.", 403)
            return
        credentials = self._read_credentials()
        if credentials is None:
            return
        username, password = credentials
        if problem := accounts.validation_error(username, password):
            self._api_error(problem, 400)
            return
        if auth.is_admin_username(username):
            self._api_error("That username is taken. Choose another one.", 409)
            return
        try:
            user = accounts.create_user(self.shop, username, password)
        except accounts.AccountExists:
            self._api_error("That username is taken. Choose another one.", 409)
            return
        except Exception as error:
            self._api_error(describe_error(error, self.shop[1]))
            return
        self._start_session(user, 201)

    def _chat(self):
        payload = self._read_json()
        if payload is None:
            return
        text = payload.get("message")
        if not isinstance(text, str) or not text.strip():
            self._api_error("Enter a question before sending.", 400)
            return
        if len(text) > 4000:
            self._api_error("Message is too long.", 413)
            return
        waiting_for = payload.get("waitingFor")
        if waiting_for not in (None, "product", "balance"):
            self._api_error("Invalid conversation state.", 400)
            return

        try:
            answer, next_question = chat_reply(self.shop, text, waiting_for)
        except Exception as error:
            self._api_error(describe_error(error, self.shop[1]))
            return
        self._send_json(200, {"answer": answer, "waitingFor": next_question})


class VercelHandler(StockroomHandler):
    """Vercel serverless entry point (see api/): opens the database for each request."""

    def _with_shop(self, method):
        try:
            with open_shop() as shop:
                self._shop = shop
                method()
        except SystemExit as error:
            self._api_error(str(error) or "The inventory database could not be opened.")

    @property
    def shop(self):
        return self._shop

    def do_GET(self):
        self._with_shop(super().do_GET)

    def do_POST(self):
        self._with_shop(super().do_POST)


def main():
    parser = argparse.ArgumentParser(description="Run the Stockroom React app API.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Local server port (default: 8000)")
    args, _ = parser.parse_known_args()

    try:
        with open_shop() as shop:
            server = HTTPServer((args.host, args.port), StockroomHandler)
            server.shop = shop
            print(f"Stockroom API listening on http://{args.host}:{args.port}")
            if not auth.can_sign_sessions():
                print("Warning: neither STOCKROOM_SECRET nor STOCKROOM_USERNAME / STOCKROOM_PASSWORD is set, "
                      "so nobody can sign in or register. Copy .env.example to .env and fill it in.", file=sys.stderr)
            if (BUILD_DIR / "index.html").is_file():
                print("Serving the built React app.")
            else:
                print("Run `npm run dev` in another terminal for the React interface.")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nStopping Stockroom server.")
            finally:
                server.server_close()
    except SystemExit as error:
        if str(error):
            print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
