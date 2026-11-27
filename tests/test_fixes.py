"""Tests for the chat, stock status and error-message fixes.

Run from the project directory with:  py -m unittest discover tests
"""
import sqlite3
import sys
import unittest
from unittest import mock

import database
from chatbot import goodbye_text, help_text, small_talk
from server import chat_reply, inventory_products


def make_shop(extra_products=()):
    """Return an in-memory copy of the demo database so tests never modify the real file."""
    source = database.open_demo()
    db = sqlite3.connect(":memory:")
    source.backup(db)
    source.close()
    db.row_factory = sqlite3.Row
    db.create_function("clean_name", 1, database.clean)
    db.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", extra_products)
    return db, False


class EmptyFollowUpTests(unittest.TestCase):
    def setUp(self):
        self.shop = make_shop()
        self.addCleanup(self.shop[0].close)

    def test_punctuation_only_product_name_asks_again(self):
        self.assertEqual(chat_reply(self.shop, "?", "product"), ("Which product? Type its name.", "product"))

    def test_punctuation_only_customer_name_asks_again(self):
        self.assertEqual(chat_reply(self.shop, "!", "balance"), ("Which customer? Type their name.", "balance"))

    def test_real_follow_up_name_still_answers(self):
        self.assertEqual(chat_reply(self.shop, "Sugar", "product"), ("Sugar: 3 bags", None))
        answer, waiting_for = chat_reply(self.shop, "ali", "balance")
        self.assertIn("remaining Rs. 1,500.00", answer)
        self.assertIsNone(waiting_for)


class NegativeStockTests(unittest.TestCase):
    def setUp(self):
        self.shop = make_shop([("Salt", -2, "packs", 3)])
        self.addCleanup(self.shop[0].close)

    def statuses(self):
        return {p["name"]: p["status"] for p in inventory_products(self.shop)}

    def test_negative_and_zero_stock_are_out_of_stock(self):
        statuses = self.statuses()
        self.assertEqual(statuses["Salt"], "out_of_stock")
        self.assertEqual(statuses["Cooking Oil"], "out_of_stock")

    def test_other_statuses_unchanged(self):
        statuses = self.statuses()
        self.assertEqual(statuses["Rice"], "in_stock")
        self.assertEqual(statuses["Sugar"], "low_stock")
        self.assertEqual(statuses["Tea"], "low_stock")

    def test_chat_lists_negative_stock_only_as_out_of_stock(self):
        db, mongo = self.shop
        self.assertIn("Salt", database.stock_answer(database.get_products(db, mongo, "empty", None), "empty"))
        for intent in ("low", "available"):
            answer = database.stock_answer(database.get_products(db, mongo, intent, None), intent)
            self.assertNotIn("Salt", answer, intent)

    def test_mongo_filter_matches_sqlite(self):
        products = [
            {"name": "Salt", "stock": -2, "unit": "packs", "reorder_level": 3},
            {"name": "Rice", "stock": 20, "unit": "bags", "reorder_level": 5},
        ]
        with mock.patch.object(database, "mongo_rows", return_value=products):
            empty = database.get_products(None, True, "empty", None)
            low = database.get_products(None, True, "low", None)
        self.assertEqual([p["name"] for p in empty], ["Salt"])
        self.assertEqual(low, [])


class CustomerBalanceTests(unittest.TestCase):
    def setUp(self):
        self.shop = make_shop()
        self.addCleanup(self.shop[0].close)

    def test_balances_match_chat_and_sort_largest_due_first(self):
        rows = database.customer_balances(self.shop)
        dues = {r["name"]: r["due"] for r in rows}
        self.assertEqual((dues["Ali"], dues["Ahmed"], dues["Bilal"]), (1500.0, 800.0, 0.0))
        self.assertEqual([r["due"] for r in rows], sorted((r["due"] for r in rows), reverse=True))
        self.assertIn("remaining Rs. 1,500.00", chat_reply(self.shop, "how much does ali owe")[0])


class ErrorMessageTests(unittest.TestCase):
    db_path = str(database.demo_path())

    def test_api_error_message_hides_file_path(self):
        message = database.describe_error(sqlite3.OperationalError("no such table: products"), False)
        self.assertEqual(message, "SQLite: no such table: products. Check the demo database file.")
        self.assertNotIn(self.db_path, message)

    def test_startup_error_in_terminal_keeps_file_path(self):
        failure = sqlite3.OperationalError("unable to open database file")
        with mock.patch.object(database, "open_demo", side_effect=failure), \
                mock.patch.object(sys, "argv", ["server.py"]):
            with self.assertRaises(SystemExit) as raised:
                with database.open_shop():
                    pass
        self.assertIn(self.db_path, str(raised.exception))


class SmallTalkTests(unittest.TestCase):
    def test_hi_and_hello_reply_hello(self):
        for word in ("hi", "hello"):
            self.assertEqual(small_talk(word), "Hello!\n" + help_text, word)

    def test_salam_greetings_reply_wa_alaikum_assalam(self):
        for word in ("salam", "assalamualaikum", "aslamualikum"):
            self.assertEqual(small_talk(word), "Wa alaikum assalam!\n" + help_text, word)

    def test_help_and_goodbye(self):
        self.assertEqual(small_talk("help"), help_text)
        for word in ("bye", "quit", "exit"):
            self.assertEqual(small_talk(word), goodbye_text, word)

    def test_other_messages_are_not_small_talk(self):
        self.assertIsNone(small_talk("stock of sugar"))

    def test_web_chat_uses_shared_replies(self):
        shop = make_shop()
        self.addCleanup(shop[0].close)
        # Messages are cleaned first, so case and trailing punctuation do not matter.
        self.assertEqual(chat_reply(shop, "Hello!"), ("Hello!\n" + help_text, None))
        self.assertEqual(chat_reply(shop, "Salam"), ("Wa alaikum assalam!\n" + help_text, None))
        self.assertEqual(chat_reply(shop, "bye"), (goodbye_text, None))
        # Small talk also works in the middle of a follow-up question.
        self.assertEqual(chat_reply(shop, "help", "product"), (help_text, None))


if __name__ == "__main__":
    unittest.main()
