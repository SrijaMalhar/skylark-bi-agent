# Skylark Drones — BI Agent

A conversational AI agent that answers business questions using live data from Monday.com boards. Built with Streamlit + Gemini.

## What it does

- Pulls live data from two Monday.com boards (Work Orders + Deals) via the GraphQL API
- Cleans messy exports: drops stray header rows, coerces money columns, normalizes sector names
- Classifies deal stages (A–O prefix) into open / won / dead pipeline
- Lets you chat with the data using Gemini AI
- One-click **Leadership Brief** with weighted pipeline, top sectors, win rate, and collections

## Setup

### 1. Get your API keys

| Key | Where |
|-----|-------|
| `MONDAY_API_TOKEN` | Monday.com → Your avatar → Admin → API |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) → Get API key |

Set both as environment variables (or in a `.env` file — don't commit that).

### 2. Set your board IDs

Open `config.py` and replace the placeholder values:

```python
WORK_ORDERS_BOARD_ID = "123456789"
DEALS_BOARD_ID       = "987654321"
```

Find the ID in the Monday.com URL: `https://yourcompany.monday.com/boards/<ID>`

### 3. Install + run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## File structure

```
app.py          main Streamlit app + chat UI
monday_api.py   GraphQL client with 5-min cache
helpers.py      data cleaning, aggregations, stats builder
config.py       board IDs and model name
requirements.txt
```

## Notes on the data

The boards have a few quirks this app handles automatically:

- **Stray header rows** — some CSV exports leave a row where cells equal the column name. These get dropped.
- **Money columns** — values can be blank, masked, or in scientific notation. Everything gets coerced to numeric; blanks stay as NaN (not treated as 0).
- **Deal stages** — prefixed A–O. L, N, O = dead/lost. G, H, J, K, "Project Completed" = won. Everything else = open pipeline.
- **Sector names** — "mining", "Mining", "MINING" all normalize to "Mining".
