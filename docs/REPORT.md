# OpenClaw — Brief Project Report

## Purpose

OpenClaw is a retail AI assistant prototype that simulates monitoring **web chat** and **WhatsApp** channels. It provides fast first responses for sizing help, order status, general FAQs, and shopping recommendations, while routing sensitive cases to a human agent.

## Design and workflow

1. **Ingress** — Messages arrive through a channel simulator (`chat` or `whatsapp`). A lightweight router can short-circuit to a human handoff when escalation keywords appear (for example, “complaint”, “speak to a person”).
2. **Agent** — A single OpenAI-backed agent (`OpenClawAgent`) handles both “personal shopper” and “support” intents. Intent is not hardcoded; the model chooses **function tools** based on the user message.
3. **Tools** — All catalog, order, policy, sizing, and FAQ facts come from structured tools that return JSON. The model composes the final reply from that JSON, which limits fabrication of SKUs, prices, or policy rules.
4. **Egress** — Replies are optionally formatted for WhatsApp (for example, bold markers normalized, short prefix).

For a deeper diagram and tool matrix, see [ARCHITECTURE.md](ARCHITECTURE.md).

## How inquiry types are handled

| Category | Tools | Behavior |
|----------|--------|----------|
| Sizing | `get_sizing_info`, sometimes `get_product` | Measurement chart, vendor fit notes, optional UK/EU to US conversion, product-specific stock by size. |
| Order status | `get_order` | Shipping status, tracking number, estimated delivery, linked product snapshot. |
| Shopping | `search_products`, `get_product` | Multi-constraint catalog search (tags, price, size in stock, sale/clearance, bestseller sort). |
| Returns | `evaluate_return` | Deterministic rule engine: clearance, vendor exceptions, sale vs normal windows and refund types. |
| General / FAQ | `search_faqs` | Keyword-scored matches from `data/faqs.json`. |
| Complex / human | Router keywords + prompt instructions | Polite handoff when automation is inappropriate. |

## Hallucination controls

- Tools return explicit `{"error": "..."}` for unknown `order_id` or `product_id`; the prompt instructs the model not to invent replacements.
- Return eligibility numbers (windows, refund type) are computed in Python from order dates and product flags, not inferred by the model alone.
- A fixed **reference date** (`CURRENT_DATE` in `src/config.py`) keeps return-window demos reproducible; align it with your evaluation date if needed.

## Assumptions

- **OpenClaw** is the name of this in-repository assistant, not a third-party product integration.
- **WhatsApp and live chat** are simulated in the CLI. Production would replace the router with webhooks (for example Meta WhatsApp Cloud API or Twilio) calling the same agent entrypoint.
- **Policy text** (`data/policy.txt`) is embedded in the system prompt for explanations; executable return logic lives in `evaluate_return` and should stay consistent with that file.
- **LLM** — Requires `OPENAI_API_KEY`. Run `pytest tests/test_tools.py` to validate tools without any API access.

## Demo examples (required coverage)

Documented step-by-step in [DEMO_EXAMPLES.md](DEMO_EXAMPLES.md) and runnable with `python main.py --demo` (after setting the API key):

- Two shopping scenarios (modest evening gown on WhatsApp; garden party dress on chat).
- Two support scenarios (return eligibility on WhatsApp; clearance return on chat).
- One edge case: invalid order id `O9999`.

## CLI entry points

| Command | Role |
|---------|------|
| `python main.py` | Interactive chat |
| `python main.py --channel` | Choose `chat` or `whatsapp` per message |
| `python main.py --demo` | Runs all scripted scenarios |

---

*This report complements [ARCHITECTURE.md](ARCHITECTURE.md) for assignment submission.*
