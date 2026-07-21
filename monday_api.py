import os
import requests
import pandas as pd
import streamlit as st

MONDAY_URL = "https://api.monday.com/v2"


@st.cache_data(ttl=300)
def get_board(board_id):
    """Fetch all items from a Monday.com board. Returns (df, error_string)."""
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        return None, "MONDAY_API_TOKEN secret is not set."
    if not board_id or "YOUR_" in str(board_id):
        return None, f"Board ID not configured yet (config.py shows: {board_id})"

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "API-Version": "2024-01",
    }

    query = """
    query ($boardId: ID!, $cursor: String) {
      boards(ids: [$boardId]) {
        items_page(limit: 200, cursor: $cursor) {
          cursor
          items {
            name
            column_values { column { title } text }
          }
        }
      }
    }
    """

    rows = []
    cursor = None

    try:
        while True:
            variables = {"boardId": board_id}
            if cursor:
                variables["cursor"] = cursor

            resp = requests.post(
                MONDAY_URL,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                return None, f"Monday.com API error: {data['errors']}"

            page = data["data"]["boards"][0]["items_page"]
            for item in page["items"]:
                row = {"Name": item["name"]}
                for cv in item["column_values"]:
                    row[cv["column"]["title"]] = cv["text"] or None
                rows.append(row)

            cursor = page.get("cursor")
            if not cursor:
                break

        return pd.DataFrame(rows), None

    except Exception as e:
        return None, str(e)
