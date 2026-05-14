"""Build the persona embedding JSON cache used by f1_select pre-ranking."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_upstage import UpstageEmbeddings

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.persona_repository import load_personas  # noqa: E402
from services.persona_retrieval import (  # noqa: E402
    DEFAULT_CACHE_PATH,
    EMBEDDING_MODEL,
    persona_selection_text,
    persona_text_hash,
)


def build_cache(output_path: Path = DEFAULT_CACHE_PATH) -> Path:
    load_dotenv()

    personas = load_personas()
    texts = [persona_selection_text(card) for card in personas]
    embeddings = UpstageEmbeddings(
        model=EMBEDDING_MODEL,
        timeout=120.0,
        max_retries=3,
    ).embed_documents(texts)

    items = [
        {
            "card_id": card.card_id,
            "text_hash": persona_text_hash(text),
            "embedding": embedding,
        }
        for card, text, embedding in zip(personas, texts, embeddings, strict=True)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"model": EMBEDDING_MODEL, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(items)} persona embeddings to {output_path}")
    return output_path


if __name__ == "__main__":
    build_cache()
