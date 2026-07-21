import os
import streamlit as st
import google.generativeai as genai

from monday_api import get_board
from helpers import clean_work_orders, clean_deals, build_stats, data_quality_notes
from config import WORK_ORDERS_BOARD_ID, DEALS_BOARD_ID, GEMINI_MODEL

# ─────────────────────────────────────────────
st.set_page_config(page_title="Skylark BI Agent", page_icon="🚁", layout="wide")
st.title("🚁 Skylark Drones — BI Agent")
st.caption("Ask questions about revenue, pipeline health, sector performance, and operations.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── load + clean data ─────────────────────────────────────────────────────────
wo_raw, wo_err = get_board(WORK_ORDERS_BOARD_ID)
deals_raw, deals_err = get_board(DEALS_BOARD_ID)

wo_df = clean_work_orders(wo_raw.copy()) if wo_raw is not None else None
deals_df = clean_deals(deals_raw.copy()) if deals_raw is not None else None

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📡 Board Status")

    if wo_err:
        st.error(f"Work Orders ❌\n{wo_err}")
    else:
        st.success(f"Work Orders ✅ — {len(wo_df)} rows")

    if deals_err:
        st.error(f"Deals ❌\n{deals_err}")
    else:
        st.success(f"Deals ✅ — {len(deals_df)} rows")

    if st.button("🔄 Refresh Data", use_container_width=True):
        get_board.clear()
        st.rerun()

    st.divider()

    if st.button("📊 Leadership Brief", type="primary", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "__BRIEF__"})
        st.rerun()

    st.divider()
    st.markdown("**Try asking:**")
    examples = [
        "What's our total pipeline value?",
        "Top sectors by revenue?",
        "What is our win rate?",
        "How much is outstanding in collections?",
        "Energy sector pipeline this quarter?",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key=q):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

    if wo_df is not None or deals_df is not None:
        with st.expander("🔍 Data notes"):
            st.markdown(data_quality_notes(wo_df, deals_df))


# ── gemini helpers ────────────────────────────────────────────────────────────
def ask_gemini(question, history):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ GEMINI_API_KEY is not set. Add it to your environment secrets."

    genai.configure(api_key=api_key)
    stats = build_stats(wo_df, deals_df)

    system = (
        "You are a business intelligence analyst for Skylark Drones. "
        "Answer founder-level questions using ONLY the provided data summary — "
        "give insight and context, not just numbers. "
        "Mention data quality caveats when relevant. "
        "If the question is ambiguous, ask ONE clarifying question before answering."
    )

    prompt = f"{system}\n\nLive data summary:\n{stats}\n\nQuestion: {question}"

    try:
        genai_history = []
        for msg in history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            genai_history.append({"role": role, "parts": [msg["content"]]})

        model = genai.GenerativeModel(GEMINI_MODEL)
        chat = model.start_chat(history=genai_history)
        return chat.send_message(prompt).text
    except Exception as e:
        return f"⚠️ Gemini error: {e}"


def make_brief():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ GEMINI_API_KEY is not set."

    genai.configure(api_key=api_key)
    stats = build_stats(wo_df, deals_df)

    prompt = (
        "Write a one-page leadership brief for Skylark Drones founders.\n"
        "Include: weighted open pipeline value, top 3 sectors by revenue, "
        "collections outstanding, win rate, and 2-3 key risks or flags. "
        "Format as clean markdown. Keep it concise.\n\n"
        f"Data: {stats}"
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        return model.generate_content(prompt).text
    except Exception as e:
        return f"⚠️ Error: {e}"


# ── chat interface ────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    if msg["content"] == "__BRIEF__":
        with st.chat_message("assistant"):
            with st.spinner("Generating leadership brief..."):
                brief = make_brief()
            st.markdown(f"## 📊 Leadership Brief\n\n{brief}")
        st.session_state.messages[i] = {
            "role": "assistant",
            "content": f"## 📊 Leadership Brief\n\n{brief}",
        }
        st.rerun()
    else:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    question = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_gemini(question, st.session_state.messages)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
