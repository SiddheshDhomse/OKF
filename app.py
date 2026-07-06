"""
Enterprise AI Knowledge Assistant — powered by Google's Open Knowledge Format (OKF).

Three tabs:
1. Ingest   — upload documents, convert them into OKF concepts.
2. Explore  — browse the actual OKF bundle on disk (it's just markdown files).
3. Ask      — query the bundle; answers are grounded and cited by concept.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

from okf import Bundle, convert_document, Retriever, stream_answer_question

BUNDLE_DIR = Path(__file__).parent / "bundle"

# ---------------------------------------------------------------------------
# PAGE CONFIG & CLAUDE-INSPIRED CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OKF Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---------- Global — Claude warm palette ---------- */
:root {
    --bg-primary: #f5f0e8;
    --bg-secondary: #ebe5d9;
    --bg-sidebar: #2c2419;
    --bg-sidebar-hover: #3d3225;
    --text-primary: #1a1612;
    --text-secondary: #6b6157;
    --text-muted: #8c8279;
    --accent: #c96442;
    --accent-light: #e07a55;
    --accent-bg: rgba(201,100,66,0.08);
    --border: rgba(26,22,18,0.1);
    --border-light: rgba(26,22,18,0.06);
    --user-bubble: #ffffff;
    --assistant-bubble: #f9f5ee;
    --terminal-bg: #1a1714;
    --terminal-text: #a8e06b;
    --terminal-dim: #5a6340;
    --terminal-border: #2e2a24;
}

html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.main .block-container {
    max-width: 960px;
    padding: 2rem 2rem 4rem 2rem;
}

/* ---------- Sidebar — dark warm ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2c2419 0%, #231e15 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] p {
    color: #c4b9a8 !important;
}
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stSelectbox label {
    color: #8c8279 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #e8dfd2 !important;
}
section[data-testid="stSidebar"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}

.sidebar-brand {
    text-align: center;
    padding: 1.25rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 1.25rem;
}
.sidebar-brand .logo { font-size: 1.75rem; }
.sidebar-brand h2 {
    font-size: 1rem;
    font-weight: 700;
    color: #e8dfd2 !important;
    margin: 0.4rem 0 0.15rem 0;
    letter-spacing: -0.01em;
}
.sidebar-brand p {
    font-size: 0.72rem;
    color: #6b6157 !important;
    margin: 0;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

.stat-row {
    display: flex;
    gap: 0.5rem;
    margin: 0.75rem 0;
}
.stat-card {
    flex: 1;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.6rem 0.75rem;
    text-align: center;
}
.stat-card .num {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--accent-light) !important;
}
.stat-card .label {
    font-size: 0.65rem;
    color: #6b6157 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ---------- Tabs — clean underline style ---------- */
div[data-testid="stTabs"] {
    background: transparent;
}
div[data-testid="stTabs"] > div:first-child {
    border-bottom: 1px solid var(--border);
    gap: 0;
}
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--text-muted);
    border-bottom: 2px solid transparent;
    padding: 0.6rem 1.25rem;
    transition: all 0.2s ease;
    background: transparent !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    color: var(--text-primary);
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* ---------- Buttons ---------- */
button[data-testid="stBaseButton-primary"] {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(201,100,66,0.2) !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent-light) !important;
    box-shadow: 0 2px 8px rgba(201,100,66,0.3) !important;
}

button[data-testid="stBaseButton-secondary"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ---------- File uploader ---------- */
section[data-testid="stFileUploader"] div[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed var(--border) !important;
    border-radius: 10px !important;
    transition: all 0.25s ease;
}
section[data-testid="stFileUploader"] div[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-bg) !important;
}

/* ---------- Chat — Claude-style ---------- */
div[data-testid="stChatMessage"] {
    border-radius: 12px !important;
    border: none !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.5rem;
}

/* ---------- Expanders ---------- */
details[data-testid="stExpander"] {
    border: 1px solid var(--border-light) !important;
    border-radius: 10px !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.82rem;
}

/* ---------- Code blocks ---------- */
pre {
    border-radius: 8px !important;
}
code {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ---------- Terminal log widget ---------- */
.terminal-log {
    background: var(--terminal-bg);
    border: 1px solid var(--terminal-border);
    border-radius: 10px;
    padding: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    line-height: 1.6;
    overflow: hidden;
    max-height: 280px;
}
.terminal-titlebar {
    background: #2e2a24;
    padding: 0.4rem 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.terminal-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
}
.terminal-dot.red { background: #e06c5a; }
.terminal-dot.yellow { background: #e0b53a; }
.terminal-dot.green { background: #5ac05a; }
.terminal-title {
    color: #6b6157;
    font-size: 0.68rem;
    margin-left: 0.5rem;
    letter-spacing: 0.03em;
}
.terminal-body {
    padding: 0.75rem 1rem;
    overflow-y: auto;
    max-height: 230px;
    color: var(--terminal-text);
}
.terminal-body .log-date {
    color: var(--accent-light);
    font-weight: 600;
    margin-top: 0.5rem;
}
.terminal-body .log-date:first-child {
    margin-top: 0;
}
.terminal-body .log-entry {
    color: #a8e06b;
    padding-left: 0.5rem;
}
.terminal-body .log-prefix {
    color: var(--terminal-dim);
}

/* ---------- Selectbox ---------- */
div[data-baseweb="select"] {
    border-radius: 8px !important;
}

/* ---------- Slider ---------- */
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] {
    background-color: var(--accent) !important;
}

/* ---------- Dividers ---------- */
hr {
    border-color: var(--border-light) !important;
}

/* ---------- Hide Streamlit chrome ---------- */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ---------- Alert styling ---------- */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.85rem;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

@st.cache_resource
def get_bundle() -> Bundle:
    return Bundle(BUNDLE_DIR)


def get_retriever(_bundle: Bundle) -> Retriever:
    return Retriever(_bundle)


def get_ollama_models(url: str) -> list[str]:
    try:
        r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=2)
        if r.status_code == 200:
            return sorted(m["name"] for m in r.json().get("models", []))
    except Exception:
        pass
    return []


def render_log_terminal(log_text: str) -> str:
    """Convert log.md into styled terminal HTML."""
    lines = log_text.strip().splitlines()
    body_html = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            continue  # skip the main heading
        elif stripped.startswith("## "):
            date = stripped.replace("## ", "")
            body_html += f'<div class="log-date">$ [{date}]</div>\n'
        elif stripped.startswith("* **Update**:"):
            msg = stripped.replace("* **Update**: ", "")
            body_html += f'<div class="log-entry"><span class="log-prefix">→ </span>{msg}</div>\n'
        elif stripped:
            body_html += f'<div class="log-entry"><span class="log-prefix">  </span>{stripped}</div>\n'

    return f"""
    <div class="terminal-log">
        <div class="terminal-titlebar">
            <span class="terminal-dot red"></span>
            <span class="terminal-dot yellow"></span>
            <span class="terminal-dot green"></span>
            <span class="terminal-title">okf-bundle — activity.log</span>
        </div>
        <div class="terminal-body">
            {body_html if body_html else '<div class="log-entry"><span class="log-prefix">  </span>No activity yet. Ingest a document to get started.</div>'}
        </div>
    </div>
    """


bundle = get_bundle()

# Initialize session state globally
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_concept_path" not in st.session_state:
    st.session_state.selected_concept_path = None


def render_chat_message(role: str, content: str, retrieved_concepts=None):
    if role == "user":
        # Clean line breaks and spacing, render as right-aligned dark speech bubble
        user_bubble_html = f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1.5rem; width: 100%;">
            <div style="background-color: #2c2419; color: #f5f0e8; padding: 0.9rem 1.25rem; border-radius: 12px 12px 2px 12px; max-width: 85%; box-shadow: 0 1px 2px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.05); font-size: 0.92rem; line-height: 1.5; white-space: pre-wrap;">{content}</div>
        </div>
        """
        st.markdown(user_bubble_html, unsafe_allow_html=True)
    else:
        # Left-aligned assistant answer with no enclosing bubble, just simple clean spacing
        st.markdown(f'<div style="margin-bottom: 0.5rem; font-size: 0.72rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 4px;"><span>🧠</span> Assistant</div>', unsafe_allow_html=True)
        st.markdown(content)
        if retrieved_concepts:
            with st.expander("📚 Sources"):
                for r in retrieved_concepts:
                    st.markdown(f"- **{r['title']}** — `{r['relpath']}`{r['via']} — score {r['score']:.3f}")
        st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
