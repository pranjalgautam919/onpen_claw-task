# OpenClaw — Architecture Document

## 1. System Overview

OpenClaw is a single-agent system that dynamically switches between two operational modes:

```
┌──────────────────────────────────────────────────────┐
│                   OpenClaw Agent                      │
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐    │
│  │ Personal Shopper │    │  Customer Support    │    │
│  │  (Revenue Mode)  │    │  (Operations Mode)   │    │
│  └────────┬────────┘    └──────────┬───────────┘    │
│           │                        │                 │
│           ▼                        ▼                 │
│  ┌─────────────────────────────────────────────┐    │
│  │            Tool Dispatcher                   │    │
│  │  search_products │ get_product │ get_order   │    │
│  │  evaluate_return │ get_sizing_info            │    │
│  │  search_faqs                                  │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                                │
│                     ▼                                │
│  ┌─────────────────────────────────────────────┐    │
│  │       Data Layer (CSV + JSON + Policy)       │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
          ▲                              │
          │         Channel Router       │
          │    ┌──────┐  ┌──────────┐   │
          └────│ Chat │  │ WhatsApp │───┘
               └──────┘  └──────────┘
```

### Why a Single Agent?

Rather than running two separate agents (shopper + support), we use a **single agent with mode detection**. This is preferable because:

1. **Simplicity** — One conversation context means the agent can handle mixed queries (e.g., "I bought a dress from order O0043, can I return it? Also, do you have anything similar in size 10?").
2. **Shared context** — Product knowledge is shared between modes, enabling richer responses.
3. **Lower latency** — No inter-agent routing or handoff overhead.
4. **Coherent conversation** — The LLM naturally detects intent from the message and selects the appropriate tools.

The system prompt clearly defines both modes and their behavioral contracts, and the LLM's function-calling capability handles mode selection implicitly through tool choice.

---

## 2. Tool Design

### 2.1 Tool Architecture

Each tool follows a strict contract:

- **Input**: Typed parameters validated by the OpenAI function-calling schema
- **Output**: Plain Python dict that gets JSON-serialised
- **Side effects**: None — all tools are pure reads
- **Error handling**: Returns `{"error": "..."}` rather than raising exceptions

### 2.2 Tool Selection Logic

The LLM decides which tools to call based on the user's message. The system prompt provides clear guidance:

| User Intent | Expected Tool(s) |
|---|---|
| "Find me a dress..." | `search_products` → possibly `get_product` for details |
| "What sizes does P0015 come in?" | `get_sizing_info(product_id="P0015")` |
| "I'm a UK 12, what US size?" | `get_sizing_info(source_region="UK", source_size="12")` |
| "What's the status of order O0043?" | `get_order` → reports shipping status + tracking |
| "Can I return order O0012?" | `evaluate_return` (internally calls `get_order`) |
| "Do you have X in size 8?" | `search_products` with size filter |
| "How long does shipping take?" | `search_faqs(query="shipping time")` |
| "What payment methods?" | `search_faqs(query="payment methods")` |

The agent may chain multiple tool calls in a single turn. For example, a shopping query might first `search_products` to find matches, then `get_product` on the top result for full stock details.

### 2.3 Tool Descriptions

**`search_products(filters)`**
- Multi-constraint filtering: tags, price range, size + stock, vendor, sale/clearance status
- Sorting by bestseller_score (default), price ascending, or price descending
- Returns compact summaries to keep token usage efficient
- Size filter automatically checks stock > 0

**`get_product(product_id)`**
- Full product detail including all sizes and per-size stock levels
- Computed discount percentage
- Returns error if product ID doesn't exist

**`get_order(order_id)`**
- Enriches order data with associated product information
- Includes **shipping status** (processing, shipped, out_for_delivery, delivered)
- Includes **tracking number** and **estimated delivery date**
- Returns error if order ID doesn't exist (anti-hallucination)

**`evaluate_return(order_id)`**
- Implements the complete policy rule engine:
  1. Clearance check → final sale, no returns
  2. Vendor exceptions → Aurelia Couture (exchange only), Nocturne (21-day window)
  3. Sale items → 7-day window, store credit only
  4. Normal items → 14-day window, full refund
