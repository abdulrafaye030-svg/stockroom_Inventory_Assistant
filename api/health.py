"""Vercel function for GET /api/health. The shared logic lives in server.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import VercelHandler as handler  # noqa: E402,F401  (Vercel looks for "handler")
