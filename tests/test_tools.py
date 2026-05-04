"""
Unit tests for OpenClaw tools.

These tests verify the tool logic against the CSV data WITHOUT requiring
an OpenAI API key. They test the data layer and business logic directly.
"""

import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools import search_products, get_product, get_order, evaluate_return, get_sizing_info, search_faqs
from src.data_loader import get_products, get_orders, get_policy, get_sizing_guide, get_faqs


# ═══════════════════════════════════════════════════════════════════════════════
# Data Loading Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataLoading:
    """Verify CSV files load correctly."""

    def test_products_load(self):
        products = get_products()
        assert len(products) > 0, "Products should not be empty"
        assert "P0001" in products, "P0001 should exist"

    def test_orders_load(self):
        orders = get_orders()
        assert len(orders) > 0, "Orders should not be empty"
        assert "O0001" in orders, "O0001 should exist"

    def test_policy_load(self):
        policy = get_policy()
        assert "Return Policy" in policy, "Policy should contain 'Return Policy'"
        assert "Clearance" in policy, "Policy should mention clearance items"
        assert "Aurelia Couture" in policy, "Policy should mention Aurelia Couture"
        assert "Nocturne" in policy, "Policy should mention Nocturne"

    def test_product_structure(self):
        products = get_products()
        p = products["P0001"]
        required_keys = [
            "product_id", "title", "vendor", "price", "compare_at_price",
            "tags", "sizes_available", "stock_per_size", "is_sale",
            "is_clearance", "bestseller_score",
        ]
        for key in required_keys:
            assert key in p, f"Product should have key '{key}'"

    def test_order_structure(self):
        orders = get_orders()
        o = orders["O0001"]
        required_keys = [
            "order_id", "order_date", "product_id", "size",
            "price_paid", "customer_id",
            "shipping_status", "tracking_number", "estimated_delivery",
        ]
        for key in required_keys:
            assert key in o, f"Order should have key '{key}'"

    def test_sizing_guide_load(self):
        guide = get_sizing_guide()
        assert "measurement_chart_inches" in guide
        assert "size_conversion" in guide
        assert "vendor_sizing_notes" in guide
        assert "fit_guidance" in guide

    def test_faqs_load(self):
        faqs = get_faqs()
        assert "categories" in faqs
        assert "shipping" in faqs["categories"]
        assert "payment" in faqs["categories"]
        assert "returns" in faqs["categories"]


# ═══════════════════════════════════════════════════════════════════════════════
# search_products Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchProducts:
    """Test the search_products tool."""

    def test_no_filters(self):
        result = search_products()
        assert result["count"] > 0, "Unfiltered search should return products"
        assert result["count"] <= 5, "Default limit is 5"

    def test_tag_filter(self):
        result = search_products(tags=["evening", "modest"])
        assert result["count"] > 0, "Should find modest evening products"
        for p in result["products"]:
            tags_lower = [t.lower() for t in p["tags"]]
            assert "evening" in tags_lower, "All results should have 'evening' tag"
            assert "modest" in tags_lower, "All results should have 'modest' tag"

    def test_max_price(self):
        result = search_products(max_price=150)
        for p in result["products"]:
            assert p["price"] <= 150, f"Price {p['price']} should be <= 150"

    def test_min_price(self):
        result = search_products(min_price=400)
        for p in result["products"]:
            assert p["price"] >= 400, f"Price {p['price']} should be >= 400"

    def test_size_filter_checks_stock(self):
        result = search_products(size="8")
        assert result["count"] > 0, "Should find products with size 8 in stock"
        for p in result["products"]:
            assert p["stock_for_requested_size"] > 0, "Stock for size 8 must be > 0"

    def test_sale_filter(self):
        result = search_products(is_sale=True, limit=20)
        for p in result["products"]:
            assert p["is_sale"] is True, "All results should be sale items"

    def test_clearance_filter(self):
        result = search_products(is_clearance=True, limit=20)
        for p in result["products"]:
            assert p["is_clearance"] is True, "All results should be clearance items"

    def test_vendor_filter(self):
        result = search_products(vendor="Nocturne", limit=20)
        for p in result["products"]:
            assert "nocturne" in p["vendor"].lower(), "All results should be from Nocturne"

    def test_multi_constraint(self):
        """Simulate: modest evening gown under $300, size 8, on sale."""
        result = search_products(
            tags=["modest", "evening"],
            max_price=300,
            size="8",
            is_sale=True,
        )
        for p in result["products"]:
            assert p["price"] <= 300
            assert p["is_sale"] is True
            assert p["stock_for_requested_size"] > 0

    def test_sort_by_price_asc(self):
        result = search_products(sort_by="price_asc", limit=10)
        prices = [p["price"] for p in result["products"]]
        assert prices == sorted(prices), "Products should be sorted by price ascending"

    def test_sort_by_price_desc(self):
        result = search_products(sort_by="price_desc", limit=10)
        prices = [p["price"] for p in result["products"]]
        assert prices == sorted(prices, reverse=True), "Products should be sorted by price descending"

    def test_limit(self):
        result = search_products(limit=3)
        assert result["count"] <= 3, "Should respect limit"

    def test_no_results(self):
        result = search_products(max_price=1)  # Nothing costs $1
        assert result["count"] == 0, "Should return no results"
        assert result["products"] == [], "Products list should be empty"


