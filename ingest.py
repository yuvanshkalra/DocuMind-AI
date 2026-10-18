import os
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_pdf(file_path: str) -> list:
    """
    Read a PDF file page by page, split each page's text into chunks,
    and attach source/page metadata to every chunk.

    Args:
        file_path: Absolute or relative path to the PDF file.

    Returns:
        A list of dicts, each with 'text' and 'metadata' keys.
    """
    filename = os.path.basename(file_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = []

    with fitz.open(file_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()
            if not text.strip():
                continue

            page_chunks = splitter.split_text(text)

            for chunk_text in page_chunks:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source": filename,
                        "page": page_number,
                    },
                })

    return chunks
