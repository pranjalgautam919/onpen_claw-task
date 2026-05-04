"""
Data layer – loads CSVs and the policy document into memory.

All data is held as plain Python dicts / lists so the tool functions
can query it without any external database.
"""

import csv
import json
from typing import Any, Dict, List, Optional

from src.config import PRODUCTS_CSV, ORDERS_CSV, POLICY_FILE, SIZING_GUIDE, FAQS_FILE


# ── Loaders ────────────────────────────────────────────────────────────────────

def _parse_list(raw: str) -> List[str]:
    """Split a comma-separated field into a trimmed list."""
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_int_list(raw: str) -> List[int]:
    """Split a comma-separated field into a list of ints."""
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def load_products() -> Dict[str, dict]:
    """Return {product_id: {…}} from the products CSV."""
    products: Dict[str, dict] = {}
    with open(PRODUCTS_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = row["product_id"].strip()
            sizes = _parse_list(row["sizes_available"])
            stock = _parse_int_list(row["stock_per_size"])
            size_stock = dict(zip(sizes, stock))
            products[pid] = {
                "product_id": pid,
                "title": row["title"].strip(),
                "vendor": row["vendor"].strip(),
                "price": float(row["price"]),
                "compare_at_price": float(row["compare_at_price"]),
                "tags": _parse_list(row["tags"]),
                "sizes_available": sizes,
                "stock_per_size": size_stock,
                "is_sale": row["is_sale"].strip().upper() == "TRUE",
                "is_clearance": row["is_clearance"].strip().upper() == "TRUE",
                "bestseller_score": int(row["bestseller_score"]),
            }
    return products


def load_orders() -> Dict[str, dict]:
    """Return {order_id: {…}} from the orders CSV."""
    orders: Dict[str, dict] = {}
    with open(ORDERS_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            oid = row["order_id"].strip()
            orders[oid] = {
                "order_id": oid,
                "order_date": row["order_date"].strip(),
                "product_id": row["product_id"].strip(),
                "size": row["size"].strip(),
                "price_paid": float(row["price_paid"]),
                "customer_id": row["customer_id"].strip(),
                "shipping_status": row.get("shipping_status", "unknown").strip(),
                "tracking_number": row.get("tracking_number", "").strip(),
                "estimated_delivery": row.get("estimated_delivery", "").strip(),
            }
    return orders


def load_policy() -> str:
    """Return the full policy text as a string."""
    with open(POLICY_FILE, encoding="utf-8") as fh:
        return fh.read()


def load_sizing_guide() -> Dict[str, Any]:
    """Return the sizing guide as a dict."""
    with open(SIZING_GUIDE, encoding="utf-8") as fh:
        return json.load(fh)


def load_faqs() -> Dict[str, Any]:
    """Return the FAQ knowledge base as a dict."""
    with open(FAQS_FILE, encoding="utf-8") as fh:
        return json.load(fh)


# ── Singleton cache ────────────────────────────────────────────────────────────

_cache: Dict[str, object] = {}


def get_products() -> Dict[str, dict]:
    if "products" not in _cache:
        _cache["products"] = load_products()
    return _cache["products"]


def get_orders() -> Dict[str, dict]:
    if "orders" not in _cache:
        _cache["orders"] = load_orders()
    return _cache["orders"]


def get_policy() -> str:
    if "policy" not in _cache:
        _cache["policy"] = load_policy()
    return _cache["policy"]


def get_sizing_guide() -> Dict[str, Any]:
    if "sizing_guide" not in _cache:
        _cache["sizing_guide"] = load_sizing_guide()
    return _cache["sizing_guide"]


def get_faqs() -> Dict[str, Any]:
    if "faqs" not in _cache:
        _cache["faqs"] = load_faqs()
    return _cache["faqs"]