- Computes days since order and compares to applicable window
- Returns structured result with eligibility, reason, policy applied, and refund type

**`get_sizing_info(product_id?, source_region?, source_size?)`**
- Returns measurement chart (bust/waist/hips in inches for US sizes 2–16)
- US ↔ UK ↔ EU size conversion with reverse lookup
- Vendor-specific fit notes (e.g. "Aurelia Couture runs slightly small")
- Product-specific guidance based on fit tags (fitted vs. relaxed, sleeve type)
- General sizing tips for fabric types and between-size guidance

**`search_faqs(query)`**
- Keyword-matched search over a curated FAQ knowledge base
- Covers: shipping, payment, returns, products, account topics
- Returns grounded answers — prevents the LLM from using training-data guesses
- Scored by word overlap + substring matching, returns top 5

---

## 3. Hallucination Prevention

This is a critical design goal. We employ multiple strategies:

### 3.1 Tool-First Policy
The system prompt explicitly instructs: *"ALWAYS call the appropriate tool before answering — never guess from memory."* The agent cannot answer product or order questions without first retrieving real data.

### 3.2 Grounded Responses
Tool results are injected as `tool` messages in the conversation. The LLM generates its response based on these concrete data points, not parametric knowledge.

### 3.3 Explicit Error Handling
When an order or product is not found, the tool returns a clear error message. The system prompt instructs the agent to relay this honestly rather than fabricating information.

### 3.4 Policy Embedding
The full return policy text is embedded in the system prompt. This ensures the LLM has accurate policy information and doesn't need to rely on (potentially incorrect) training data.

### 3.5 Low Temperature
We use `temperature=0.2` to reduce creative/random generation and keep responses factual.

### 3.6 Tool Call Cap
A maximum of 5 tool calls per turn prevents infinite loops and ensures the agent converges to a response.

---

## 4. Channel Integration

### 4.1 Architecture

The `ChannelRouter` sits between incoming messages and the agent:

```
Customer Message → Channel Router → OpenClaw Agent → Tool Calls → Response → Format → Customer
                        │
                        ├─ Escalation check (keyword-based)
                        └─ Channel-specific formatting
```

### 4.2 Chat Channel
- Standard markdown formatting
- Direct integration path (in production: WebSocket or REST API)

### 4.3 WhatsApp Channel
- Simplified markdown (single asterisks for bold)
- Emoji prefixes for visual context
- In production: would integrate via WhatsApp Business API (Twilio or Meta Cloud API)
- Message templates for structured responses

### 4.4 Escalation Logic
Certain keywords trigger automatic routing to a human agent:
- Complaints, damage claims, legal mentions
- Explicit requests for a human/manager/supervisor
- Multi-order disputes

The escalation response informs the customer that a human agent will follow up and provides support hours.

### 4.5 Inquiry Categories

| Category | Handling |
|---|---|
| Sizing questions | `get_sizing_info` → measurement chart, vendor fit notes, size conversion |
| Order status | `get_order` → shipping status, tracking number, estimated delivery |
| Return requests | `evaluate_return` → full policy evaluation |
| General FAQs | `search_faqs` → grounded answers from curated knowledge base |
| Complex queries | Escalated to human agent |

---

## 5. Data Flow

```
1. Customer types: "I need a modest evening gown under $300 in size 8, on sale"

2. Agent receives message, appends to conversation history

3. OpenAI API call with tool definitions → model returns:
   tool_call: search_products({
     tags: ["modest", "evening"],
     max_price: 300,
     size: "8",
     is_sale: true,
     sort_by: "bestseller_score"
   })

4. Tool executes against products.csv:
   - Filters by tags containing "modest" AND "evening"
   - Filters price ≤ 300
   - Filters size "8" with stock > 0
   - Filters is_sale = true
   - Sorts by bestseller_score descending

5. Results returned to conversation as tool message

6. Model generates natural language response explaining:
   - Which products match and why
   - Price vs. compare_at_price (savings)
   - Stock availability for requested size
   - Bestseller ranking as social proof
```

---

## 6. Design Decisions

