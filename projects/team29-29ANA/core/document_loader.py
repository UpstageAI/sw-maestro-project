import os
import uuid
from pathlib import Path

import chromadb
from pypdf import PdfReader

CHUNK_SIZE = 1500
OVERLAP = 200
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"


def load_documents(pdf_paths: list[str]) -> str:
    """PDF 파일들을 ChromaDB에 인덱싱하고 collection_name 반환"""
    if not pdf_paths:
        raise ValueError("PDF 파일 목록이 비어 있습니다")

    collection_name = f"session_{uuid.uuid4().hex[:8]}"

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    for doc_index, path in enumerate(pdf_paths):
        if not path.lower().endswith(".pdf"):
            raise ValueError(f"PDF 파일만 지원합니다: {path}")

        p = Path(path)
        if not p.exists():
            raise ValueError(f"파일을 찾을 수 없습니다: {path}")
        if not p.is_file():
            raise ValueError(f"경로가 파일이 아닙니다: {path}")

        try:
            reader = PdfReader(path)
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            full_text = "\n".join(pages_text)
        except Exception as e:
            raise ValueError(f"PDF 텍스트 추출 실패: {path}") from e

        if len(full_text) < 100:
            raise ValueError(f"문서 내용이 너무 짧습니다: {path}")

        filename = os.path.basename(path)
        chunks = _chunk_text(full_text, CHUNK_SIZE, OVERLAP)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({"source": filename, "chunk_index": i})
            all_ids.append(f"{collection_name}_doc{doc_index}_{filename}_chunk_{i}")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.create_collection(collection_name)
    collection.add(documents=all_chunks, metadatas=all_metadatas, ids=all_ids)

    return collection_name


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError(f"overlap({overlap})은 chunk_size({chunk_size})보다 작아야 합니다")
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