st.sidebar.markdown("""
<div class="sidebar-brand">
    <div class="logo">🧠</div>
    <h2>OKF Assistant</h2>
    <p>Structure-preserving RAG</p>
</div>
""", unsafe_allow_html=True)

ollama_url = st.sidebar.text_input(
    "Ollama Host",
    value="http://localhost:11434",
    help="The URL where your local Ollama instance is running.",
)

models = get_ollama_models(ollama_url)
if models:
    model_name = st.sidebar.selectbox(
        "Model",
        options=models,
        help="Select a model pulled in your Ollama instance.",
    )
else:
    model_name = st.sidebar.text_input(
        "Model",
        value="llama3",
        help="Ollama offline or no models found. Enter a model name manually.",
    )
    st.sidebar.warning("Could not connect to Ollama.")

# Stats
doc_count = sum(1 for p in BUNDLE_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")) if BUNDLE_DIR.exists() else 0
concept_files = list(BUNDLE_DIR.rglob("*.md")) if BUNDLE_DIR.exists() else []
concept_count = len([f for f in concept_files if f.name not in {"index.md", "log.md"}])

st.sidebar.markdown(f"""
<div class="stat-row">
    <div class="stat-card">
        <div class="num">{doc_count}</div>
        <div class="label">Documents</div>
    </div>
    <div class="stat-card">
        <div class="num">{concept_count}</div>
        <div class="label">Concepts</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()
if st.sidebar.button("🗑️ Clear Chat", type="secondary", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_ask, tab_ingest, tab_explore, tab_viewer = st.tabs(["💬 Chat", "📥 Ingest", "🔍 Explore", "📖 Viewer"])

# ---------------------------------------------------------------------------
# ASK — Claude-style centered chat
# ---------------------------------------------------------------------------
with tab_ask:
    top_k = st.slider("Retrieval depth", 1, 10, 5, help="Number of OKF concepts to retrieve for grounding each answer.")
    st.divider()

    # Replay history
    for msg in st.session_state.messages:
        render_chat_message(msg["role"], msg["content"], msg.get("retrieved_concepts"))

    # New messages
    if question := st.chat_input("Ask anything about your knowledge bundle…"):
        if not model_name:
            st.error("Select an Ollama model in the sidebar.")
        else:
            # 1. User Message (Right-aligned bubble)
            render_chat_message("user", question)
            st.session_state.messages.append({"role": "user", "content": question})

            # 2. Retrieval Phase
            retriever = get_retriever(bundle)
            with st.spinner("Retrieving…"):
                results = retriever.search(question, top_k=top_k, expand_links=True)

            retrieved_info = []
            for r in results:
                relpath = str(r.concept.path.relative_to(BUNDLE_DIR)) if r.concept.path else "?"
                via = f" (via link from *{r.via_link_from}*)" if r.via_link_from else ""
                retrieved_info.append({
                    "title": r.concept.title,
                    "relpath": relpath,
                    "via": via,
                    "score": r.score,
                })

            # 3. Assistant Streaming Response Phase
            st.markdown(f'<div style="margin-bottom: 0.5rem; font-size: 0.72rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 4px;"><span>🧠</span> Assistant</div>', unsafe_allow_html=True)
            
            gen = stream_answer_question(
                question, results, BUNDLE_DIR,
                history=st.session_state.messages[:-1],
                model=model_name, host=ollama_url,
            )
            full_response = st.write_stream(gen)

            if retrieved_info:
                with st.expander("📚 Sources"):
                    for r in retrieved_info:
                        st.markdown(f"- **{r['title']}** — `{r['relpath']}`{r['via']} — score {r['score']:.3f}")
            st.markdown('<div style="margin-bottom: 2rem;"></div>', unsafe_allow_html=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "retrieved_concepts": retrieved_info,
            })
            
            st.rerun()

# ---------------------------------------------------------------------------
# INGEST — with terminal-style log
# ---------------------------------------------------------------------------
with tab_ingest:
    col_upload, col_log = st.columns([3, 2])

    with col_upload:
        st.subheader("Upload Documents")
        st.caption("Drag-and-drop enterprise documents. Each is parsed into structured OKF concepts.")

        uploaded_files = st.file_uploader(
            "Supported: .docx, .pdf, .txt, .md",
            type=["docx", "pdf", "txt", "md"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            if st.button("⚡ Convert to OKF", type="primary", use_container_width=True):
                with st.spinner("Processing…"):
                    all_concepts = []
                    for uploaded in uploaded_files:
                        suffix = Path(uploaded.name).suffix
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(uploaded.getvalue())
                            tmp_path = Path(tmp.name)
                        try:
                            concepts = convert_document(bundle, tmp_path, uploaded.name)
                            all_concepts.extend(concepts)
                        finally:
                            tmp_path.unlink(missing_ok=True)

                st.success(f"✅ {len(all_concepts)} concepts from {len(uploaded_files)} doc(s)")
                with st.expander("Preview concepts", expanded=True):
                    for c in all_concepts:
                        st.markdown(f"**{c.title}** — `{c.type}` · `{c.resource}`")
                        st.code(c.to_markdown(), language="markdown")
                st.cache_resource.clear()
                st.rerun()

    with col_log:
        st.subheader("Activity Log")
        log_path = BUNDLE_DIR / "log.md"
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8")
            st.markdown(render_log_terminal(log_text), unsafe_allow_html=True)
        else:
            st.markdown(render_log_terminal(""), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# EXPLORE
# ---------------------------------------------------------------------------
with tab_explore:
    st.subheader("Bundle Explorer")
    st.caption("Every concept is a markdown file with YAML frontmatter. Browse the raw bundle.")

    all_md = sorted(BUNDLE_DIR.rglob("*.md"))
    if not all_md:
        st.info("No documents ingested yet. Head to the Ingest tab.")
    else:
        rel_paths = [str(p.relative_to(BUNDLE_DIR)) for p in all_md]
        selected = st.selectbox("Select file", rel_paths)
        selected_path = BUNDLE_DIR / selected
        raw = selected_path.read_text(encoding="utf-8")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Raw OKF Markdown**")
            st.code(raw, language="markdown")
        with col2:
            st.markdown("**Rendered Preview**")
            st.markdown(raw)

# ---------------------------------------------------------------------------
# INTERACTIVE OKF VIEWER
# ---------------------------------------------------------------------------
with tab_viewer:
    st.subheader("OKF Knowledge Browser")
    st.caption("Explore documents and their interconnected concepts as a visual graph or list.")

    all_concepts = bundle.load_all_concepts()
    if not all_concepts:
        st.info("No documents ingested yet. Go to the Ingest tab to add documents.")
    else:
        viewer_mode = st.radio("Display Mode", ["Graph View", "Document List View"], horizontal=True, key="viewer_mode_toggle")
        st.divider()
        
        if viewer_mode == "Graph View":
            # Graph visualization (Vis.js in iframe)
            import json
            
            nodes_data = []
            edges_data = []
            concept_map = {}
            seen_edges = set()
            
            # Map document folders dynamically to distinct colors for origin doc-wise color coding
            doc_dirs = sorted(list(set(c.path.parent.name for c in all_concepts if c.path)))
            colors_list = [
                "#c96442", "#2a6f97", "#38b000", "#7209b7",
                "#f72585", "#3a0ca3", "#f8961e", "#43aa8b", "#577590"
            ]
            doc_colors = {doc: colors_list[i % len(colors_list)] for i, doc in enumerate(doc_dirs)}
            
            for c in all_concepts:
                if not c.path:
                    continue
                c_id = str(c.path.resolve())
                rel_path = str(c.path.relative_to(BUNDLE_DIR))
                doc_name = c.path.parent.name
                color = doc_colors.get(doc_name, "#c96442")
                
                nodes_data.append({
                    "id": c_id,
                    "label": c.title,
                    "title": f"Doc: {c.resource} | Type: {c.type}", # Tooltip on hover
                    "color": {
                        "background": color,
                        "border": color,
                        "highlight": {
                            "background": "#ebe5d9",
                            "border": "#c96442"
                        }
                    },
                    "font": {
                        "color": "#1a1612", # Dark text to be readable on the warm light canvas
                        "size": 11,
                        "face": "Inter, sans-serif"
                    }
                })
                
                clean_body = c.body
                if "## Related" in clean_body:
                    clean_body = clean_body.split("## Related")[0].strip()
                    
                concept_map[c_id] = {
                    "title": c.title,
                    "type": c.type,
                    "resource": c.resource,
                    "tags": c.tags,
                    "body": clean_body,
                    "rel_path": rel_path
                }
                
                for link in c.links:
                    if link.endswith("index.md"):
                        continue
                    link_path = (c.path.parent / link).resolve()
                    link_id = str(link_path)
                    if link_path.exists():
                        edge = (c_id, link_id)
                        if edge not in seen_edges:
                            seen_edges.add(edge)
                            edges_data.append({
                                "from": c_id,
                                "to": link_id,
                            })
            
            nodes_json = json.dumps(nodes_data)
            edges_json = json.dumps(edges_data)
            concept_map_json = json.dumps(concept_map)
            
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
              <style>
                * {{ box-sizing: border-box; }}
                body {{
                  font-family: 'Inter', sans-serif;
                  margin: 0;
                  padding: 0;
                  background-color: #f5f0e8;
                  color: #1a1612;
                  height: 100vh;
                  overflow: hidden;
                }}
                .container {{
                  display: flex;
                  width: 100%;
                  height: 100vh;
                  border: 1px solid rgba(26,22,18,0.1);
                  border-radius: 12px;
                  overflow: hidden;
                  background-color: #ffffff;
                }}
                #network-pane {{
                  width: 65%;
                  height: 100%;
                  position: relative;
                  background-color: #faf8f5;
                }}
                #detail-pane {{
                  width: 35%;
                  height: 100%;
                  border-left: 1px solid rgba(26,22,18,0.1);
                  padding: 1.5rem;
                  background-color: #ffffff;
                  overflow-y: auto;
                  display: flex;
                  flex-direction: column;
                }}
                .placeholder-text {{
                  color: #8c8279;
                  font-size: 0.9rem;
                  text-align: center;
                  margin-top: auto;
                  margin-bottom: auto;
                }}
                .badge {{
                  display: inline-block;
                  background-color: #ebe5d9;
                  color: #6b6157;
                  padding: 4px 8px;
                  border-radius: 6px;
                  font-size: 0.72rem;
                  font-weight: 600;
                  margin-right: 6px;
                  margin-bottom: 6px;
                  border: 1px solid rgba(26,22,18,0.06);
                }}
                .tag {{
                  display: inline-block;
                  background-color: rgba(201,100,66,0.08);
                  color: #c96442;
                  padding: 2px 8px;
                  border-radius: 12px;
                  font-size: 0.7rem;
                  font-weight: 600;
                  margin-right: 6px;
                  margin-bottom: 6px;
                }}
                h3 {{
                  margin-top: 0;
                  font-size: 1.25rem;
                  font-weight: 700;
                  color: #1a1612;
                  line-height: 1.3;
                }}
                .content-body {{
                  font-size: 0.88rem;
                  line-height: 1.6;
                  color: #2c2419;
                  margin-top: 1rem;
                  white-space: pre-wrap;
                }}
                #detail-pane::-webkit-scrollbar {{ width: 6px; }}
                #detail-pane::-webkit-scrollbar-track {{ background: transparent; }}
                #detail-pane::-webkit-scrollbar-thumb {{
                  background: rgba(26,22,18,0.1);
                  border-radius: 3px;
                }}
                #detail-pane::-webkit-scrollbar-thumb:hover {{ background: rgba(26,22,18,0.2); }}
              </style>
              <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            </head>
            <body>
              <div class="container">
                <div id="network-pane"></div>
                <div id="detail-pane">
                  <div id="detail-content" class="placeholder-text">
                    <div style="font-size: 2.5rem; margin-bottom: 1rem;">🔍</div>
                    Click a node in the graph to display concept details and links.
                  </div>
                </div>
              </div>

              <script type="text/javascript">
                const conceptMap = {concept_map_json};
                const nodes = new vis.DataSet({nodes_json});
                const edges = new vis.DataSet({edges_json});

                const container = document.getElementById('network-pane');
                const data = {{ nodes: nodes, edges: edges }};
                
                const options = {{
                  nodes: {{
                    shape: 'dot',
                    size: 14,
                    font: {{
                      size: 11,
                      face: 'Inter, sans-serif',
                      color: '#1a1612'
                    }},
                    borderWidth: 1.5,
                    shadow: {{
                      enabled: true,
                      color: 'rgba(0,0,0,0.05)',
                      size: 4,
                      x: 0,
                      y: 2
                    }}
                  }},
                  edges: {{
                    arrows: 'to',
                    color: {{
                      color: 'rgba(26,22,18,0.15)',
                      highlight: '#c96442',
                      hover: '#c96442'
                    }},
                    width: 1.2,
                    smooth: {{
                      type: 'continuous',
                      forceDirection: 'none',
                      roundness: 0.5
                    }}
                  }},
                  physics: {{
                    stabilization: {{
                      enabled: true,
                      iterations: 150
                    }},
                    barnesHut: {{
                      gravitationalConstant: -1200,
                      centralGravity: 0.15,
                      springLength: 85,
                      springConstant: 0.04
                    }}
                  }},
                  interaction: {{
                    hover: true,
                    tooltipDelay: 200
                  }}
                }};

                const network = new vis.Network(container, data, options);

                network.on("selectNode", function (params) {{
                  if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const concept = conceptMap[nodeId];
                    if (concept) {{
                      let tagsHtml = '';
                      if (concept.tags && concept.tags.length > 0) {{
                        tagsHtml = concept.tags.map(t => `<span class="tag">#${{t}}</span>`).join('');
                      }}
                      
                      let contentHtml = `
                        <h3>📖 ${{concept.title}}</h3>
                        <div style="margin-bottom: 12px; display: flex; flex-wrap: wrap;">
                          <span class="badge">📁 Type: ${{concept.type}}</span>
                          <span class="badge">📄 File: ${{concept.rel_path}}</span>
                        </div>
                        <div style="margin-bottom: 15px;">${{tagsHtml}}</div>
                        <hr style="border: 0; border-top: 1px solid rgba(26,22,18,0.06); margin: 10px 0;" />
                        <div class="content-body">${{concept.body}}</div>
                      `;
                      document.getElementById('detail-pane').innerHTML = `<div id="detail-content">${{contentHtml}}</div>`;
                    }}
                  }}
                }});

                network.on("deselectNode", function (params) {{
                  document.getElementById('detail-pane').innerHTML = `
                    <div id="detail-content" class="placeholder-text">
                      <div style="font-size: 2.5rem; margin-bottom: 1rem;">🔍</div>
                      Click a node in the graph to display concept details and links.
                    </div>
                  `;
                }});
              </script>
            </body>
            </html>
            """
            components.html(html_code, height=600)
            
        else:
            # Document list browser
            # Build maps for easy lookup
            concepts_by_path = {c.path.resolve(): c for c in all_concepts if c.path}
            
            # Group concepts by document directory
            docs = {}
            for c in all_concepts:
                if c.path:
                    doc_dir = c.path.parent.name
                    docs.setdefault(doc_dir, []).append(c)
            
            sorted_doc_dirs = sorted(docs.keys())
            
            # UI Columns: Selector on left (1/3), concept detail on right (2/3)
            col_list, col_detail = st.columns([1, 2])
            
            with col_list:
                st.markdown("##### 📂 Documents")
                doc_display_names = {d: d.replace("-", " ").title() for d in sorted_doc_dirs}
                selected_doc_dir = st.selectbox(
                    "Select Document Folder",
                    options=sorted_doc_dirs,
                    format_func=lambda x: doc_display_names[x],
                    key="viewer_doc_select"
                )
                
                st.markdown("##### 📄 Concepts")
                doc_concepts = sorted(docs[selected_doc_dir], key=lambda c: c.title)
                
                # Find index of currently selected concept if it belongs to this doc
                selected_idx = 0
                if st.session_state.selected_concept_path:
                    resolved_selected = Path(st.session_state.selected_concept_path).resolve()
                    for idx, c in enumerate(doc_concepts):
                        if c.path.resolve() == resolved_selected:
                            selected_idx = idx
                            break
                
                # Select concept
                selected_concept = st.radio(
                    "Select Concept to View",
                    options=doc_concepts,
                    format_func=lambda c: c.title,
                    index=selected_idx,
                    key="concept_radio"
                )
                
                # Update selected path in session state
                if selected_concept:
                    st.session_state.selected_concept_path = str(selected_concept.path.resolve())

            with col_detail:
                if st.session_state.selected_concept_path:
                    curr_path = Path(st.session_state.selected_concept_path).resolve()
                    concept = concepts_by_path.get(curr_path)
                    
                    if concept:
                        # Title
                        st.markdown(f"### 📖 {concept.title}")
                        
                        # Metadata row
                        meta_html = f"""
                        <div style="display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;">
                            <span style="background-color: var(--bg-secondary); color: var(--text-secondary); padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; border: 1px solid var(--border-light);">
                                📁 Type: {concept.type}
                            </span>
                            <span style="background-color: var(--bg-secondary); color: var(--text-secondary); padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; border: 1px solid var(--border-light);">
                                📄 Source: {concept.resource}
                            </span>
                        </div>
                        """
                        st.markdown(meta_html, unsafe_allow_html=True)
                        
                        # Tags
                        if concept.tags:
                            tags_html = "".join([f'<span style="background-color: var(--accent-bg); color: var(--accent); padding: 2px 8px; border-radius: 12px; margin-right: 6px; font-size: 0.72rem; font-weight: 600;">#{tag}</span>' for tag in concept.tags])
                            st.markdown(f'<div style="margin-bottom: 15px;">{tags_html}</div>', unsafe_allow_html=True)
                        
                        st.divider()
                        
                        # Body (excluding the Related section)
                        body_to_render = concept.body
                        if "## Related" in body_to_render:
                            body_to_render = body_to_render.split("## Related")[0].strip()
                        
                        st.markdown(body_to_render)
                        
                        # Related concepts list
                        related_links = []
                        if concept.links:
                            for link in concept.links:
                                if link.endswith("index.md"):
                                    continue
                                link_path = (concept.path.parent / link).resolve()
                                neighbor = concepts_by_path.get(link_path)
                                if neighbor:
                                    related_links.append(neighbor)
                        
                        if related_links:
                            st.divider()
                            st.markdown("##### 🔗 Connected Concepts")
                            
                            cols = st.columns(min(len(related_links), 4))
                            for idx, neighbor in enumerate(related_links):
                                col_idx = idx % len(cols)
                                if cols[col_idx].button(f"📄 {neighbor.title}", key=f"nav_{neighbor.path.name}_{idx}", use_container_width=True):
                                    st.session_state.selected_concept_path = str(neighbor.path.resolve())
                                    st.rerun()
                    else:
                        st.info("Concept not found.")
                else:
                    st.info("Select a concept from the list on the left to begin.")
