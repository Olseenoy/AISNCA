import streamlit as st
from datetime import datetime
import pandas as pd
from utils.chatbot import ask_question, expand_root_cause
from pdf_generator import make_report_pdf   # ✅ use corrected function

st.title("Smart Non-Conformance Analyser")

# Chat history
if "chat" not in st.session_state:
    st.session_state.chat = []

uploaded_file = st.file_uploader("Upload CSV Log", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Simple chat UI
    user_input = st.chat_input("Describe the issue or select a query...")
    if user_input:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.chat.append((timestamp, "User", user_input))

        # Call chatbot logic
        response = ask_question(user_input, df)
        st.session_state.chat.append((timestamp, "Bot", response))

    # Display chat
    for timestamp, role, msg in st.session_state.chat:
        st.write(f"[{timestamp}] **{role}:** {msg}")

    # ✅ PDF generation
    if st.button("Generate CAPA PDF"):
        pdf_bytes, filename = make_report_pdf({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "factory": "Factory A",   # you can update this to dynamic input
            "shift": "Shift 1",       # or derive from chat/CSV
            "machine": "Machine X",
            "issue": "Non-conformance issue",
            "additional_notes": None,
            "evidence_text": "Historical data from CSV",
            "expanded_root_cause": "Expanded explanation of root cause",
            "capa": "Proposed correction and preventive action"
        })

        st.download_button(
            label="Download CAPA Report",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf"
        )
