import io
import fitz  # PyMuPDF
import streamlit as st
import requests

API_BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(page_title="DocuMind AI", page_icon="🧠", layout="wide")

st.markdown("""
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
}
[data-testid="stMain"] {
    background: #0f1117;
}

/* ── Header bar ── */
.dm-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 18px 0 10px 0;
    border-bottom: 1px solid #23262f;
    margin-bottom: 24px;
}
.dm-header .dm-logo {
    font-size: 2rem;
    line-height: 1;
}
.dm-header .dm-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f0f2f6;
    letter-spacing: -0.5px;
    margin: 0;
}
.dm-header .dm-sub {
    font-size: 0.82rem;
    color: #6b7280;
    margin: 0;
}

/* ── Panel titles ── */
.dm-panel-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 12px;
}

/* ── Upload card ── */
.dm-upload-card {
    background: #16181f;
    border: 1px solid #23262f;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

/* ── Indexed doc list ── */
.dm-doc-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #16181f;
    border: 1px solid #23262f;
    border-radius: 8px;
    margin-bottom: 6px;
    font-size: 0.84rem;
    color: #d1d5db;
}
.dm-doc-item .dm-doc-icon { color: #f87171; }
.dm-doc-item .dm-doc-chunks {
    margin-left: auto;
    font-size: 0.75rem;
    color: #6b7280;
}

/* ── Chunk card inside expander ── */
.dm-chunk {
    background: #16181f;
    border-left: 3px solid #3b5bdb;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-bottom: 10px;
    font-size: 0.82rem;
    color: #9ca3af;
    line-height: 1.6;
}
.dm-chunk-header {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}

/* ── PDF preview page label ── */
.dm-page-label {
    font-size: 0.72rem;
    color: #4b5563;
    text-align: center;
    margin: 4px 0 14px 0;
}

/* ── Expander tweaks ── */
[data-testid="stExpander"] {
    background: #16181f !important;
    border: 1px solid #23262f !important;
    border-radius: 8px !important;
}

/* ── Divider ── */
hr { border-color: #23262f !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []        # list of {"name", "chunks"}
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None         # bytes of the last uploaded PDF
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="dm-header">
    <span class="dm-logo">🧠</span>
    <div>
        <p class="dm-title">DocuMind AI</p>
        <p class="dm-sub">Upload a PDF, then ask anything about it</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

left_col, right_col = st.columns([1, 2], gap="large")

# ── Left column ──────────────────────────────────────────────────────────────
with left_col:
    st.markdown('<p class="dm-panel-title">📂 Documents</p>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="dm-upload-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop a PDF here or click to browse",
            type=["pdf"],
            label_visibility="visible",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        # Always keep the latest file bytes available for preview
        file_bytes = uploaded_file.getvalue()
        if st.session_state.pdf_name != uploaded_file.name:
            st.session_state.pdf_bytes = file_bytes
            st.session_state.pdf_name = uploaded_file.name

        already_indexed = any(
            d["name"] == uploaded_file.name for d in st.session_state.indexed_docs
        )
        if not already_indexed:
            with st.spinner(f"Indexing **{uploaded_file.name}**…"):
                try:
                    response = requests.post(
                        f"{API_BASE}/upload",
                        files={"file": (uploaded_file.name, file_bytes, "application/pdf")},
                        timeout=120,
                    )
                    response.raise_for_status()
                    data = response.json()
                    st.session_state.indexed_docs.append(
                        {"name": uploaded_file.name, "chunks": data["chunks_indexed"]}
                    )
                    st.success(f"✅ Indexed **{data['chunks_indexed']}** chunks")
                except requests.exceptions.ConnectionError:
                    st.error("❌ API unreachable. Is `uvicorn api:app --reload` running?")
                except requests.exceptions.HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail", str(exc))
                    except Exception:
                        detail = exc.response.text or str(exc)
                    st.error(f"❌ {detail}")

    # Indexed document list
    if st.session_state.indexed_docs:
        st.markdown('<p class="dm-panel-title" style="margin-top:20px;">✅ Indexed</p>', unsafe_allow_html=True)
        for doc in st.session_state.indexed_docs:
            st.markdown(
                f'<div class="dm-doc-item">'
                f'<span class="dm-doc-icon">📄</span>'
                f'<span>{doc["name"]}</span>'
                f'<span class="dm-doc-chunks">{doc["chunks"]} chunks</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<p style="font-size:0.82rem;color:#4b5563;margin-top:8px;">'
            'No documents indexed yet.</p>',
            unsafe_allow_html=True,
        )

# ── Right column — tabbed: Chat | Preview ────────────────────────────────────
with right_col:
    chat_tab, preview_tab = st.tabs(["💬 Chat", "📄 Preview"])

    # ── Chat tab ─────────────────────────────────────────────────────────────
    with chat_tab:
        # Render existing conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("chunks"):
                    with st.expander(f"📎 View {len(msg['chunks'])} source chunks"):
                        for i, chunk in enumerate(msg["chunks"], start=1):
                            page = chunk["metadata"].get("page", "?")
                            source = chunk["metadata"].get("source", "unknown")
                            st.markdown(
                                f'<div class="dm-chunk">'
                                f'<div class="dm-chunk-header">Chunk {i} · {source} · Page {page}</div>'
                                f'{chunk["text"]}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

        # Empty state
        if not st.session_state.messages:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;">'
                '<div style="font-size:2.5rem;margin-bottom:12px;">💬</div>'
                '<p style="font-size:1rem;font-weight:600;color:#6b7280;">No messages yet</p>'
                '<p style="font-size:0.84rem;color:#4b5563;">Upload a PDF on the left, then ask a question below.</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        user_query = st.chat_input("Ask a question about your document…")

        if user_query:
            with st.chat_message("user"):
                st.markdown(user_query)
            st.session_state.messages.append(
                {"role": "user", "content": user_query, "chunks": []}
            )

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        response = requests.post(
                            f"{API_BASE}/chat",
                            json={"query": user_query},
                            timeout=60,
                        )
                        response.raise_for_status()
                        data = response.json()
                        answer = data["answer"]
                        chunks = data["chunks"]

                        st.markdown(answer)

                        with st.expander(f"📎 View {len(chunks)} source chunks"):
                            for i, chunk in enumerate(chunks, start=1):
                                page = chunk["metadata"].get("page", "?")
                                source = chunk["metadata"].get("source", "unknown")
                                st.markdown(
                                    f'<div class="dm-chunk">'
                                    f'<div class="dm-chunk-header">Chunk {i} · {source} · Page {page}</div>'
                                    f'{chunk["text"]}'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer, "chunks": chunks}
                        )

                    except requests.exceptions.ConnectionError:
                        err = "❌ Could not reach the API. Is `uvicorn api:app --reload` running?"
                        st.error(err)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": err, "chunks": []}
                        )
                    except requests.exceptions.HTTPError as exc:
                        try:
                            detail = exc.response.json().get("detail", str(exc))
                        except Exception:
                            detail = exc.response.text or str(exc)
                        err = f"❌ {detail}"
                        st.error(err)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": err, "chunks": []}
                        )

    # ── Preview tab ───────────────────────────────────────────────────────────
    with preview_tab:
        if st.session_state.pdf_bytes is None:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;">'
                '<div style="font-size:2.5rem;margin-bottom:12px;">📄</div>'
                '<p style="font-size:1rem;font-weight:600;color:#6b7280;">No document loaded</p>'
                '<p style="font-size:0.84rem;color:#4b5563;">Upload a PDF on the left to preview it here.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            pdf_doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            total_pages = pdf_doc.page_count

            st.markdown(
                f'<p class="dm-panel-title">{st.session_state.pdf_name} '
                f'<span style="color:#4b5563;font-weight:400;">· {total_pages} pages</span></p>',
                unsafe_allow_html=True,
            )

            # Page selector
            page_num = st.slider(
                "Page", min_value=1, max_value=total_pages, value=1,
                label_visibility="collapsed",
            )

            # Render selected page to PNG via fitz
            page = pdf_doc[page_num - 1]
            mat = fitz.Matrix(2.0, 2.0)   # 2× scale for sharp rendering
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")

            st.image(
                io.BytesIO(img_bytes),
                caption=f"Page {page_num} of {total_pages}",
                use_column_width="always",
            )

            pdf_doc.close()
