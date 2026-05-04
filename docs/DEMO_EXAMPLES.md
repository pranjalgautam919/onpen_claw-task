# OpenClaw — Demo Examples

These examples demonstrate the agent's behavior across all required scenarios.
Run them with `python main.py --demo` or test interactively with `python main.py`.

---

## Demo 1: Personal Shopper — Modest Evening Gown (WhatsApp)

### Input
```
Channel: WhatsApp
"Hi! I need a modest evening gown under $300 in size 8. I prefer something on sale."
```

### Expected Agent Behavior
1. **Tool called**: `search_products` with:
   - `tags: ["modest", "evening"]`
   - `max_price: 300`
   - `size: "8"`
   - `is_sale: true`
   - `sort_by: "bestseller_score"`

2. **Multi-constraint reasoning**:
   - Filters for both "modest" AND "evening" tags
   - Ensures price ≤ $300
   - Only includes products with size 8 in stock
   - Prioritises sale items as requested
   - Sorts by bestseller score for best recommendations

3. **Expected matches** (examples):
   - P0036 — Modest Lace Evening Gown by Moonlit ($289, sale, score 83)
   - P0071 — Modest Velvet Maxi by Moonlit ($248, sale, score 79)
   - P0098 — Modest Wrap Maxi Gown by Moonlit ($268, sale, score 81)
   - P0025 — Pearl-Detail Evening Gown by Nocturne ($266, sale, score 87)

4. **Response should explain**:
   - Why each dress fits the "modest" and "evening" criteria
   - Current price vs. original price (savings)
   - Stock availability for size 8
   - Bestseller ranking as social proof
   - WhatsApp formatting (single asterisks, emoji prefix)

---

## Demo 2: Personal Shopper — Garden Party Dress (Chat)

### Input
```
Channel: Chat
"I'm looking for a casual dress for a garden party, size 10, under $200."
```

### Expected Agent Behavior
1. **Tool called**: `search_products` with:
   - `tags: ["casual"]` (and possibly "floral" or "garden")
   - `max_price: 200`
   - `size: "10"`

2. **Expected matches** (examples):
   - P0007 — Floral Garden Party Dress by Bella Rosa ($145, score 70)
   - P0027 — Puff Sleeve Midi by Bella Rosa ($155, score 66)
   - P0045 — Tiered Cotton Maxi by Wanderlust ($183, sale, score 60)
   - P0001 — Classic A-Line Midi Dress by Bella Rosa ($137, score 72)

3. **Response should**:
   - Recommend dresses suitable for a garden party setting
   - Highlight floral/outdoor-appropriate options
   - Note any sale items for extra value
   - Confirm size 10 availability

---

## Demo 3: Customer Support — Return Inquiry (WhatsApp)

### Input
```
Channel: WhatsApp
"Order O0043 — I bought this dress last week. It doesn't fit. Can I return it?"
```

### Expected Agent Behavior
1. **Tool called**: `evaluate_return("O0043")`

2. **Internal evaluation**:
   - Fetches order O0043: product P0079 (Embroidered Boho Maxi), ordered 2026-01-18
   - Product is by Bella Rosa, NOT sale, NOT clearance
   - Days since order: ~100 days (well past 14-day window)
   - Normal return policy: 14 days → **NOT ELIGIBLE**

3. **Response should**:
   - Clearly state the order is not eligible for return
   - Explain the 14-day return window
   - Show how many days have passed
   - Be empathetic but firm about policy
   - Suggest alternatives (exchange if applicable, or contact support)

---

## Demo 4: Customer Support — Clearance Return Attempt (Chat)

### Input
```
Channel: Chat
"Can I return order O0012? I changed my mind about it."
```

### Expected Agent Behavior
1. **Tool called**: `evaluate_return("O0012")`

2. **Internal evaluation**:
   - Fetches order O0012: product P0035 (Chambray Shift Dress)
   - Product IS a clearance item (`is_clearance: true`)
   - Clearance policy: **Final sale — no returns or exchanges**

3. **Response should**:
   - Clearly state clearance items are final sale
   - Reference the specific policy rule
   - Be polite but definitive
   - Not offer alternatives that contradict policy

---

## Demo 5: Edge Case — Invalid Order ID (Chat)

### Input
```
Channel: Chat
"What's the status of order O9999?"
```

### Expected Agent Behavior
1. **Tool called**: `get_order("O9999")`

2. **Tool returns**: `{"error": "Order 'O9999' not found. Please double-check the order ID."}`

3. **Response should**:
   - Inform the customer that the order was not found
   - NOT fabricate any order details
   - Ask the customer to verify the order ID
   - Offer to help with the correct ID
   - Possibly suggest contacting support if the issue persists

---

## Additional Scenarios for Interactive Testing

### Sizing Question
```
"What sizes does the Crystal-Embellished Gown (P0020) come in? Is size 12 available?"
```
Expected: Agent calls `get_product("P0020")`, reports all sizes and stock for size 12.

### Vendor-Specific Return (Aurelia Couture)
```
"I want to return order O0007. The Organza Ball Gown doesn't match my outfit."
```
Expected: Agent calls `evaluate_return("O0007")`, applies Aurelia Couture exchange-only policy.

### Sale Item Return
```
"Can I get a refund for order O0005?"
```
Expected: Agent evaluates, notes it's a normal item by Bella Rosa, checks date vs. 14-day window.

### Complex Multi-Constraint Shopping
```
"I need an elegant evening gown from either Nocturne or Aurelia Couture, size 12, 
budget is $400, and I'd like something with a high bestseller score."
```
Expected: Agent calls `search_products` with appropriate filters, may call twice (once per vendor), presents top options sorted by bestseller score.

### Human Escalation
```
"This is unacceptable! I want to speak to a manager about my damaged order!"
```
Expected: Triggers escalation keywords ("manager", "damaged"), routes to human agent message.
