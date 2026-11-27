"""Shop data, stock queries and invoice balances."""
import os
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path


def clean(text):
    return " ".join(text.lower().strip().rstrip("?!.").split())


# Renamed when the sample data changes, so an older demo file is not reused.
DEMO_FILE = "inventory_demo_v3.db"


def demo_path():
    """The SQLite demo file. Vercel only allows writing to its temp folder."""
    if os.environ.get("VERCEL"):
        return Path(tempfile.gettempdir()) / DEMO_FILE
    return Path(__file__).with_name(DEMO_FILE)


def open_demo():
    path = demo_path()
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.create_function("clean_name", 1, clean)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='products'").fetchone():
        db.executescript("""
            BEGIN;
            CREATE TABLE products (name TEXT PRIMARY KEY, stock INTEGER, unit TEXT, reorder_level INTEGER);
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE invoices (customer_id INTEGER, total INTEGER, paid INTEGER);
            INSERT INTO products VALUES
                ('Rice', 20, 'bags', 5), ('Sugar', 3, 'bags', 5), ('Cooking Oil', 0, 'bottles', 4),
                ('Tea', 4, 'boxes', 4), ('Flour', 18, 'bags', 6), ('Ghee', 7, 'tins', 4),
                ('Daal Chana', 9, 'kg', 5), ('Daal Masoor', 2, 'kg', 5), ('Chickpeas', 8, 'kg', 4),
                ('Red Chilli Powder', 6, 'packets', 6), ('Turmeric', 11, 'packets', 5),
                ('Milk Powder', 0, 'tins', 3), ('Eggs', 0, 'trays', 2), ('Biscuits', 40, 'packs', 12),
                ('Soap', 15, 'bars', 10), ('Detergent', 3, 'packs', 6), ('Matchboxes', 60, 'boxes', 20),
                ('Bottled Water', 24, 'bottles', 12);
            INSERT INTO customers VALUES
                (1, 'Ali'), (2, 'Ahmed'), (3, 'Bilal'), (4, 'Hassan'), (5, 'Usman'),
                (6, 'Omar'), (7, 'Hamza'), (8, 'Faisal'), (9, 'Imran'), (10, 'Kamran');
            INSERT INTO invoices VALUES
                (1, 3000, 2500), (1, 2000, 1000), (2, 1000, 200), (3, 700, 700),
                (4, 4200, 1200), (4, 1800, 1800), (5, 2600, 2600), (6, 3500, 1000), (6, 900, 600),
                (7, 6000, 3800), (8, 1500, 1500), (9, 7500, 2500), (10, 1200, 450);
            COMMIT;
        """)
    return db


# Optional MERN settings. Change the values on the right to your real top-level field names.
collections = {"products": "products", "customers": "customers", "invoices": "orders"}
fields = {
    "products": {"name": "name", "stock": "stock", "unit": "unit", "reorder_level": "reorder_level"},
    "customers": {"id": "_id", "name": "name"},
    "invoices": {"customer_id": "customer_id", "total": "total", "paid": "amount_paid"},
}
filters = {"products": {}, "customers": {}, "invoices": {}}


# Stock conditions only use fixed SQL. A name typed by the user is a parameter.
stock_filters = {
    "available": "stock > 0",
    "empty": "stock <= 0",
    "low": "stock > 0 AND stock <= reorder_level",
    "product": "clean_name(name) = ?",
}


def mongo_rows(db, table):
    mapping = fields[table]
    documents = db[collections[table]].find(filters[table], list(mapping.values()))
    return [{key: row[field] for key, field in mapping.items()} for row in documents]


def get_products(db, mongo, intent, name):
    if not mongo:
        sql = "SELECT name, stock, unit, reorder_level FROM products WHERE " + stock_filters[intent]
        return db.execute(sql, (name,) if name else ()).fetchall()

    products = mongo_rows(db, "products")
    if intent == "product":
        return [p for p in products if clean(p["name"]) == name]
    if intent == "available":
        return [p for p in products if p["stock"] > 0]
    if intent == "empty":
        return [p for p in products if p["stock"] <= 0]
    return [p for p in products if 0 < p["stock"] <= p["reorder_level"]]


def stock_answer(products, intent):
    if not products:
        return "Product not found." if intent == "product" else "No matching products."
    if intent == "product" and len(products) > 1:
        return "Several products share that name. Use distinct full product names."
    lines = []
    for item in products:
        line = f"{item['name']}: {item['stock']} {item['unit']}"
        if intent == "low":
            line += f" (reorder level {item['reorder_level']})"
        lines.append(line)
    return "\n".join(lines)


