# Smart Non-Conformance Analyzer

Streamlit app that analyzes non-conformance (NC) logs, performs semantic search over historical incidents, expands root causes using an LLM (OpenAI), generates CAPA recommendations, and creates a downloadable PDF report.

## Quickstart

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate    # macOS / Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