| Decision | Rationale |
|---|---|
| Single agent, not multi-agent | Simpler, lower latency, handles mixed queries naturally |
| CSV data, not database | Meets spec requirements, zero infrastructure, easy to inspect |
| OpenAI function-calling | Industry-standard structured tool use, schema validation built-in |
| Policy in system prompt | Ensures LLM has accurate rules without extra tool calls |
| Singleton data cache | Avoids re-reading CSVs on every tool call |
| Channel router pattern | Clean separation of concerns; easy to add new channels |
| Low temperature (0.2) | Factual, consistent responses over creative ones |

---

## 7. Assumptions & Limitations

This section explicitly documents what the system **can** and **cannot** do.

### 7.1 What Is Simulated

| Capability | Status | Detail |
|---|---|---|
| WhatsApp integration | **Simulated** | Channel routing, formatting, and escalation logic are implemented. Actual WhatsApp Business API (Twilio / Meta Cloud API) integration is not connected. The `ChannelRouter` is designed as a plug-in point for real webhook endpoints. |
| Chat integration | **Simulated** | Same as WhatsApp — the routing and formatting layer exists, but no WebSocket/REST server is running. |
| Shipping tracking | **Simulated** | Orders include `shipping_status`, `tracking_number`, and `estimated_delivery` fields generated from order data. In production, these would come from carrier APIs (FedEx, UPS, USPS, DHL). The agent can report status and tracking numbers, but cannot provide real-time GPS location or live carrier updates. |

### 7.2 Data Boundaries

| Data | Available | Not Available |
|---|---|---|
| Products | Title, vendor, price, tags, sizes, stock per size, sale/clearance status, bestseller score | Product images, fabric composition, care instructions, customer reviews |
| Orders | Order date, product, size, price paid, customer ID, shipping status, tracking, est. delivery | Real-time carrier tracking, delivery confirmation signatures, payment method |
| Sizing | US/UK/EU conversion, bust/waist/hip measurement chart, vendor fit notes, fit-type guidance | Weight-based recommendations, body-type matching, garment-specific measurements |
| FAQs | Shipping, payment, returns, products, account (curated knowledge base) | Live inventory counts beyond CSV, real-time promotions, loyalty program details |

### 7.3 Known Limitations

1. **No real-time carrier tracking** — The agent reports the shipping status and tracking number stored in the orders data. It cannot query FedEx/UPS APIs for live updates. If a customer asks "where exactly is my package right now?", the agent should share the tracking number and suggest checking the carrier's website directly.

2. **Sizing guidance is general, not personalized** — The sizing guide includes measurement charts and vendor notes, but cannot account for individual body proportions, personal fit preferences, or garment-specific stretch factors. The agent advises based on standard measurements.

3. **FAQ scope is curated** — The FAQ knowledge base covers the most common topics (shipping, payment, returns, products, accounts). Questions outside this scope (e.g., corporate partnerships, wholesale pricing, sustainability practices) will not have grounded answers. The agent is instructed to use `search_faqs` rather than its training data, and to escalate when no match is found.

4. **No customer authentication** — The agent does not verify that the person asking about an order is the actual customer. In production, this would require identity verification before sharing order details.

5. **Static inventory** — Product stock levels are loaded from CSV at startup. Real-time inventory changes (purchases by other customers, restocking) are not reflected during a session.

---

## 8. Production Considerations

If deploying to production, the following enhancements would be needed:

1. **Real WhatsApp Integration** — Connect the `ChannelRouter` to WhatsApp Business API via Twilio or Meta Cloud API webhooks
2. **Real Chat Integration** — WebSocket or REST endpoint for web chat widget
3. **Database Backend** — Replace CSVs with PostgreSQL for scalability and real-time updates
4. **Carrier API Integration** — Real-time tracking via FedEx/UPS/USPS/DHL APIs
5. **Authentication** — Customer identity verification before order access
6. **Rate Limiting** — Prevent abuse of the AI endpoint
7. **Logging & Analytics** — Track response quality, escalation rates, resolution times
8. **Caching Layer** — Redis for frequently accessed products/orders
9. **Multi-language Support** — For international customers
10. **Personalized Sizing** — ML-based size recommendation using purchase history and return patterns
