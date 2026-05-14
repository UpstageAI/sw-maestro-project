from app.repositories.sqlite import SQLiteRepository


def test_repository_persists_workspace_document_chunk_card_relation_and_chat(tmp_path):
    repo = SQLiteRepository(tmp_path / "ich.sqlite3")
    repo.initialize()

    workspace = repo.create_workspace("SOMA 49", "Ideation sample workspace")
    assert workspace["id"] == 1
    assert workspace["name"] == "SOMA 49"

    document = repo.create_raw_document(
        workspace_id=workspace["id"],
        filename="meeting.md",
        document_type="md",
        content="가설: 사용자는 멘토링 준비 시간을 줄이고 싶다.",
    )
    assert document["id"] == 1
    assert document["content"].startswith("가설:")

    chunks = repo.create_chunks(
        document_id=document["id"],
        workspace_id=workspace["id"],
        contents=["가설: 사용자는 멘토링 준비 시간을 줄이고 싶다."],
    )
    assert chunks[0]["chunk_index"] == 0

    card = repo.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunks[0]["id"],
        card_type="hypothesis",
        title="멘토링 준비 시간 절감 가설",
        summary="사용자는 멘토링 준비 시간을 줄이고 싶어 한다.",
        evidence_quote="가설: 사용자는 멘토링 준비 시간을 줄이고 싶다.",
        keywords=["멘토링", "준비 시간"],
        tags=["needs_validation"],
        status="needs_validation",
        confidence="medium",
    )
    assert card["id"] == 1
    assert card["keywords"] == ["멘토링", "준비 시간"]

    relation = repo.create_relation(
        workspace_id=workspace["id"],
        source_card_id=card["id"],
        target_card_id=card["id"],
        relation_type="derived_from",
        reason="카드가 원문 chunk에서 추출됨",
        confidence="high",
    )
    assert relation["relation_type"] == "derived_from"

    chat = repo.create_chat_history(
        workspace_id=workspace["id"],
        question="왜 멘토링 준비가 중요한가?",
        answer="저장된 컨텍스트 기준으로 준비 시간 절감 가설이 있습니다.",
        referenced_card_ids=[card["id"]],
        referenced_chunk_ids=[chunks[0]["id"]],
    )
    assert chat["referenced_card_ids"] == [card["id"]]

    assert repo.list_workspaces()[0]["name"] == "SOMA 49"
    assert repo.list_raw_documents(workspace["id"])[0]["filename"] == "meeting.md"
    assert repo.list_chunks(workspace["id"])[0]["content"].startswith("가설:")
    assert repo.list_cards(workspace["id"], card_type="hypothesis")[0]["title"] == "멘토링 준비 시간 절감 가설"
    assert repo.list_relations(workspace["id"], card_id=card["id"])[0]["reason"] == "카드가 원문 chunk에서 추출됨"
    assert repo.list_chat_history(workspace["id"])[0]["question"] == "왜 멘토링 준비가 중요한가?"


def test_repository_updates_and_deletes_workspace_with_cascade(tmp_path):
    repo = SQLiteRepository(tmp_path / "ich.sqlite3")
    repo.initialize()
    workspace = repo.create_workspace("Before", "initial")
    document = repo.create_raw_document(workspace["id"], "source.md", "md", "결정: 유지한다.")
    chunk = repo.create_chunks(document["id"], workspace["id"], ["결정: 유지한다."])[0]
    repo.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunk["id"],
        card_type="decision",
        title="유지 결정",
        summary="유지한다.",
        evidence_quote="결정: 유지한다.",
        keywords=["유지"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )

    updated = repo.update_workspace(workspace["id"], name="After", description="updated")
    assert updated["name"] == "After"
    assert updated["description"] == "updated"

    repo.delete_workspace(workspace["id"])
    assert repo.list_workspaces() == []
    assert repo.list_raw_documents(workspace["id"]) == []
    assert repo.list_cards(workspace["id"]) == []


def test_repository_updates_and_deletes_full_card_fields(tmp_path):
    repo = SQLiteRepository(tmp_path / "ich.sqlite3")
    repo.initialize()
    workspace = repo.create_workspace("Cards")
    document = repo.create_raw_document(workspace["id"], "source.md", "md", "결정: SQLite")
    chunk = repo.create_chunks(document["id"], workspace["id"], ["결정: SQLite"])[0]
    card = repo.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=document["id"],
        source_chunk_id=chunk["id"],
        card_type="decision",
        title="SQLite",
        summary="SQLite를 쓴다.",
        evidence_quote="결정: SQLite",
        keywords=["SQLite"],
        tags=["decided"],
        status="decided",
        confidence="high",
    )

    updated = repo.update_card(
        card["id"],
        card_type="hypothesis",
        title="회의 준비",
        summary="회의 준비 시간이 줄어든다.",
        evidence_quote="가설: 회의 준비 시간이 줄어든다.",
        keywords=["회의", "준비"],
        tags=["needs_validation"],
        status="needs_validation",
        confidence="medium",
    )
    assert updated["card_type"] == "hypothesis"
    assert updated["title"] == "회의 준비"
    assert updated["keywords"] == ["회의", "준비"]
    assert updated["tags"] == ["needs_validation"]

    repo.delete_card(card["id"])
    assert repo.list_cards(workspace["id"]) == []
