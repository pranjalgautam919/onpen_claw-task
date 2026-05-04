#!/usr/bin/env python3
"""
OpenClaw — Retail AI Assistant
===============================
CLI entry point.

Usage:
    python main.py              Interactive chat mode
    python main.py --demo       Run pre-built demo scenarios
    python main.py --channel    Interactive mode with channel selection
"""

import argparse
import sys

# Windows consoles often default to cp1252; emoji/box-drawing need UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from src.agent import OpenClawAgent
from src.channels import ChannelRouter, ChannelSimulator
from src.config import OPENAI_API_KEY


# ── ANSI colors ────────────────────────────────────────────────────────────────

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _require_openai_key() -> None:
    """LLM modes need OPENAI_API_KEY (see .env.example)."""
    if not (OPENAI_API_KEY or "").strip():
        print(
            f"{Colors.RED}{Colors.BOLD}Missing OPENAI_API_KEY.{Colors.RESET}\n"
            "Copy .env.example to .env and set your key, or export OPENAI_API_KEY.\n"
            "Tool logic is still verified with: pytest tests/test_tools.py",
            file=sys.stderr,
        )
        sys.exit(1)


BANNER = f"""{Colors.CYAN}{Colors.BOLD}
  ╔══════════════════════════════════════════════════╗
  ║                                                  ║
  ║          🦀  O P E N C L A W   A I  🦀          ║
  ║                                                  ║
  ║     Retail AI Assistant — Fashion Boutique       ║
  ║     Personal Shopper · Customer Support          ║
  ║                                                  ║
  ╚══════════════════════════════════════════════════╝
{Colors.RESET}"""


def interactive_mode():
    """Standard interactive chat mode."""
    _require_openai_key()
    print(BANNER)
    print(f"{Colors.DIM}  Type your message and press Enter. Type 'quit' to exit.")
    print(f"  Type 'reset' to clear conversation history.{Colors.RESET}\n")

    agent = OpenClawAgent()

    while True:
        try:
            user_input = input(f"{Colors.GREEN}{Colors.BOLD}You: {Colors.RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.DIM}Goodbye! 👋{Colors.RESET}")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() == "quit":
            print(f"\n{Colors.DIM}Goodbye! 👋{Colors.RESET}")
            break
        if user_input.strip().lower() == "reset":
            agent.reset()
            print(f"{Colors.YELLOW}  ↻ Conversation reset.{Colors.RESET}\n")
            continue

        print(f"{Colors.DIM}  ⏳ Thinking...{Colors.RESET}")
        response = agent.chat(user_input)
        print(f"\n{Colors.CYAN}{Colors.BOLD}OpenClaw:{Colors.RESET} {response}\n")


def channel_mode():
    """Interactive mode with channel selection (chat / whatsapp)."""
    _require_openai_key()
    print(BANNER)
    print(f"{Colors.DIM}  Simulated channel mode. Select a channel for each message.")
    print(f"  Type 'quit' to exit, 'reset' to clear history.{Colors.RESET}\n")

    agent = OpenClawAgent()
    router = ChannelRouter(agent)

    while True:
        try:
            channel = input(
                f"{Colors.YELLOW}Channel [chat/whatsapp]: {Colors.RESET}"
            ).strip().lower()
            if channel == "quit":
                break
            if channel not in ("chat", "whatsapp"):
                channel = "chat"
                print(f"{Colors.DIM}  Defaulting to 'chat'.{Colors.RESET}")

            user_input = input(f"{Colors.GREEN}{Colors.BOLD}Customer: {Colors.RESET}")
            if user_input.strip().lower() in ("quit", "exit"):
                break
            if user_input.strip().lower() == "reset":
                agent.reset()
                print(f"{Colors.YELLOW}  ↻ Conversation reset.{Colors.RESET}\n")
                continue

            print(f"{Colors.DIM}  ⏳ Processing on {channel.upper()} channel...{Colors.RESET}")
            response = router.route_message(user_input, channel)
            print(f"\n{Colors.CYAN}{Colors.BOLD}OpenClaw [{channel.upper()}]:{Colors.RESET} {response}\n")

        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.DIM}Goodbye! 👋{Colors.RESET}")
            break


def demo_mode():
    """Run pre-built demo scenarios."""
    _require_openai_key()
    print(BANNER)
    print(f"{Colors.YELLOW}{Colors.BOLD}  Running demo scenarios...{Colors.RESET}\n")

    agent = OpenClawAgent()
    router = ChannelRouter(agent)
    simulator = ChannelSimulator(router)
    simulator.run_demo()

    print(f"\n{Colors.GREEN}{Colors.BOLD}  ✓ All demos complete!{Colors.RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw — Retail AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Interactive chat
  python main.py --demo       Run demo scenarios
  python main.py --channel    Channel-aware interactive mode
        """,
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run pre-built demo scenarios (2 shopping, 2 support, 1 edge case).",
    )
    parser.add_argument(
        "--channel",
        action="store_true",
        help="Interactive mode with chat/WhatsApp channel selection.",
    )

    args = parser.parse_args()

    if args.demo:
        demo_mode()
    elif args.channel:
        channel_mode()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
