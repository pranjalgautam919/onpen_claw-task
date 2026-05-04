"""
OpenClaw Agent – the core agentic loop.

This module implements a conversational agent that:
1. Receives user messages (shopping queries or support requests).
2. Decides which tools to call via OpenAI function-calling.
3. Executes the tools and feeds results back to the LLM.
4. Returns a final natural-language answer grounded in real data.

Hallucination is minimised by:
- Never answering product/order questions without first calling a tool.
- Including the full policy text in the system prompt.
- Instructing the model to refuse rather than guess when data is missing.
"""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOOL_CALLS_PER_TURN,
    CURRENT_DATE,
)
from src.data_loader import get_policy
from src.tools import TOOL_SCHEMAS, TOOL_MAP


# ═══════════════════════════════════════════════════════════════════════════════
# System prompt
# ═══════════════════════════════════════════════════════════════════════════════

def _build_system_prompt() -> str:
    policy = get_policy()
    return f"""You are **OpenClaw**, a premium retail AI assistant for a fashion boutique.
You operate in two modes depending on the customer's need:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE 1 — PERSONAL SHOPPER (Revenue Agent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When a customer asks for product recommendations:
• Use the `search_products` tool with appropriate filters.
• Consider ALL stated constraints: occasion, style, budget, size, sale preference.
• Verify stock for the requested size before recommending.
• Prioritise sale items when the customer mentions deals/discounts/sale.
• Use bestseller_score as a tiebreaker or when the customer wants popular items.
• Explain WHY each recommendation fits (price, style, availability).
• If no products match, say so honestly — never invent products.
• Offer to relax constraints if results are sparse.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE 2 — CUSTOMER SUPPORT (Operations Agent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When a customer asks about an order or return:
• Use `get_order` to fetch order details including **shipping status, tracking
  number, and estimated delivery date**.
• Use `evaluate_return` to check return eligibility.
• Apply the return policy rules precisely — never guess.
• Clearly state: eligible or not, reason, refund type, and any next steps.
• If the order ID is not found, say so — never fabricate order info.
• When reporting order status, include the shipping status and tracking number
  from the tool results. If the status is "delivered", confirm delivery. If
  "shipped" or "out_for_delivery", share the tracking number and estimated
  delivery date.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SIZING GUIDANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When a customer asks about sizing, fit, or size conversion:
• Use the `get_sizing_info` tool. Pass the product_id if the customer
  mentions a specific product.
• If the customer provides a UK or EU size, pass source_region and
  source_size to get the US equivalent.
• Include vendor-specific fit notes (e.g. "Aurelia Couture runs slightly
  small — consider sizing up").
• Reference the measurement chart for precise bust/waist/hip guidance.
• Mention fit-type advice (fitted vs. relaxed) based on product tags.
• NEVER guess measurements — always use tool data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GENERAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• ALWAYS call the appropriate tool before answering — never guess from memory.
• For general questions (shipping, payment, returns policy, account), use
  the `search_faqs` tool to retrieve grounded answers from our FAQ database.
  Do NOT answer general questions from your training knowledge alone.
• If you cannot help, route the query to a human agent with a polite message.
• Be professional, warm, and concise.
• For complex or ambiguous queries that go beyond your tools, suggest the
  customer contact a human agent.
• Today's date is {CURRENT_DATE}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RETURN POLICY (reference)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{policy}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CHAT & WHATSAPP CHANNEL BEHAVIOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You monitor customer-facing chat and WhatsApp channels. For every incoming
message, respond immediately and accurately. Categories you handle:

1. **Sizing questions** — Use `get_sizing_info` (with product_id if known)
   to provide measurement charts, vendor fit notes, and size conversions.
2. **Order status** — Use `get_order` to report shipping status, tracking
   number, and estimated delivery date alongside order details.
3. **General inquiries** — Use `search_faqs` to retrieve grounded answers
   about shipping, payment, returns, and account questions.

If a query is too complex or requires human judgement (complaints, damage
claims, multi-order issues), respond with:
"I'd like to connect you with a team member who can assist further.
A human agent will be with you shortly."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AVAILABLE TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. search_products — filter catalog by tags, price, size, vendor, sale status
2. get_product — full details for a specific product
3. get_order — order details + shipping status + tracking
4. evaluate_return — policy-based return eligibility check
5. get_sizing_info — measurement chart, size conversion, vendor fit notes
6. search_faqs — grounded FAQ answers (shipping, payment, returns, account)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Agent class
# ═══════════════════════════════════════════════════════════════════════════════

class OpenClawAgent:
    """Stateful conversational agent with tool-calling."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = MODEL_NAME
        self.messages: List[dict] = [
            {"role": "system", "content": _build_system_prompt()},
        ]

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.

        This implements the agentic loop:
        1. Append user message.
        2. Call OpenAI with tool definitions.
        3. If the model requests tool calls → execute them → feed results back.
        4. Repeat until the model produces a final text response.
        """
        self.messages.append({"role": "user", "content": user_message})

        tool_call_count = 0

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=TEMPERATURE,
            )

            msg = response.choices[0].message

            # If no tool calls, we have a final answer
            if not msg.tool_calls:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content

            # Process tool calls
            self.messages.append(msg)  # append the assistant message with tool_calls

            for tool_call in msg.tool_calls:
                tool_call_count += 1
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                print(f"  🔧 Tool call: {fn_name}({json.dumps(fn_args, indent=2)})")

                if fn_name in TOOL_MAP:
                    result = TOOL_MAP[fn_name](**fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

            # Safety: prevent infinite tool-call loops
            if tool_call_count >= MAX_TOOL_CALLS_PER_TURN:
                break

        # If we exhausted tool calls, force a final response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=TEMPERATURE,
        )
        final = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": final})
        return final

    def reset(self):
        """Clear conversation history (keep system prompt)."""
        self.messages = [self.messages[0]]
