"""
Structured tool implementations for the OpenClaw agent.

Each public function corresponds to a tool the LLM may invoke via
function-calling. All functions return plain dicts/lists so they can
be JSON-serialised and passed back into the conversation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config import CURRENT_DATE
from src.data_loader import get_products, get_orders, get_policy, get_sizing_guide, get_faqs


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 1 — search_products
# ═══════════════════════════════════════════════════════════════════════════════

def search_products(
    tags: Optional[List[str]] = None,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    size: Optional[str] = None,
    vendor: Optional[str] = None,
    is_sale: Optional[bool] = None,
    is_clearance: Optional[bool] = None,
    sort_by: Optional[str] = "bestseller_score",
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Search and filter products by multiple constraints.

    Parameters
    ----------
    tags : list[str] | None
        Tag keywords to match (e.g. ["modest", "evening"]).  ALL must match.
    max_price : float | None
        Maximum price (inclusive).
    min_price : float | None
        Minimum price (inclusive).
    size : str | None
        Required size – only products with stock > 0 for this size are returned.
    vendor : str | None
        Vendor name (case-insensitive substring match).
    is_sale : bool | None
        If True only sale items; if False only non-sale.
    is_clearance : bool | None
        If True only clearance items; if False only non-clearance.
    sort_by : str
        One of "bestseller_score", "price_asc", "price_desc".
    limit : int
        Max results to return.

    Returns
    -------
    dict with keys: "count", "products" (list of product summaries).
    """
    products = get_products()
    results: List[dict] = []

    for p in products.values():
        # ── tag filter ─────────────────────────────────────────────────────
        if tags:
            p_tags_lower = [t.lower() for t in p["tags"]]
            if not all(t.lower() in p_tags_lower for t in tags):
                continue

        # ── price filters ──────────────────────────────────────────────────
        if max_price is not None and p["price"] > max_price:
            continue
        if min_price is not None and p["price"] < min_price:
            continue

        # ── size & stock filter ────────────────────────────────────────────
        if size is not None:
            stock = p["stock_per_size"].get(size, 0)
            if stock <= 0:
                continue

        # ── vendor filter ──────────────────────────────────────────────────
        if vendor is not None:
            if vendor.lower() not in p["vendor"].lower():
                continue

        # ── sale / clearance filters ───────────────────────────────────────
        if is_sale is not None and p["is_sale"] != is_sale:
            continue
        if is_clearance is not None and p["is_clearance"] != is_clearance:
            continue

        # Build a slim summary for the response
        result_item = {
            "product_id": p["product_id"],
            "title": p["title"],
            "vendor": p["vendor"],
            "price": p["price"],
            "compare_at_price": p["compare_at_price"],
            "tags": p["tags"],
            "is_sale": p["is_sale"],
            "is_clearance": p["is_clearance"],
            "bestseller_score": p["bestseller_score"],
        }
        if size is not None:
            result_item["stock_for_requested_size"] = p["stock_per_size"].get(size, 0)
        results.append(result_item)

    # ── sorting ────────────────────────────────────────────────────────────────
    if sort_by == "price_asc":
        results.sort(key=lambda x: x["price"])
    elif sort_by == "price_desc":
        results.sort(key=lambda x: x["price"], reverse=True)
    else:  # default: bestseller_score desc
        results.sort(key=lambda x: x["bestseller_score"], reverse=True)

    results = results[:limit]

    return {
        "count": len(results),
        "products": results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 2 — get_product
# ═══════════════════════════════════════════════════════════════════════════════

def get_product(product_id: str) -> Dict[str, Any]:
    """
    Fetch full details for a single product by ID.

    Returns
    -------
    dict – full product record, or an error dict if not found.
    """
    products = get_products()
    pid = product_id.strip().upper()
    if pid not in products:
        return {"error": f"Product '{pid}' not found in inventory."}
    p = products[pid]
    return {
        "product_id": p["product_id"],
        "title": p["title"],
        "vendor": p["vendor"],
        "price": p["price"],
        "compare_at_price": p["compare_at_price"],
        "discount_pct": round((1 - p["price"] / p["compare_at_price"]) * 100, 1)
        if p["compare_at_price"] > p["price"]
        else 0,
        "tags": p["tags"],
        "sizes_available": p["sizes_available"],
        "stock_per_size": p["stock_per_size"],
        "is_sale": p["is_sale"],
        "is_clearance": p["is_clearance"],
        "bestseller_score": p["bestseller_score"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 3 — get_order
# ═══════════════════════════════════════════════════════════════════════════════

def get_order(order_id: str) -> Dict[str, Any]:
    """
    Fetch full details for a single order by ID.
    Also enriches the response with the associated product info.

    Returns
    -------
    dict – order + product snapshot, or an error dict if not found.
    """
    orders = get_orders()
    products = get_products()
    oid = order_id.strip().upper()

    if oid not in orders:
        return {"error": f"Order '{oid}' not found. Please double-check the order ID."}

    o = orders[oid]
    product_info = products.get(o["product_id"])

    result = {
        "order_id": o["order_id"],
        "order_date": o["order_date"],
        "product_id": o["product_id"],
        "size": o["size"],
        "price_paid": o["price_paid"],
        "customer_id": o["customer_id"],
        "shipping_status": o.get("shipping_status", "unknown"),
        "tracking_number": o.get("tracking_number", ""),
        "estimated_delivery": o.get("estimated_delivery", ""),
    }

    if product_info:
        result["product"] = {
            "title": product_info["title"],
            "vendor": product_info["vendor"],
            "is_sale": product_info["is_sale"],
            "is_clearance": product_info["is_clearance"],
            "tags": product_info["tags"],
        }
    else:
        result["product"] = {"note": "Product details unavailable."}

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 4 — evaluate_return
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_return(order_id: str) -> Dict[str, Any]:
    """
    Evaluate whether an order is eligible for return based on policies.

    Steps
    -----
    1. Fetch order & product.
    2. Determine item type (clearance → sale → normal).
    3. Check vendor-specific overrides.
    4. Compute days since purchase and compare to allowed window.

    Returns
    -------
    dict with:
      - eligible : bool
      - reason   : str  (human-readable explanation)
      - policy_applied : str
      - refund_type : str | None
      - days_since_order : int
    """
    order_result = get_order(order_id)
    if "error" in order_result:
        return order_result

    # Parse dates
    today = datetime.strptime(CURRENT_DATE, "%Y-%m-%d")
    order_date = datetime.strptime(order_result["order_date"], "%Y-%m-%d")
    days_since = (today - order_date).days

    product = order_result.get("product", {})
    vendor = product.get("vendor", "")
    is_clearance = product.get("is_clearance", False)
    is_sale = product.get("is_sale", False)

    # ── Rule engine ────────────────────────────────────────────────────────────
    # Clearance → final sale
    if is_clearance:
        return {
            "eligible": False,
            "reason": (
                "This is a clearance item. Per our policy, clearance items are "
                "final sale and not eligible for return or exchange."
            ),
            "policy_applied": "Clearance — Final Sale",
            "refund_type": None,
            "days_since_order": days_since,
            "order_summary": _order_summary(order_result),
        }

    # Vendor exceptions
    if "aurelia couture" in vendor.lower():
        window = 14  # normal window, but exchanges only
        if days_since <= window:
            return {
                "eligible": True,
                "reason": (
                    f"Aurelia Couture items are eligible for exchange only (no refunds). "
                    f"Your order was placed {days_since} day(s) ago, within the "
                    f"{window}-day window."
                ),
                "policy_applied": "Vendor Exception — Aurelia Couture (Exchange Only)",
                "refund_type": "exchange_only",
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }
        else:
            return {
                "eligible": False,
                "reason": (
                    f"Aurelia Couture items allow exchanges within {window} days. "
                    f"Your order was placed {days_since} day(s) ago — past the window."
                ),
                "policy_applied": "Vendor Exception — Aurelia Couture (Window Expired)",
                "refund_type": None,
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }

    if "nocturne" in vendor.lower():
        window = 21  # extended
        refund = "store_credit" if is_sale else "full_refund"
        if days_since <= window:
            return {
                "eligible": True,
                "reason": (
                    f"Nocturne items have an extended {window}-day return window. "
                    f"Your order was placed {days_since} day(s) ago. "
                    f"{'Store credit will be issued (sale item).' if is_sale else 'Full refund applies.'}"
                ),
                "policy_applied": f"Vendor Exception — Nocturne ({window}-day window)",
                "refund_type": refund,
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }
        else:
            return {
                "eligible": False,
                "reason": (
                    f"Nocturne items have an extended {window}-day return window, "
                    f"but your order was placed {days_since} day(s) ago — past the window."
                ),
                "policy_applied": f"Vendor Exception — Nocturne (Window Expired)",
                "refund_type": None,
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }

    # Sale items → 7-day window, store credit only
    if is_sale:
        window = 7
        if days_since <= window:
            return {
                "eligible": True,
                "reason": (
                    f"This is a sale item. Returns are accepted within {window} days "
                    f"for store credit only. Your order was placed {days_since} day(s) ago."
                ),
                "policy_applied": "Sale Item — 7-Day Window (Store Credit)",
                "refund_type": "store_credit",
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }
        else:
            return {
                "eligible": False,
                "reason": (
                    f"Sale items must be returned within {window} days. "
                    f"Your order was placed {days_since} day(s) ago — past the window."
                ),
                "policy_applied": "Sale Item — Window Expired",
                "refund_type": None,
                "days_since_order": days_since,
                "order_summary": _order_summary(order_result),
            }

    # Normal items → 14-day window, full refund
    window = 14
    if days_since <= window:
        return {
            "eligible": True,
            "reason": (
                f"Normal return policy applies. Returns accepted within {window} days "
                f"for a full refund. Your order was placed {days_since} day(s) ago."
            ),
            "policy_applied": "Normal Item — 14-Day Window (Full Refund)",
            "refund_type": "full_refund",
            "days_since_order": days_since,
            "order_summary": _order_summary(order_result),
        }
    else:
        return {
            "eligible": False,
            "reason": (
                f"Normal items must be returned within {window} days. "
                f"Your order was placed {days_since} day(s) ago — past the window."
            ),
            "policy_applied": "Normal Item — Window Expired",
            "refund_type": None,
            "days_since_order": days_since,
            "order_summary": _order_summary(order_result),
        }


def _order_summary(order_result: dict) -> dict:
    """Compact order summary for inclusion in return evaluation."""
    return {
        "order_id": order_result["order_id"],
        "order_date": order_result["order_date"],
        "product_id": order_result["product_id"],
        "product_title": order_result.get("product", {}).get("title", "N/A"),
        "vendor": order_result.get("product", {}).get("vendor", "N/A"),
        "size": order_result["size"],
        "price_paid": order_result["price_paid"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 5 — get_sizing_info
# ═══════════════════════════════════════════════════════════════════════════════

def get_sizing_info(
    product_id: Optional[str] = None,
    source_region: Optional[str] = None,
    source_size: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve sizing guidance. Optionally product-specific.

    Parameters
    ----------
    product_id : str | None
        If provided, returns vendor-specific fit advice + product tags for the item.
    source_region : str | None
        Customer's sizing region ('UK' or 'EU') for conversion lookup.
    source_size : str | None
        Customer's size in their region (e.g. '12') to convert to US.

    Returns
    -------
    dict with measurement_chart, fit_guidance, vendor notes, and optional conversion.
    """
    guide = get_sizing_guide()
    result: Dict[str, Any] = {
        "measurement_chart_inches": guide["measurement_chart_inches"],
        "general_tips": guide["general_tips"],
    }

    # Size conversion
    if source_region and source_size:
        region_key = f"US_to_{source_region.upper()}"
        conversion = guide["size_conversion"].get(region_key, {})
        # Reverse lookup: find US size whose mapped value equals source_size
        us_size = None
        for us, foreign in conversion.items():
            if foreign == source_size:
                us_size = us
                break
        if us_size:
            result["size_conversion"] = {
                "from": f"{source_region.upper()} {source_size}",
                "to_us": us_size,
            }
        else:
            result["size_conversion"] = {
                "note": f"Could not find a US equivalent for {source_region.upper()} {source_size}."
            }

    # Product-specific guidance
    if product_id:
        products = get_products()
        pid = product_id.strip().upper()
        p = products.get(pid)
        if p:
            vendor = p["vendor"]
            tags = p["tags"]
            result["product_info"] = {
                "product_id": pid,
                "title": p["title"],
                "vendor": vendor,
                "sizes_available": p["sizes_available"],
                "stock_per_size": p["stock_per_size"],
            }
            # Vendor-specific note
            vendor_notes = guide.get("vendor_sizing_notes", {})
            result["vendor_sizing_note"] = vendor_notes.get(vendor, "No specific sizing notes for this vendor.")
            # Fit guidance based on tags
            fit_tips = guide.get("fit_guidance", {})
            applicable_tips = {tag: fit_tips[tag] for tag in tags if tag in fit_tips}
            if applicable_tips:
                result["fit_guidance_for_product"] = applicable_tips
        else:
            result["product_info"] = {"error": f"Product '{pid}' not found."}

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 6 — search_faqs
# ═══════════════════════════════════════════════════════════════════════════════

def search_faqs(query: str) -> Dict[str, Any]:
    """
    Search the FAQ knowledge base for answers matching a query.

    Uses simple keyword matching against FAQ questions and returns
    the most relevant Q&A pairs.

    Parameters
    ----------
    query : str
        The customer's question or topic keywords.

    Returns
    -------
    dict with matching FAQ entries.
    """
    faqs = get_faqs()
    query_lower = query.lower()
    query_words = set(query_lower.split())

    matches = []
    for category, items in faqs.get("categories", {}).items():
        for faq in items:
            q_lower = faq["q"].lower()
            # Score by word overlap
            q_words = set(q_lower.split())
            overlap = len(query_words & q_words)
            # Also check substring match
            substring_match = any(w in q_lower for w in query_words if len(w) > 3)
            if overlap >= 2 or substring_match:
                matches.append({
                    "category": category,
                    "question": faq["q"],
                    "answer": faq["a"],
                    "relevance": overlap + (1 if substring_match else 0),
                })

    matches.sort(key=lambda x: x["relevance"], reverse=True)
    return {
        "count": len(matches),
        "results": matches[:5],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Schema — OpenAI function-calling definitions
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search the product catalog with optional filters. "
                "Use this to find products matching customer preferences such as "
                "occasion, style, price range, size, vendor, sale status, etc. "
                "Returns a list of matching products sorted by relevance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Tag keywords to filter by (e.g. 'modest', 'evening', "
                            "'long-sleeve', 'fitted'). ALL tags must match."
                        ),
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price (inclusive).",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum price (inclusive).",
                    },
                    "size": {
                        "type": "string",
                        "description": (
                            "Required size (e.g. '8', '10'). Only products with "
                            "stock > 0 in this size are returned."
                        ),
                    },
                    "vendor": {
                        "type": "string",
                        "description": "Vendor name to filter by (substring match).",
                    },
                    "is_sale": {
                        "type": "boolean",
                        "description": "If true, only sale items; if false, only non-sale.",
                    },
                    "is_clearance": {
                        "type": "boolean",
                        "description": "If true, only clearance items; if false, only non-clearance.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["bestseller_score", "price_asc", "price_desc"],
                        "description": "Sort order. Default is bestseller_score (highest first).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 5).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": (
                "Get full details for a specific product by its product_id. "
                "Use this when you need complete information about a specific product "
                "including all sizes, stock levels, and pricing details."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID (e.g. 'P0001').",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "Fetch details of a specific order by order_id. "
                "Returns order date, product info, size, price paid, customer ID, "
                "shipping status, tracking number, and estimated delivery date. "
                "Use this to look up order status, tracking, or details before evaluating returns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID (e.g. 'O0001').",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_return",
            "description": (
                "Evaluate whether an order is eligible for return or exchange. "
                "Checks the order date, product type (normal/sale/clearance), "
                "and vendor-specific policies to determine eligibility, "
                "refund type, and provide a clear explanation. "
                "Use this when a customer asks about returning an item."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to evaluate for return eligibility.",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sizing_info",
            "description": (
                "Retrieve sizing guidance including measurement charts, "
                "size conversion (US/UK/EU), vendor-specific fit notes, "
                "and product-specific sizing advice. Use this when a customer "
                "asks about sizing, fit, measurements, or size conversion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": (
                            "Optional product ID to get product-specific sizing advice "
                            "including vendor notes and fit guidance."
                        ),
                    },
                    "source_region": {
                        "type": "string",
                        "enum": ["UK", "EU"],
                        "description": "Customer's sizing region for conversion (UK or EU).",
                    },
                    "source_size": {
                        "type": "string",
                        "description": "Customer's size in their region (e.g. '12') to convert to US.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_faqs",
            "description": (
                "Search the FAQ knowledge base for answers to common questions. "
                "Covers shipping, payment, returns, products, and account topics. "
                "Use this for general inquiries that are not product-specific or order-specific."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The customer's question or keywords to search for.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatcher — maps function name → callable
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_MAP = {
    "search_products": search_products,
    "get_product": get_product,
    "get_order": get_order,
    "evaluate_return": evaluate_return,
    "get_sizing_info": get_sizing_info,
    "search_faqs": search_faqs,
}
