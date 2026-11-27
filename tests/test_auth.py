"""Tests for sign-in credentials and session tokens.

Run from the project directory with:  py -m unittest discover tests
"""
import os
import unittest
from unittest import mock

import auth
import envfile


@mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "tester", "STOCKROOM_PASSWORD": "test-pass-1", "STOCKROOM_SECRET": ""})
class AuthTests(unittest.TestCase):
    def test_configured_credentials_accepted(self):
        self.assertTrue(auth.check_credentials("tester", "test-pass-1"))
        self.assertTrue(auth.check_credentials(" Tester ", "test-pass-1"))

    def test_wrong_credentials_rejected(self):
        self.assertFalse(auth.check_credentials("tester", "wrong"))
        self.assertFalse(auth.check_credentials("someone", "test-pass-1"))
        self.assertFalse(auth.check_credentials("tester", "Test-pass-1"))

    def test_other_credentials_from_environment(self):
        with mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "owner", "STOCKROOM_PASSWORD": "s3cret"}):
            self.assertTrue(auth.check_credentials("owner", "s3cret"))
            self.assertFalse(auth.check_credentials("tester", "test-pass-1"))

    def test_no_credentials_means_nobody_can_sign_in(self):
        token = auth.create_token("tester")
        with mock.patch.dict(os.environ, {"STOCKROOM_USERNAME": "", "STOCKROOM_PASSWORD": ""}):
            self.assertFalse(auth.is_configured())
            self.assertFalse(auth.check_credentials("", ""))
            self.assertFalse(auth.check_credentials("tester", "test-pass-1"))
            self.assertIsNone(auth.read_token(token))

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


class EnvFileTests(unittest.TestCase):
    def test_parse_env(self):
        text = """
# comment
STOCKROOM_USERNAME=rafay
export STOCKROOM_PASSWORD = "pa ss=word"
QUOTED='x'
EMPTY=
not a setting
"""
        self.assertEqual(
            envfile.parse_env(text),
            {"STOCKROOM_USERNAME": "rafay", "STOCKROOM_PASSWORD": "pa ss=word", "QUOTED": "x", "EMPTY": ""},
        )

    def test_existing_environment_wins_and_missing_file_is_fine(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, ".env")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("STOCKROOM_TEST_A=from-file\nSTOCKROOM_TEST_B=from-file\n")
            with mock.patch.dict(os.environ, {"STOCKROOM_TEST_A": "from-env"}):
                envfile.load_env_file(path)
                self.assertEqual(os.environ["STOCKROOM_TEST_A"], "from-env")
                self.assertEqual(os.environ["STOCKROOM_TEST_B"], "from-file")
                os.environ.pop("STOCKROOM_TEST_B")
            self.assertEqual(envfile.load_env_file(os.path.join(folder, "missing.env")), {})


if __name__ == "__main__":
    unittest.main()