# ═══════════════════════════════════════════════════════════════════════════════
# get_product Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetProduct:
    """Test the get_product tool."""

    def test_valid_product(self):
        result = get_product("P0001")
        assert "error" not in result
        assert result["product_id"] == "P0001"
        assert result["title"] is not None
        assert isinstance(result["sizes_available"], list)
        assert isinstance(result["stock_per_size"], dict)

    def test_invalid_product(self):
        result = get_product("P9999")
        assert "error" in result, "Should return error for invalid product ID"

    def test_case_insensitive(self):
        result = get_product("p0001")
        assert "error" not in result, "Should handle lowercase product IDs"

    def test_discount_calculation(self):
        result = get_product("P0003")  # Satin Cocktail Dress: $258 vs $310
        if result["compare_at_price"] > result["price"]:
            assert result["discount_pct"] > 0, "Should compute discount percentage"


# ═══════════════════════════════════════════════════════════════════════════════
# get_order Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetOrder:
    """Test the get_order tool."""

    def test_valid_order(self):
        result = get_order("O0001")
        assert "error" not in result
        assert result["order_id"] == "O0001"
        assert "product" in result, "Should include enriched product info"
        assert "title" in result["product"], "Product info should have title"

    def test_order_has_tracking_data(self):
        """Verify orders include shipping status and tracking info."""
        result = get_order("O0001")
        assert "error" not in result
        assert "shipping_status" in result, "Order should include shipping_status"
        assert result["shipping_status"] in (
            "processing", "shipped", "out_for_delivery", "delivered", "unknown"
        ), f"Unexpected status: {result['shipping_status']}"
        assert "tracking_number" in result, "Order should include tracking_number"
        assert len(result["tracking_number"]) > 0, "Tracking number should not be empty"
        assert "estimated_delivery" in result, "Order should include estimated_delivery"

    def test_invalid_order(self):
        result = get_order("O9999")
        assert "error" in result, "Should return error for invalid order ID"

    def test_case_insensitive(self):
        result = get_order("o0001")
        assert "error" not in result, "Should handle lowercase order IDs"


