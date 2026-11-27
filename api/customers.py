"""Vercel function for GET /api/customers. The shared logic lives in server.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import VercelHandler  # noqa: E402


class handler(VercelHandler):
    """Vercel finds functions by a top-level class named "handler", so it is defined here."""
