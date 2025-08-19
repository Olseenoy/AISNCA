# utils.py
import pandas as pd
import openai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import numpy as np
import os

# Optional local model imports
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.neighbors import NearestNeighbors
except Exception:
    SentenceTransformer = None


def load_csv(path):
    df = pd.read_csv(path, dtype=str).fillna("")
    expected = ["date","shift","factory","machine","issue","root_cause","correction","corrective_action","reported_by"]
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    return df

_tfidf_cache = {}

def tfidf_search(df, query, top_k=5):
    corpus = (df["factory"].astype(str) + " " + df["machine"].astype(str) + " " +
              df["issue"].astype(str) + " " + df["root_cause"].astype(str))
    key = "default"
    if key not in _tfidf_cache:
        vect = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
        X = vect.fit_transform(corpus)
        _tfidf_cache[key] = (vect, X)
    else:
        vect, X = _tfidf_cache[key]
    qv = vect.transform([query])
    cosine_similarities = linear_kernel(qv, X).flatten()
    top_indices = cosine_similarities.argsort()[::-1][:top_k]
    results = []
    for i in top_indices:
        row = df.iloc[i].to_dict()
        row["score"] = float(cosine_similarities[i])
        results.append(row)
    return results


def semantic_search(df, query, openai_api_key=None, top_k=5):
    if openai_api_key:
        openai.api_key = openai_api_key
        texts = (df["factory"].astype(str) + " " + df["machine"].astype(str) + " " +
                  df["issue"].astype(str) + " " + df["root_cause"].astype(str)).tolist()
        resp = openai.Embedding.create(model="text-embedding-3-small", input=texts)
        emb_rows = [r["embedding"] for r in resp["data"]]
        qemb = openai.Embedding.create(model="text-embedding-3-small", input=[query])["data"][0]["embedding"]
        def cosine(a,b):
            a = np.array(a); b = np.array(b)
            return float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b)+1e-12))
        scores = [cosine(qemb, r) for r in emb_rows]
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for i in top_indices:
            row = df.iloc[i].to_dict()
            row["score"] = float(scores[i])
            results.append(row)
        return results
    else:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed for local semantic search")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        texts = (df["factory"].astype(str) + " " + df["machine"].astype(str) + " " +
                  df["issue"].astype(str) + " " + df["root_cause"].astype(str)).tolist()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        qemb = model.encode([query], convert_to_numpy=True)[0]
        nbrs = NearestNeighbors(n_neighbors=min(top_k, len(texts)), metric="cosine").fit(embeddings)
        dists, idxs = nbrs.kneighbors([qemb])
        results = []
        for dist, i in zip(dists[0], idxs[0]):
            row = df.iloc[i].to_dict()
            row["score"] = float(1 - dist)
            results.append(row)
        return results


def expand_root_cause_and_capa(context: dict, openai_api_key=None):
    prompt = f"""
You are a Quality Assurance expert. Given the information below, expand the root cause into a clear, thorough narrative (3-6 sentences),
identify immediate corrections, and produce a CAPA plan with: objective, short-term corrective actions, root cause analysis (5 whys), preventive actions,
owners, timeline (short-term and long-term), and metrics to verify effectiveness.

Context:
Reported issue: {context.get('reported_issue')}
Observed root cause (from history): {context.get('observed_root_cause')}
Evidence: {context.get('evidence')}
Factory: {context.get('factory')}
Machine: {context.get('machine')}
Shift: {context.get('shift')}
Additional notes: {context.get('additional_notes')}
"""
    if not openai_api_key:
        expanded = ("[No LLM key provided] Observed root cause: " + context.get('observed_root_cause', 'N/A') +
                    ". Recommended to investigate operator procedures, check recent maintenance, and validate recipes.")
        capa = ("[No LLM key] CAPA: 1) Immediate: Stop production, segregate affected batches. 2) Short-term: Repair/replace faulty parts. "
                "3) Preventive: Update SOPs, retrain staff. Owner: QA Manager. Timeline: immediate -> 1 week -> 1 month. KPI: rework rate.")
        return expanded, capa

    openai.api_key = openai_api_key
    completion = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"You are a helpful quality assurance and process improvement assistant."},
            {"role":"user","content":prompt}
        ],
        temperature=0.2,
        max_tokens=800
    )
    text = completion["choices"][0]["message"]["content"].strip()
    return text, text
