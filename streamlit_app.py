# streamlit_app.py
import streamlit as st
from datetime import datetime
import pandas as pd
import os
from utils import (load_csv, semantic_search, tfidf_search, expand_root_cause_and_capa)
from pdf_generator import make_report_pdf
from streamlit_chat import message as chat_message

st.set_page_config(page_title="Smart Non-Conformance Analyzer", layout="wide")

st.title("Smart Non-Conformance Analyzer — Chat UI")

# Sidebar: Settings & API key
st.sidebar.header("Settings / Connectors")
openai_key = st.sidebar.text_input("OpenAI API Key (optional, for LLM & embeddings)", type="password")
csv_path = st.sidebar.text_input("CSV log path", value="data/sample_nc_log.csv")
use_embeddings = st.sidebar.checkbox("Use OpenAI embeddings (if key provided)", value=True)

if st.sidebar.button("Reload CSV"):
    st.experimental_rerun()

# Load CSV
if not os.path.exists(csv_path):
    st.error(f"CSV not found at {csv_path}. Upload or provide valid path.")
    st.stop()

df = load_csv(csv_path)

# Chat memory in session state
if "history" not in st.session_state:
    st.session_state.history = []

# Top chat area
chat_col, form_col = st.columns([3, 1])

with chat_col:
    st.header("Conversation")
    for i, h in enumerate(st.session_state.history):
        is_user = (h["role"] == "user")
        chat_message(h["text"], is_user=is_user, key=f"msg_{i}")
        if "meta" in h and h["meta"]:
            st.write(h["meta"])

with form_col:
    st.header("New Report / Query")
    now = datetime.now()
    st.write("Date & Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

    shift = st.selectbox("Shift", options=["Day", "Swing", "Night"], index=0)
    factory = st.text_input("Factory", value="")
    machine = st.text_input("Machine", value="")
    issue_short = st.text_input("What is the issue? (short phrase)", value="")

    additional_notes = st.text_area("Additional context (optional)")

    if st.button("Submit / Analyze"):
        user_message = (f"Shift: {shift}\nFactory: {factory}\nMachine: {machine}\n"
                        f"Issue: {issue_short}\nNotes: {additional_notes}")
        st.session_state.history.append({
            "role": "user",
            "text": user_message,
            "timestamp": now.isoformat(),
            "meta": {"recorded_at": now.strftime("%Y-%m-%d %H:%M:%S")}
        })

        query_text = f"{factory} {machine} {issue_short} {additional_notes}"
        top_k = 5

        try:
            if openai_key and use_embeddings:
                search_results = semantic_search(df, query_text, openai_api_key=openai_key, top_k=top_k)
            else:
                search_results = tfidf_search(df, query_text, top_k=top_k)
        except Exception as e:
            st.error(f"Search error: {e}")
            search_results = []

        evidence_text = ""
        for idx, row in enumerate(search_results):
            evidence_text += (f"Result {idx+1} | date: {row.get('date','')} , shift: {row.get('shift','')}, "
                              f"factory: {row.get('factory','')}, machine: {row.get('machine','')}\n"
                              f"Issue: {row.get('issue','')}\nRoot cause: {row.get('root_cause','')}\n"
                              f"Correction: {row.get('correction','')}\nCorrective action: {row.get('corrective_action','')}\n\n")

        st.subheader("Matching historical incidents")
        if evidence_text.strip():
            st.code(evidence_text)
        else:
            st.info("No close matches found in the log.")

        base_root_cause = search_results[0].get("root_cause") if search_results else ""
        prompt_context = {
            "reported_issue": issue_short or "N/A",
            "observed_root_cause": base_root_cause or "Not found in historical logs",
            "evidence": evidence_text,
            "shift": shift,
            "factory": factory,
            "machine": machine,
            "additional_notes": additional_notes
        }

        try:
            expanded, capa = expand_root_cause_and_capa(prompt_context, openai_api_key=openai_key)
        except Exception as e:
            st.error(f"LLM expansion error: {e}")
            expanded, capa = "LLM unavailable", "LLM unavailable"

        st.subheader("Expanded Root Cause")
        st.write(expanded)
        st.subheader("Suggested CAPA (Corrective & Preventive Actions)")
        st.write(capa)

        assistant_text = f"Expanded Root Cause:\n{expanded}\n\nCAPA:\n{capa}"
        st.session_state.history.append({
            "role": "assistant",
            "text": assistant_text,
            "timestamp": datetime.now().isoformat(),
            "meta": {"based_on_rows": len(search_results)}
        })

        pdf_bytes = make_report_pdf({
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "shift": shift, "factory": factory, "machine": machine, "issue": issue_short,
            "additional_notes": additional_notes,
            "evidence_text": evidence_text,
            "expanded_root_cause": expanded,
            "capa": capa
        })
        st.download_button("Download PDF report", data=pdf_bytes, file_name=f"NC_Report_{now.strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf")
