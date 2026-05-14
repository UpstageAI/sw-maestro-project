from typing import Any

from app.repositories.sqlite import SQLiteRepository
from app.services.vector_store import LocalVectorStore


class RetrievalService:
    def __init__(self, repository: SQLiteRepository, vector_store: LocalVectorStore | None = None):
        self.repository = repository
        self.vector_store = vector_store or LocalVectorStore()

    def search(
        self,
        workspace_id: int,
        query: str,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        filters = {key: value for key, value in (filters or {}).items() if value}
        cards = self._list_filtered_cards(workspace_id, filters)
        chunks = self._list_filtered_chunks(workspace_id, filters)
        card_items = [
            {
                **card,
                "search_text": f"{card['title']} {card['summary']} {' '.join(card['keywords'])} {' '.join(card['tags'])}",
            }
            for card in cards
        ]
        chunk_items = [{**chunk, "search_text": chunk["content"]} for chunk in chunks]
        ranked_cards = self.vector_store.rank(query, card_items, text_key="search_text", top_k=top_k)
        ranked_chunks = self.vector_store.rank(query, chunk_items, text_key="search_text", top_k=top_k)
        self._apply_metadata_tiebreak(ranked_cards, filters, metadata_keys=("card_type", "status", "confidence", "source_type"))
        self._apply_metadata_tiebreak(ranked_chunks, filters, metadata_keys=("source_type",))
        for card in ranked_cards:
            card.pop("search_text", None)
        for chunk in ranked_chunks:
            chunk.pop("search_text", None)
        return {"cards": ranked_cards, "chunks": ranked_chunks}

    def _list_filtered_cards(self, workspace_id: int, filters: dict[str, str]) -> list[dict[str, Any]]:
        cards = self.repository.list_cards(
            workspace_id,
            card_type=filters.get("card_type"),
            status=filters.get("status"),
            confidence=filters.get("confidence"),
        )
        source_type = filters.get("source_type")
        if not source_type:
            return cards
        document_index = self._document_index(workspace_id)
        return [
            {**card, "source_type": document_index.get(card["source_document_id"], "")}
            for card in cards
            if document_index.get(card["source_document_id"]) == source_type
        ]

    def _list_filtered_chunks(self, workspace_id: int, filters: dict[str, str]) -> list[dict[str, Any]]:
        chunks = self.repository.list_chunks(workspace_id)
        source_type = filters.get("source_type")
        if not source_type:
            return chunks
        document_index = self._document_index(workspace_id)
        return [
            {**chunk, "source_type": document_index.get(chunk["document_id"], "")}
            for chunk in chunks
            if document_index.get(chunk["document_id"]) == source_type
        ]

    def _document_index(self, workspace_id: int) -> dict[int, str]:
        return {
            document["id"]: document.get("source_type", "")
            for document in self.repository.list_raw_documents(workspace_id)
        }

    @staticmethod
    def _apply_metadata_tiebreak(
        items: list[dict[str, Any]],
        filters: dict[str, str],
        metadata_keys: tuple[str, ...],
    ) -> None:
        if not items:
            return
        items.sort(
            key=lambda item: (
                -float(item.get("score") or 0),
                -sum(1 for key in metadata_keys if filters.get(key) and item.get(key) == filters[key]),
                -int(item.get("id") or 0),
            )
        )

    def expand_one_hop_relations(self, workspace_id: int, card_ids: list[int]) -> list[dict[str, Any]]:
        seen_relation_ids: set[int] = set()
        relations: list[dict[str, Any]] = []
        for card_id in card_ids:
            for relation in self.repository.list_relations(workspace_id, card_id=card_id):
                if relation["id"] not in seen_relation_ids:
                    seen_relation_ids.add(relation["id"])
                    relations.append(relation)
        return relations

    def expand_with_neighbor_cards(
        self, workspace_id: int, card_ids: list[int]
    ) -> dict[str, list[dict[str, Any]]]:
        relations = self.expand_one_hop_relations(workspace_id, card_ids)
        seed_ids = set(card_ids)
        neighbor_ids: set[int] = set()
        for r in relations:
            for nid in (r["source_card_id"], r["target_card_id"]):
                if nid not in seed_ids:
                    neighbor_ids.add(nid)
        neighbor_cards: list[dict[str, Any]] = []
        for nid in neighbor_ids:
            try:
                neighbor_cards.append(self.repository.get_card(nid))
            except KeyError:
                pass
        return {"relations": relations, "neighbor_cards": neighbor_cards}