def account_totals(customers, invoices):
    """Billed and paid amounts per customer ID, after checking each invoice."""
    totals = {str(c["id"]): [Decimal(0), Decimal(0)] for c in customers}
    for invoice in invoices:
        billed = Decimal(str(invoice["total"]))
        paid = Decimal(str(invoice["paid"]))
        if not billed.is_finite() or not paid.is_finite() or not 0 <= paid <= billed:
            raise ValueError("Check the invoice amounts.")
        customer_id = str(invoice["customer_id"])
        if customer_id not in totals:
            raise ValueError("An invoice refers to a customer outside the selected customer records.")
        account = totals[customer_id]
        account[0] += billed
        account[1] += paid
    return totals


def load_accounts(shop):
    db, mongo = shop
    if mongo:
        return mongo_rows(db, "customers"), mongo_rows(db, "invoices")
    customers = db.execute("SELECT id, name FROM customers").fetchall()
    invoices = db.execute("SELECT customer_id, total, paid FROM invoices").fetchall()
    return customers, invoices


def customer_balances(shop):
    """Each customer's billed, paid and remaining amounts, for the dashboard."""
    customers, invoices = load_accounts(shop)
    totals = account_totals(customers, invoices)
    rows = []
    for c in customers:
        billed, paid = totals[str(c["id"])]
        rows.append({"name": c["name"], "billed": float(billed), "paid": float(paid), "due": float(billed - paid)})
    return sorted(rows, key=lambda row: (-row["due"], row["name"]))


def balance_answer(customers, invoices, name):
    totals = account_totals(customers, invoices)
    if name:
        customers = [c for c in customers if clean(c["name"]) == name]
        if not customers:
            return "Customer not found."
        if len(customers) > 1:
            return "Several customers share that name. Use distinct full names for individual lookup."
    lines = []
    for c in customers:
        billed, paid = totals[str(c["id"])]
        due = billed - paid
        if name:
            return f"{c['name']}: billed Rs. {billed:,.2f}, paid Rs. {paid:,.2f}, remaining Rs. {due:,.2f}."
        if due > 0:
            lines.append(f"{c['name']} (ID {c['id']}) owes Rs. {due:,.2f}.")
    return "\n".join(lines) or "All customer balances are clear."


def get_answer(shop, intent, name):
    db, mongo = shop
    if intent in ("available", "low", "empty", "product"):
        return stock_answer(get_products(db, mongo, intent, name), intent)
    customers, invoices = load_accounts(shop)
    return balance_answer(customers, invoices, name)


def describe_error(error, mongo):
    if isinstance(error, sqlite3.Error):
        return f"SQLite: {error}. Check the demo database file."
    if isinstance(error, KeyError):
        key = error.args[0]
        if key in ("MONGODB_URI", "MONGODB_DB"):
            return f"Set {key} in the terminal before starting MongoDB mode."
        return f"Missing field {key!r}. Check the field mapping in database.py."
    if isinstance(error, ValueError):
        return str(error)
    if isinstance(error, (InvalidOperation, TypeError)):
        return "Check that stock, reorder levels and invoice amounts are numeric."
    return f"{'MongoDB' if mongo else 'Inventory'}: {type(error).__name__}. Check the server address, access and database name."


@contextmanager
def open_shop():
    mongo = "--mongo" in sys.argv
    connection = None
    errors = (KeyError, ValueError, sqlite3.Error)
    try:
        try:
            if mongo:
                from pymongo import MongoClient
                from pymongo.errors import PyMongoError
                errors += (PyMongoError,)
                connection = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=4000)
                db = connection[os.environ["MONGODB_DB"]]
                missing = set(collections.values()) - set(db.list_collection_names())
                if missing:
                    raise ValueError("MongoDB collections missing: " + ", ".join(sorted(missing)))
            else:
                connection = db = open_demo()
        except ImportError:
            raise SystemExit("MongoDB mode needs the driver. Run: py -m pip install pymongo")
        except errors as error:
            message = describe_error(error, mongo)
            if isinstance(error, sqlite3.Error):
                # Startup errors print only to the local terminal, so the path is safe and useful here.
                message += f" File: {demo_path()}"
            raise SystemExit(message) from error
        print("Inventory Bot |", "MongoDB" if mongo else "SQLite demo")
        yield db, mongo
    except (KeyboardInterrupt, EOFError):
        print("\nBot: Goodbye!")
    finally:
        if connection is not None:
            connection.close()
