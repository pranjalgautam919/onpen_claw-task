"""
Configuration for the OpenClaw Retail AI Assistant.
Loads environment variables and defines paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRODUCTS_CSV = DATA_DIR / "products.csv"
ORDERS_CSV = DATA_DIR / "orders.csv"
POLICY_FILE = DATA_DIR / "policy.txt"
SIZING_GUIDE = DATA_DIR / "sizing_guide.json"
FAQS_FILE = DATA_DIR / "faqs.json"

# ── OpenAI ─────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# ── Agent Settings ─────────────────────────────────────────────────────────────
MAX_TOOL_CALLS_PER_TURN = 5
TEMPERATURE = 0.2

# ── Date reference (for return window calculations) ───────────────────────────
# In production this would be datetime.now(). We fix it for reproducibility.
CURRENT_DATE = "2026-05-04"
