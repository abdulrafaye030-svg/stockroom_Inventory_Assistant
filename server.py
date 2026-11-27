"""Local API and production static-file server for the Stockroom React app."""
import argparse
import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

from chatbot import get_answer, match_question, small_talk
from database import clean, customer_balances, describe_error, mongo_rows, open_shop


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

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _api_error(self, error, status=500):
        self._send_json(status, {"error": str(error)})

    def do_GET(self):
        request = urlparse(self.path)
        if request.path.startswith("/api/"):
            if request.path == "/api/health":
                source = "MongoDB" if self.shop[1] else "SQLite demo"
                self._send_json(200, {"ok": True, "source": source})
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

    def do_POST(self):
        request = urlparse(self.path)
        if request.path != "/api/chat":
            self._api_error("API endpoint not found.", 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._api_error("Invalid request length.", 400)
            return
        if content_length <= 0:
            self._api_error("A JSON request body is required.", 400)
            return
        if content_length > MAX_REQUEST_BYTES:
            self._api_error("Message is too long.", 413)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._api_error("Request body must be valid JSON.", 400)
            return
        if not isinstance(payload, dict):
            self._api_error("Request body must be a JSON object.", 400)
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