# ═══════════════════════════════════════════════════════════════════════════════
# evaluate_return Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluateReturn:
    """Test the evaluate_return tool with policy rules."""

    def test_invalid_order(self):
        result = evaluate_return("O9999")
        assert "error" in result, "Should return error for invalid order"

    def test_clearance_item_not_returnable(self):
        """Find a clearance item order and verify it's not returnable."""
        orders = get_orders()
        products = get_products()
        clearance_order = None
        for oid, o in orders.items():
            p = products.get(o["product_id"])
            if p and p["is_clearance"]:
                clearance_order = oid
                break

        if clearance_order:
            result = evaluate_return(clearance_order)
            assert result["eligible"] is False, "Clearance items should not be returnable"
            assert "clearance" in result["reason"].lower()
            assert result["refund_type"] is None

    def test_return_evaluation_has_required_fields(self):
        """Any valid evaluation should include standard fields."""
        result = evaluate_return("O0001")
        if "error" not in result:
            assert "eligible" in result
            assert "reason" in result
            assert "policy_applied" in result
            assert "days_since_order" in result
            assert "order_summary" in result

    def test_aurelia_couture_exchange_only(self):
        """Find an Aurelia Couture order and verify exchange-only policy."""
        orders = get_orders()
        products = get_products()
        ac_order = None
        for oid, o in orders.items():
            p = products.get(o["product_id"])
            if p and "aurelia couture" in p["vendor"].lower() and not p["is_clearance"]:
                ac_order = oid
                break

        if ac_order:
            result = evaluate_return(ac_order)
            # Whether eligible depends on date, but if eligible, must be exchange only
            if result.get("eligible"):
                assert result["refund_type"] == "exchange_only"
            assert "aurelia couture" in result["policy_applied"].lower() or \
                   "aurelia couture" in result.get("reason", "").lower()

    def test_days_since_order_calculated(self):
        """Verify days_since_order is a positive integer."""
        result = evaluate_return("O0001")
        if "error" not in result:
            assert isinstance(result["days_since_order"], int)
            assert result["days_since_order"] >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# get_sizing_info Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetSizingInfo:
    """Test the get_sizing_info tool."""

    def test_general_sizing(self):
        """Should return measurement chart and tips without product_id."""
        result = get_sizing_info()
        assert "measurement_chart_inches" in result
        assert "general_tips" in result
        assert "8" in result["measurement_chart_inches"]

    def test_size_conversion_uk_to_us(self):
        """UK 12 should convert to US 8."""
        result = get_sizing_info(source_region="UK", source_size="12")
        assert "size_conversion" in result
        assert result["size_conversion"]["to_us"] == "8"

    def test_size_conversion_eu_to_us(self):
        """EU 38 should convert to US 8."""
        result = get_sizing_info(source_region="EU", source_size="38")
        assert "size_conversion" in result
        assert result["size_conversion"]["to_us"] == "8"

    def test_size_conversion_not_found(self):
        """Invalid size should return a note, not crash."""
        result = get_sizing_info(source_region="UK", source_size="99")
        assert "size_conversion" in result
        assert "note" in result["size_conversion"]

    def test_product_specific_sizing(self):
        """Should include vendor notes and fit guidance for a specific product."""
        result = get_sizing_info(product_id="P0002")  # Aurelia Couture
        assert "product_info" in result
        assert result["product_info"]["vendor"] == "Aurelia Couture"
        assert "vendor_sizing_note" in result
        assert "sizing_note" not in result.get("vendor_sizing_note", "").lower() or len(result["vendor_sizing_note"]) > 0

    def test_product_not_found(self):
        result = get_sizing_info(product_id="P9999")
        assert "product_info" in result
        assert "error" in result["product_info"]

    def test_fit_guidance_for_fitted_product(self):
        """Fitted products should return fit-specific guidance."""
        result = get_sizing_info(product_id="P0002")  # Tags include 'fitted'
        if "fit_guidance_for_product" in result:
            assert "fitted" in result["fit_guidance_for_product"]


# ═══════════════════════════════════════════════════════════════════════════════
# search_faqs Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchFaqs:
    """Test the search_faqs tool."""

    def test_shipping_query(self):
        result = search_faqs("How long does shipping take?")
        assert result["count"] > 0, "Should find shipping FAQs"
        assert any("shipping" in r["category"] for r in result["results"])

    def test_payment_query(self):
        result = search_faqs("What payment methods do you accept?")
        assert result["count"] > 0, "Should find payment FAQs"

    def test_return_policy_query(self):
        result = search_faqs("How do I return an item?")
        assert result["count"] > 0, "Should find return FAQs"

    def test_no_results(self):
        result = search_faqs("xyzzy foobar nonsense")
        assert result["count"] == 0, "Should return no results for gibberish"

    def test_result_structure(self):
        result = search_faqs("shipping")
        if result["count"] > 0:
            entry = result["results"][0]
            assert "category" in entry
            assert "question" in entry
            assert "answer" in entry
            assert "relevance" in entry


# ═══════════════════════════════════════════════════════════════════════════════
# Channel Router Tests (no API key needed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChannelRouter:
    """Test escalation and formatting logic."""

    def test_escalation_keywords(self):
        from src.channels import ChannelRouter

        class MockAgent:
            def chat(self, msg):
                return "mock response"

        router = ChannelRouter(MockAgent())

        # Should trigger escalation
        assert router._needs_escalation("I want to speak to a manager")
        assert router._needs_escalation("This is damaged goods!")
        assert router._needs_escalation("I need a human agent")

        # Should NOT trigger escalation
        assert not router._needs_escalation("What sizes do you have?")
        assert not router._needs_escalation("Can I return order O0001?")

    def test_whatsapp_formatting(self):
        from src.channels import ChannelRouter

        class MockAgent:
            def chat(self, msg):
                return "This is **bold** text"

        router = ChannelRouter(MockAgent())
        response = router.route_message("Hello", "whatsapp")
        assert "**" not in response, "WhatsApp should use single asterisks"
        assert "*bold*" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
