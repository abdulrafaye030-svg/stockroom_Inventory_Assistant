"""Tests for account registration: validation, password hashing, storage and the HTTP API.

Run from the project directory with:  py -m unittest discover tests
"""
import http.client
import json
import os
import sqlite3
import threading
import unittest
from http.server import HTTPServer
from unittest import mock

import accounts
import auth
import database
from server import StockroomHandler


def make_shop():
    """An in-memory copy of the demo database, so tests never add users to the real file."""
    source = database.open_demo()
    db = sqlite3.connect(":memory:", check_same_thread=False)
    source.backup(db)
    source.close()
    db.row_factory = sqlite3.Row
    db.create_function("clean_name", 1, database.clean)
    return db, False


ENV = {"STOCKROOM_USERNAME": "owner", "STOCKROOM_PASSWORD": "owner-pass-1", "STOCKROOM_SECRET": "test-secret"}


@mock.patch.object(accounts, "ITERATIONS", 1_000)  # Keep the tests fast.
class AccountTests(unittest.TestCase):
    def setUp(self):
        self.shop = make_shop()
        self.addCleanup(self.shop[0].close)

    def test_validation(self):
        self.assertIsNone(accounts.validation_error("rafay_1", "long-enough"))
        self.assertIsNotNone(accounts.validation_error("ab", "long-enough"))
        self.assertIsNotNone(accounts.validation_error("has space", "long-enough"))
        self.assertIsNotNone(accounts.validation_error("x" * 33, "long-enough"))
        self.assertIsNotNone(accounts.validation_error("rafay", "short"))
        self.assertIsNotNone(accounts.validation_error("rafay", "p" * 257))
        self.assertIsNotNone(accounts.validation_error("password1", "Password1"))

    def test_hash_is_salted_and_verifies(self):
        first, second = accounts.hash_password("secret-123"), accounts.hash_password("secret-123")
        self.assertNotEqual(first, second)
        self.assertNotIn("secret-123", first)
        self.assertTrue(accounts.verify_password("secret-123", first))
        self.assertFalse(accounts.verify_password("secret-124", first))
        self.assertFalse(accounts.verify_password("secret-123", "not-a-hash"))
        self.assertFalse(accounts.verify_password("secret-123", None))

    def test_create_and_authenticate(self):
        self.assertEqual(accounts.create_user(self.shop, " Rafay ", "secret-123"), "Rafay")
        self.assertEqual(accounts.authenticate(self.shop, "rafay", "secret-123"), "Rafay")
        self.assertIsNone(accounts.authenticate(self.shop, "rafay", "Secret-123"))
        self.assertIsNone(accounts.authenticate(self.shop, "nobody", "secret-123"))

    def test_duplicate_username_is_case_insensitive(self):
        accounts.create_user(self.shop, "Rafay", "secret-123")
        with self.assertRaises(accounts.AccountExists):
            accounts.create_user(self.shop, "RAFAY", "other-pass-9")

    def test_password_is_not_stored(self):
        accounts.create_user(self.shop, "rafay", "secret-123")
        stored = self.shop[0].execute("SELECT password_hash FROM users").fetchone()[0]
        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.assertNotIn("secret-123", stored)

    def test_signup_switch(self):
        for value, expected in (("", True), ("true", True), ("false", False), ("0", False), ("OFF", False)):
            with mock.patch.dict(os.environ, {"STOCKROOM_ALLOW_SIGNUP": value}):
                self.assertEqual(accounts.signup_enabled(), expected, value)


@mock.patch.object(accounts, "ITERATIONS", 1_000)
@mock.patch.dict(os.environ, {**ENV, "STOCKROOM_ALLOW_SIGNUP": "true"})
class RegisterApiTests(unittest.TestCase):
    """Runs the real request handler on a local port."""

    def setUp(self):
        self.shop = make_shop()
        self.server = HTTPServer(("127.0.0.1", 0), StockroomHandler)
        self.server.shop = self.shop
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.shop[0].close)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, cookie=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        payload = json.loads(response.read() or b"{}")
        set_cookie = response.getheader("Set-Cookie")
        connection.close()
        return response.status, payload, set_cookie

    def register(self, username="rafay", password="secret-123"):
        return self.request("POST", "/api/register", {"username": username, "password": password})

    def test_register_signs_in_and_allows_login(self):
        status, payload, cookie = self.register()
        self.assertEqual(status, 201)
        self.assertEqual(payload, {"authenticated": True, "user": "rafay"})
        self.assertIn("HttpOnly", cookie)

        token_cookie = cookie.split(";")[0]
        status, payload, _ = self.request("GET", "/api/session", cookie=token_cookie)
        self.assertEqual((status, payload["user"], payload["signupEnabled"]), (200, "rafay", True))
        status, _, _ = self.request("GET", "/api/products", cookie=token_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(self.request("GET", "/api/products")[0], 401)

        status, payload, _ = self.request("POST", "/api/login", {"username": "RAFAY", "password": "secret-123"})
        self.assertEqual((status, payload["user"]), (200, "rafay"))
        status, _, _ = self.request("POST", "/api/login", {"username": "rafay", "password": "wrong-pass"})
        self.assertEqual(status, 401)

    def test_admin_login_still_works(self):
        status, payload, _ = self.request("POST", "/api/login", {"username": "owner", "password": "owner-pass-1"})
        self.assertEqual((status, payload["user"]), (200, "owner"))

    def test_duplicate_and_reserved_names_rejected(self):
        self.assertEqual(self.register()[0], 201)
        self.assertEqual(self.register("Rafay", "another-pass")[0], 409)
        self.assertEqual(self.register("OWNER", "another-pass")[0], 409)

    def test_invalid_details_rejected(self):
        self.assertEqual(self.register("ab", "secret-123")[0], 400)
        self.assertEqual(self.register("rafay", "short")[0], 400)
        self.assertEqual(self.request("POST", "/api/register", {"username": "rafay"})[0], 400)

    def test_signup_can_be_turned_off(self):
        with mock.patch.dict(os.environ, {"STOCKROOM_ALLOW_SIGNUP": "false"}):
            status, payload, _ = self.register()
            self.assertEqual(status, 403)
            self.assertFalse(self.request("GET", "/api/session")[1]["signupEnabled"])

    def test_registration_needs_a_signing_key(self):
        with mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "", "STOCKROOM_PASSWORD": "", "STOCKROOM_SECRET": ""}):
            self.assertFalse(auth.can_sign_sessions())
            self.assertEqual(self.register()[0], 503)

    def test_registered_user_works_with_only_a_secret(self):
        with mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "", "STOCKROOM_PASSWORD": ""}):
            status, _, cookie = self.register()
            self.assertEqual(status, 201)
            self.assertEqual(self.request("GET", "/api/session", cookie=cookie.split(";")[0])[1]["user"], "rafay")


if __name__ == "__main__":
    unittest.main()
