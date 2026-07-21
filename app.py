import os
import streamlit as st
import google.generativeai as genai

from monday_api import get_board
from helpers import clean_work_orders, clean_deals, build_stats
from config import WORK_ORDERS_BOARD_ID, DEALS_BOARD_ID, GEMINI_MODEL

st.set_page_config(page_title="Skylark BI Agent", page_icon="\U0001f681")
st.title("\U0001f681 Skylark Drones BI Agent")
st.caption("Ask questions about revenue, pipeline, and operations.")

if "messages" not in st.session_state:
    st.session_state.messages = []

wo_raw, wo_err   = get_board(WORK_ORDERS_BOARD_ID)
deals_raw, deals_err = get_board(DEALS_BOARD_ID)
wo_df    = clean_work_orders(wo_raw.copy())   if wo_raw    is not None else None
deals_df = clean_deals(deals_raw.copy()) if deals_raw is not None else None

if wo_err:    st.error(wo_err)
if deals_err: st.error(deals_err)


def ask_gemini(question, history):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY not set. Add it to your environment."
    genai.configure(api_key=api_key)
    stats  = build_stats(wo_df, deals_df)
    system = ("You are a BI analyst for Skylark Drones. "
              "Answer questions using ONLY the provided data. Give insights not just numbers.")
    prompt = f"{system}\n\nData: {stats}\n\nQuestion: {question}"
    try:
        hist = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]}
                for m in history[:-1]]
        model = genai.GenerativeModel(GEMINI_MODEL)
        return model.start_chat(history=hist).send_message(prompt).text
    except Exception as e:
        return f"Gemini error: {e}"


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    q = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_gemini(q, st.session_state.messages)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
