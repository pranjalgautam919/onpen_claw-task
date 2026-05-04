"""
Channel simulation layer for OpenClaw.

Simulates monitoring of Chat and WhatsApp channels.
In production, this would integrate with:
- WhatsApp Business API (via Twilio / Meta Cloud API)
- Web chat widget (via WebSocket / REST)

For this prototype, we simulate both channels through the CLI
with channel-aware routing and response formatting.
"""

from typing import Optional
from src.agent import OpenClawAgent


class ChannelRouter:
    """
    Routes incoming messages from different channels to the OpenClaw agent.
    Applies channel-specific formatting and handles escalation.
    """

    # Keywords that trigger human escalation
    ESCALATION_KEYWORDS = [
        "speak to a person", "human agent", "manager", "complaint",
        "damaged", "broken", "legal", "lawyer", "sue", "refund dispute",
        "escalate", "supervisor",
    ]

    def __init__(self, agent: OpenClawAgent):
        self.agent = agent

    def route_message(self, message: str, channel: str = "chat") -> str:
        """
        Process a message from a specific channel.

        Parameters
        ----------
        message : str
            The customer's message.
        channel : str
            One of 'chat', 'whatsapp'.

        Returns
        -------
        str – The formatted response.
        """
        # Check for escalation triggers
        if self._needs_escalation(message):
            return self._escalation_response(channel)

        # Route to agent
        response = self.agent.chat(message)

        # Format for channel
        return self._format_response(response, channel)

    def _needs_escalation(self, message: str) -> bool:
        """Check if the message should be routed to a human agent."""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self.ESCALATION_KEYWORDS)

    def _escalation_response(self, channel: str) -> str:
        """Generate an escalation message appropriate for the channel."""
        base = (
            "I understand you'd like to speak with a team member. "
            "I'm connecting you with a human agent now — "
            "someone will be with you shortly.\n\n"
            "For reference, our support hours are Mon–Fri 9 AM – 6 PM EST."
        )
        if channel == "whatsapp":
            return f"🙋‍♀️ {base}\n\n_Reply STOP to cancel._"
        return base

    def _format_response(self, response: str, channel: str) -> str:
        """Apply channel-specific formatting."""
        if channel == "whatsapp":
            # WhatsApp uses simpler markdown
            response = response.replace("**", "*")
            # Add a friendly prefix for WhatsApp
            if not response.startswith("🙋"):
                response = f"👗 {response}"
        return response


class ChannelSimulator:
    """
    Simulates incoming messages from Chat and WhatsApp channels.
    Used for demo / testing purposes.
    """

    DEMO_SCENARIOS = [
        {
            "channel": "whatsapp",
            "message": "Hi! I need a modest evening gown under $300 in size 8. I prefer something on sale.",
            "description": "Personal Shopper — WhatsApp: Modest evening gown request",
        },
        {
            "channel": "chat",
            "message": "I'm looking for a casual dress for a garden party, size 10, under $200.",
            "description": "Personal Shopper — Chat: Casual garden party dress",
        },
        {
            "channel": "whatsapp",
            "message": "Order O0043 — I bought this dress last week. It doesn't fit. Can I return it?",
            "description": "Support — WhatsApp: Return inquiry",
        },
        {
            "channel": "chat",
            "message": "Can I return order O0012? I changed my mind about it.",
            "description": "Support — Chat: Clearance return attempt",
        },
        {
            "channel": "chat",
            "message": "What's the status of order O9999?",
            "description": "Edge Case — Chat: Invalid order ID",
        },
    ]

    def __init__(self, router: ChannelRouter):
        self.router = router

    def run_demo(self):
        """Run all demo scenarios and print results."""
        for i, scenario in enumerate(self.DEMO_SCENARIOS, 1):
            print(f"\n{'='*70}")
            print(f"  DEMO {i}: {scenario['description']}")
            print(f"  Channel: {scenario['channel'].upper()}")
            print(f"{'='*70}")
            print(f"\n📨 Customer: {scenario['message']}\n")

            response = self.router.route_message(
                scenario["message"],
                scenario["channel"],
            )
            print(f"🤖 OpenClaw:\n{response}\n")

            # Reset agent between scenarios for clean state
            self.router.agent.reset()
