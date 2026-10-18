import os
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from ingest import process_pdf
from database import add_chunks, hybrid_search

load_dotenv()

app = FastAPI(title="DocuMind AI")

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    chunks: list


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are DocuMind AI, a precise document-analysis assistant.

Rules you MUST follow without exception:
1. Answer the user's question using ONLY the document chunks provided below.
2. Do NOT use any outside knowledge or make assumptions beyond what is in the chunks.
3. After EVERY individual fact or sentence you state, append a citation in the
   format [Page X], where X is the page number from the chunk's metadata.
4. If the provided chunks do not contain enough information to answer the
   question, respond exactly with:
   "I don't have enough information in the provided documents to answer that."
5. Never fabricate citations or page numbers.

Document chunks:
{context}"""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Accept a PDF upload, extract and chunk its text, then store the chunks
    in the Qdrant in-memory collection.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Write the upload to a temp file so fitz can open it by path
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = process_pdf(tmp_path)
        # Preserve the original filename in metadata instead of the temp path
        for chunk in chunks:
            chunk["metadata"]["source"] = file.filename
        add_chunks(chunks)
    finally:
        os.remove(tmp_path)

    return {
        "message": f"'{file.filename}' processed successfully.",
        "chunks_indexed": len(chunks),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Run a hybrid search for the query, build a grounded context window,
    and return the LLM answer together with the retrieved chunks.
    """
    retrieved = hybrid_search(request.query, top_k=5)

    if not retrieved:
        raise HTTPException(
            status_code=404,
            detail="No relevant chunks found. Please upload a document first.",
        )

    # Build the context block injected into the system prompt
    context_lines = []
    for i, chunk in enumerate(retrieved, start=1):
        source = chunk["metadata"].get("source", "unknown")
        page = chunk["metadata"].get("page", "?")
        context_lines.append(
            f"[Chunk {i} | Source: {source} | Page {page}]\n{chunk['text']}"
        )
    context = "\n\n".join(context_lines)

    llm = ChatOllama(
        model="llama3.2",
        temperature=0,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(context=context)),
        HumanMessage(content=request.query),
    ]

    response = llm.invoke(messages)

    return ChatResponse(
        answer=response.content,
        chunks=retrieved,
    )
