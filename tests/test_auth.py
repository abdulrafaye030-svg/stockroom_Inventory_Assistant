"""Tests for sign-in credentials and session tokens.

Run from the project directory with:  py -m unittest discover tests
"""
import os
import unittest
from unittest import mock

import auth


@mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "", "STOCKROOM_PASSWORD": "", "STOCKROOM_SECRET": ""})
class AuthTests(unittest.TestCase):
    def test_default_credentials_accepted(self):
        self.assertTrue(auth.check_credentials("rafay", "rafay1234"))
        self.assertTrue(auth.check_credentials(" Rafay ", "rafay1234"))

    def test_wrong_credentials_rejected(self):
        self.assertFalse(auth.check_credentials("rafay", "wrong"))
        self.assertFalse(auth.check_credentials("someone", "rafay1234"))
        self.assertFalse(auth.check_credentials("rafay", "Rafay1234"))

    def test_environment_credentials_replace_default(self):
        with mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "owner", "STOCKROOM_PASSWORD": "s3cret"}):
            self.assertTrue(auth.check_credentials("owner", "s3cret"))
            self.assertFalse(auth.check_credentials("rafay", "rafay1234"))

    def test_token_round_trip(self):
        self.assertEqual(auth.read_token(auth.create_token("admin")), "admin")

    def test_tampered_token_rejected(self):
        token = auth.create_token("admin")
        encoded, expires, signature = token.split(".")
        self.assertIsNone(auth.read_token(f"{encoded}.{int(expires) + 999}.{signature}"))
        self.assertIsNone(auth.read_token(token[:-1] + ("0" if token[-1] != "0" else "1")))
        self.assertIsNone(auth.read_token("garbage"))
        self.assertIsNone(auth.read_token(None))

    def test_expired_token_rejected(self):
        token = auth.create_token("admin", now=1_000)
        self.assertIsNone(auth.read_token(token, now=1_000 + auth.SESSION_SECONDS + 1))

    def test_changing_password_invalidates_sessions(self):
        token = auth.create_token("admin")
        with mock.patch.dict(os.environ, {"STOCKROOM_PASSWORD": "new-password"}):
            self.assertIsNone(auth.read_token(token))

    def test_cookie_header_parsing(self):
        self.assertEqual(auth.token_from_cookie_header("a=1; stockroom_session=abc.1.f; b=2"), "abc.1.f")
        self.assertIsNone(auth.token_from_cookie_header(None))

    def test_cookie_flags(self):
        cookie = auth.session_cookie("t", secure=True)
        for flag in ("HttpOnly", "SameSite=Strict", "Secure", "Path=/"):
            self.assertIn(flag, cookie)
        self.assertIn("Max-Age=0", auth.session_cookie(None, secure=False))


if __name__ == "__main__":
    unittest.main()
