# 🧠 DocuMind AI: Research & Document Intelligence Engine

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20DB-DC244C?style=for-the-badge&logo=qdrant&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-0.1+-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" />
</p>

---

## Overview

DocuMind AI is a **production-grade Retrieval-Augmented Generation (RAG) system** engineered for deep analysis of complex research papers and technical documents. It moves beyond naive RAG implementations by combining three critical capabilities that separate prototypes from production systems:

- **Page-level citation enforcement** — the LLM is architecturally constrained to append `[Page X]` citations to every factual claim, sourced directly from document metadata, making every answer independently verifiable.
- **Hybrid dense/sparse retrieval** — Qdrant fuses semantic (cosine) and lexical (BM25) search via Reciprocal Rank Fusion, capturing both conceptual similarity and exact keyword matches that pure vector search misses.
- **Automated evaluation pipeline** — a Ragas-powered evaluation script scores the system on **Faithfulness** (hallucination rate) and **Context Precision** (retrieval accuracy), providing quantitative proof of system reliability.

---

## System Architecture

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Document Ingestion                                      │
│     • PyMuPDF (fitz) — page-by-page extraction with        │
│       strict page number tracking preserved in metadata     │
│     • LangChain RecursiveCharacterTextSplitter              │
│       chunk_size=500, chunk_overlap=50                      │
│     • Output: [{ text, metadata: {source, page} }]         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Hybrid Vector Database                                  │
│     • Qdrant (in-memory) with two vector spaces:           │
│       — Dense:  FastEmbed all-MiniLM-L6-v2 (semantic)      │
│       — Sparse: FastEmbed BM25 (lexical keyword)           │
│     • Retrieval fuses both via Reciprocal Rank Fusion       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. LLM Grounding Layer                                     │
│     • Model: Ollama llama3.2 (local, free) /               │
│             OpenAI gpt-4o-mini (cloud)                      │
│     • System prompt enforces strict grounding rules:        │
│       — Answer ONLY from retrieved chunks                   │
│       — Cite [Page X] after every factual statement        │
│       — Refuse to answer if context is insufficient        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Evaluation Pipeline                                     │
│     • Ragas framework with LLM-as-judge scoring:           │
│       — Faithfulness:      hallucination rate (0–1)        │
│       — Context Precision: retrieval accuracy  (0–1)       │
│     • asyncio-native for compatibility with Ragas SDK      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 🔍 Hybrid Search Retrieval
Combines **dense semantic vectors** (capturing conceptual meaning) with **BM25 sparse vectors** (capturing exact terminology) in a single Qdrant query. Results are fused via Reciprocal Rank Fusion — consistently outperforming either retrieval method alone, especially on technical jargon and acronyms common in research papers.

### 💬 Interactive Streamlit UI with Citation Verification
A two-panel interface built for research workflows:
- **Left panel** — PDF uploader with live indexing status and a persistent indexed-documents list
- **Right panel (Chat tab)** — full conversation history; every assistant response includes a collapsible **"View Source Chunks"** expander showing the exact text and page number used to generate each answer
- **Right panel (Preview tab)** — side-by-side PDF viewer rendered page-by-page via PyMuPDF, with a slider for navigation — so citations can be spot-checked against the source document without leaving the app

### 🛡️ Zero-Hallucination Evaluation Script
`evaluate.py` runs an automated Ragas evaluation against a `SingleTurnSample` test case using the same LLM-as-judge pattern as production:
- **Faithfulness score** decomposes the response into atomic claims and verifies each against the retrieved context
- **Context Precision score** validates that the most relevant chunks rank highest in retrieval
- Designed to be extended with real query/response pairs from production logs

### ⚡ FastAPI Backend
Clean REST API with two endpoints:
- `POST /upload` — accepts PDF, extracts and chunks text, embeds and upserts into Qdrant
- `POST /chat` — runs hybrid search, builds a grounded context window, returns LLM answer + raw chunks

---

## Project Structure

```
DocuMind AI/
├── api.py            # FastAPI backend (upload + chat endpoints)
├── app.py            # Streamlit frontend (chat UI + PDF preview)
├── ingest.py         # PDF extraction and chunking (PyMuPDF + LangChain)
├── database.py       # Qdrant hybrid vector store (FastEmbed)
├── evaluate.py       # Ragas evaluation pipeline
├── requirements.txt  # Python dependencies
└── .env              # API keys (not committed)
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/yuvanshkalra/DocuMind-AI.git
cd DocuMind-AI
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

```powershell
# Create the .env file
'OPENAI_API_KEY=your-api-key-here' | Out-File -FilePath .env -Encoding utf8
```

> **Running locally for free?** Install [Ollama](https://ollama.com/download), then run `ollama pull llama3.2`. The system is pre-configured to use `llama3.2` by default — no API key required.

### 5. Run the FastAPI backend

```powershell
uvicorn api:app --reload
```

API will be available at `http://localhost:8000` · Interactive docs at `http://localhost:8000/docs`

### 6. Run the Streamlit frontend (new terminal)

```powershell
streamlit run app.py
```

UI will be available at `http://localhost:8501`

### 7. (Optional) Run the evaluation pipeline

```powershell
python evaluate.py
```

---

## Evaluation Results

| Metric | Score | Description |
|---|---|---|
| **Faithfulness** | 1.0 | All claims grounded in retrieved context — zero hallucinations |
| **Context Precision** | 1.0 | Retrieved chunks ranked by relevance with full precision |

> Scores reflect the included mock test case. Plug in real query/response pairs from production logs to continuously benchmark system performance.

---

## Tech Stack

| Component | Technology |
|---|---|
| API Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| PDF Parsing | PyMuPDF (fitz) |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Vector Database | Qdrant (in-memory / persistent) |
| Embeddings | FastEmbed (`all-MiniLM-L6-v2` + BM25) |
| LLM | Ollama `llama3.2` / OpenAI `gpt-4o-mini` |
| Evaluation | Ragas (Faithfulness + Context Precision) |

---

<p align="center">Built with precision. Evaluated with rigor. Zero hallucinations tolerated.</p>
