# 🧠 Enterprise AI Knowledge Assistant (OKF-powered)

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-black?logo=ollama&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

> **Structure-preserving RAG that keeps your document hierarchy, metadata, and cross-document relationships intact — powered entirely by local LLMs via Ollama.**

---

## 🎯 The Problem

A typical RAG pipeline chunks documents into arbitrary text blocks and stores embeddings. It loses:

- **Document structure** — headings, hierarchy, sections
- **Metadata** — type, owner document, timestamps
- **Relationships** — connections between concepts, even across different source documents
- **Portability** — knowledge locked in a vector DB schema

## ✅ The Solution: Open Knowledge Format (OKF)

OKF represents knowledge as a **directory of markdown files**. Each file is one "concept" with a small YAML frontmatter block and cross-links to related concepts via standard markdown links.

**It's just files** — readable in any editor, diffable in git, and usable by any AI agent without a proprietary SDK.

---

## ⚡ Features

| Feature | Description |
|---|---|
| **Multi-document ingestion** | Batch-upload `.docx`, `.pdf`, `.txt`, `.md` files in a single action |
| **Structure-preserving parsing** | DOCX heading styles, PDF font-size deltas, markdown headings — real structure, not arbitrary chunks |
| **OKF concept generation** | YAML frontmatter (type, title, tags, timestamp) + markdown body + cross-links to sibling sections |
| **Link-graph retrieval** | TF-IDF search expanded one hop through the markdown link graph — recovers cross-document relationships |
| **Streaming chat** | Real-time token-by-token streaming from local Ollama models |
| **Persistent chat history** | Conversation and sources survive tab switches |
| **Grounded citations** | Every answer cites source concepts by title and file path |
| **100% local** | No cloud APIs — runs entirely on your machine with Ollama |
| **Premium dark UI** | Custom-themed Streamlit interface with glassmorphism, gradient accents, and micro-animations |

---

## 🏗️ Architecture

```
Uploaded document (.docx / .pdf / .txt / .md)
        │
        ▼
  okf/parsers.py        → split into (heading, body) sections using each
                           format's real structure
        │
        ▼
  okf/converter.py      → one OKF concept per section: frontmatter
                           (type/title/description/tags/timestamp/resource)
                           + body + cross-links to siblings & parent doc
        │
        ▼
  okf/bundle.py         → writes concepts to disk as an OKF bundle:
                           bundle/<doc>/<section>.md, bundle/<doc>/index.md,
                           bundle/index.md, bundle/log.md
        │
        ▼
  okf/retrieval.py      → TF-IDF search over concept text, expanded one hop
                           through the markdown link graph
        │
        ▼
  okf/qa.py             → retrieved concepts assembled into context,
                           Ollama streams an answer with citations
        │
        ▼
  app.py (Streamlit)    → Ingest / Explore Bundle / Ask tabs
```

---

## 📂 Project Structure

```
OKF/
├── app.py                  # Streamlit frontend (3 tabs: Ingest, Explore, Ask)
├── okf/                    # Core library
│   ├── __init__.py         # Public API exports
│   ├── models.py           # Concept dataclass, slugify, frontmatter parsing
│   ├── parsers.py          # DOCX/PDF/TXT→Section parsers
│   ├── converter.py        # Section→OKF concept pipeline
│   ├── bundle.py           # Filesystem bundle management (index.md, log.md)
│   ├── retrieval.py        # TF-IDF + link-graph retrieval
│   └── qa.py               # Ollama streaming QA with grounded citations
├── sample_docs/            # Example enterprise documents for testing
├── bundle/                 # Generated OKF bundle (gitignored)
├── requirements.txt        # Python dependencies
├── .streamlit/config.toml  # Dark theme configuration
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **[Ollama](https://ollama.com/)** installed and running locally
- A pulled model (e.g., `ollama pull llama3` or `ollama pull mistral`)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/okf-knowledge-assistant.git
cd okf-knowledge-assistant

# Install dependencies
pip install -r requirements.txt

# Start the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Ollama models are auto-detected in the sidebar.

---

## 📖 Usage

### 1. 📥 Ingest Tab
Upload one or more enterprise documents, pick an OKF `type` (Policy, SOP, Contract, etc.), and click convert. Each document is parsed into structured sections and written as individual OKF concept files.

### 2. 🌳 Explore Bundle Tab
Browse the generated OKF bundle on disk — raw markdown with YAML frontmatter side-by-side with a rendered preview. Inspect cross-links between concepts.

### 3. 💬 Ask Tab
Ask natural language questions. The assistant retrieves relevant concepts (including ones reachable only by following cross-links from direct matches), streams a grounded answer from your local Ollama model, and cites every claim by concept title and file path.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit with custom CSS theming |
| Document parsing | python-docx, pdfplumber |
| Knowledge format | OKF v0.1 (YAML frontmatter + markdown) |
| Retrieval | scikit-learn TF-IDF + link-graph expansion |
| LLM inference | Ollama (local, any model) |
| Storage | Filesystem (the bundle IS the database) |

---

## 🧩 Design Philosophy — YAGNI

Deliberately **not** included:

- ❌ Vector database — TF-IDF + link-graph traversal is enough to prove the concept
- ❌ Authentication — single-user local tool
- ❌ Graph database — markdown links ARE the graph
- ❌ Custom schema validator — YAML frontmatter is self-describing
- ❌ Cloud APIs — everything runs locally

The filesystem is the storage layer — that's the entire point of OKF.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
