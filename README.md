# OpenClaw — Retail AI Assistant

An agentic AI system that simulates two roles for a fashion boutique:

- **Personal Shopper** (Revenue Agent) — product recommendations with multi-constraint reasoning  
- **Customer Support Assistant** (Operations Agent) — order lookups, return evaluations, policy enforcement  

Built with OpenAI function-calling: the model chooses **which tools to call** and answers from real data (CSVs/JSON/policy), not fixed reply strings.

---

## How to run

### 1. Prerequisites

- Python 3.10+ (3.9+ may work)  
- An [OpenAI API key](https://platform.openai.com/account/api-keys)  

### 2. Install

From the project folder (`d:\prt` or your clone path):

```powershell
cd d:\prt
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
cd prt
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure API key

```powershell
copy .env.example .env
```

Edit `.env` and set:

```env
OPENAI_API_KEY=sk-your-key-here
```

Optional: `MODEL_NAME` (default `gpt-4o-mini`).

Interactive modes **exit early** if `OPENAI_API_KEY` is missing.

### 4. Run the CLI

| Command | What it does |
|--------|----------------|
| `python main.py` | Interactive chat with OpenClaw |
| `python main.py --demo` | Runs 5 scripted scenarios (shopping, support, invalid order) |
| `python main.py --channel` | Same as chat, but you pick `chat` or `whatsapp` each turn (simulated channel formatting) |

Examples:

```powershell
python main.py
python main.py --demo
python main.py --channel
```

Inside interactive modes: type `quit` to exit, `reset` to clear conversation history.

### 5. Run tests (no API key)

Tool and data logic are tested without calling OpenAI:

```powershell
python -m pytest tests/test_tools.py -v
```

---

## Project structure

```
prt/
├── data/
│   ├── products.csv
│   ├── orders.csv
│   ├── policy.txt
│   ├── sizing_guide.json
│   └── faqs.json
├── src/
│   ├── config.py          # Paths, API key, CURRENT_DATE (fixed “today” for returns)
│   ├── data_loader.py
│   ├── tools.py           # Tool implementations + OpenAI schemas
│   ├── agent.py           # OpenClaw agent loop
│   └── channels.py        # Simulated chat / WhatsApp routing
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEMO_EXAMPLES.md
│   └── REPORT.md          # Short submission-style summary
├── tests/
│   └── test_tools.py
├── main.py                # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Tools (function calling)

| Tool | Purpose |
|------|---------|
| `search_products` | Filters catalog (tags, price, size/stock, vendor, sale/clearance, sort) |
| `get_product` | Full detail for one `product_id` |
| `get_order` | Order + shipping/tracking + product snapshot |
| `evaluate_return` | Policy-based return eligibility |
| `get_sizing_info` | Charts, conversions, vendor/fit notes |
| `search_faqs` | Grounded FAQ lookup |

---

## Demo scenarios

With `python main.py --demo`:

1. Shopping (WhatsApp) — modest evening gown, size 8, under $300, sale  
2. Shopping (Chat) — casual garden party dress, size 10, under $200  
3. Support (WhatsApp) — return question for order O0043  
4. Support (Chat) — clearance return attempt (O0012)  
5. Edge case (Chat) — invalid order O9999  

Details: [docs/DEMO_EXAMPLES.md](docs/DEMO_EXAMPLES.md).

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _(required for LLM modes)_ | OpenAI API key |
| `MODEL_NAME` | `gpt-4o-mini` | Chat model |

Return-window math uses a fixed **reference date** in `src/config.py` (`CURRENT_DATE`) so behavior is reproducible.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — design, tools, anti-hallucination approach  
- [Demo examples](docs/DEMO_EXAMPLES.md) — expected tools and outcomes  
- [Brief report](docs/REPORT.md) — workflow summary and assumptions  

---

## Windows console (Unicode)

`main.py` configures UTF-8 stdout/stderr when supported so banners and emoji render; if your terminal still garbles output, try running from Windows Terminal or set `PYTHONIOENCODING=utf-8`.

---


