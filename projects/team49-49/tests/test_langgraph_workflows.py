import json
from pathlib import Path

from langgraph.graph.state import CompiledStateGraph

from app.repositories.sqlite import SQLiteRepository
from app.workflows.registry import get_workflow_registry
from app.workflows.qa import RetrievalQAWorkflow
from app.workflows.source_intake import SourceIntakeWorkflow
from app.workflows.storage import StorageWorkflow


class CountingRepository(SQLiteRepository):
    def __init__(self, path):
        super().__init__(path)
        self.list_relations_calls = 0

    def list_relations(self, workspace_id: int, card_id: int | None = None):
        self.list_relations_calls += 1
        return super().list_relations(workspace_id, card_id)


def test_storage_workflow_uses_compiled_langgraph(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")

    workflow = StorageWorkflow(repository)
    result = workflow.ingest_text(
        workspace_id=workspace["id"],
        filename="meeting.md",
        content="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )

    assert isinstance(workflow.graph, CompiledStateGraph)
    assert result["card_count"] == 1
    assert result["new_card_ids"] == [1]
    assert result["needs_review_count"] == 0
    assert repository.list_cards(workspace["id"])[0]["card_type"] == "decision"


def test_storage_workflow_exposes_card_extraction_studio_input_schema(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workflow = StorageWorkflow(repository)

    input_schema = workflow.graph.get_input_jsonschema()

    assert set(input_schema["required"]) == {"workspace_id", "filename", "content"}
    assert {
        "workspace_id",
        "filename",
        "content",
        "source_type",
        "source_url",
        "external_id",
        "document_id",
    } == set(input_schema["properties"])
    assert "stored_chunks" not in input_schema["properties"]
    assert "new_card_ids" not in input_schema["properties"]


def test_storage_workflow_reindexes_existing_document_cards(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    document = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="source.md",
        document_type="md",
        content="결정: 기존 원문은 SQLite relation 테이블을 우선 사용한다.",
    )

    workflow = StorageWorkflow(repository)
    first = workflow.reindex_document(document)
    assert first["card_count"] == 1
    assert repository.list_cards(workspace["id"])[0]["card_type"] == "decision"

    updated_document = repository.update_raw_document(document["id"], content="가설: 수정된 원문은 회의 준비 시간을 줄일 수 있다.")
    second = workflow.reindex_document(updated_document)

    assert second["card_count"] == 1
    cards = repository.list_cards(workspace["id"])
    assert len(cards) == 1
    assert cards[0]["card_type"] == "hypothesis"
    assert cards[0]["source_document_id"] == document["id"]


def test_storage_workflow_loads_existing_relations_once_for_batch(tmp_path):
    repository = CountingRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")

    StorageWorkflow(repository).ingest_text(
        workspace_id=workspace["id"],
        filename="meeting.md",
        content="\n".join(
            [
                "아이디어: 멘토링 준비 질문을 자동 정리한다.",
                "가설: 사용자는 멘토링 준비 시간을 줄이고 싶다.",
                "근거: 반복 회의에서 같은 질문이 계속 나온다.",
            ]
        ),
    )

    assert repository.list_relations_calls <= 1


def test_source_intake_workflow_uses_compiled_langgraph_for_pasted_content():
    workflow = SourceIntakeWorkflow()

    result = workflow.normalize(
        workspace_id=1,
        source_type="notion",
        source_url="https://notion.so/team/architecture",
        external_id="notion-page",
        title="architecture-note.md",
        content="결정: pasted content를 fetch보다 우선한다.",
    )

    assert isinstance(workflow.graph, CompiledStateGraph)
    assert result["filename"] == "architecture-note.md"
    assert result["content"] == "결정: pasted content를 fetch보다 우선한다."
    assert result["source_type"] == "notion"
    assert result["fetched_via"] == "pasted"


def test_qa_workflow_uses_compiled_langgraph(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    StorageWorkflow(repository).ingest_text(
        workspace_id=workspace["id"],
        filename="architecture.md",
        content="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )

    workflow = RetrievalQAWorkflow(repository)
    result = workflow.answer(workspace_id=workspace["id"], question="왜 GraphDB를 제외했어?")

    assert isinstance(workflow.graph, CompiledStateGraph)
    assert result["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."
    assert result["confidence"] == "low"


def test_qa_workflow_exposes_studio_input_and_context_schema(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workflow = RetrievalQAWorkflow(repository)

    input_schema = workflow.graph.get_input_jsonschema()
    context_schema = workflow.graph.get_context_jsonschema()
    context_schema_text = json.dumps(context_schema).lower()

    assert set(input_schema["required"]) == {"workspace_id", "question"}
    assert set(input_schema["properties"]) == {"workspace_id", "question"}
    assert {
        "answer_mode",
        "top_k",
        "system_prompt",
        "temperature",
        "max_tokens",
    } <= set(context_schema["properties"])
    assert "api_key" not in context_schema_text
    assert "access_token" not in context_schema_text
    assert "bearer" not in context_schema_text


def test_qa_workflow_can_run_in_studio_extract_mode_without_llm_key(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    repository.initialize()
    workspace = repository.create_workspace("SOMA 49")
    StorageWorkflow(repository).ingest_text(
        workspace_id=workspace["id"],
        filename="architecture.md",
        content="결정: MVP에서는 GraphDB 대신 SQLite relation 테이블을 사용한다.",
    )

    workflow = RetrievalQAWorkflow(repository)
    result = workflow.graph.invoke(
        {"workspace_id": workspace["id"], "question": "왜 GraphDB를 제외했어?"},
        context={"answer_mode": "extractive", "top_k": 1},
    )

    assert "UPSTAGE_API_KEY" not in result["answer"]
    assert result["cited_card_ids"]
    assert result["cited_chunk_ids"]


def test_source_intake_workflow_exposes_studio_input_schema():
    workflow = SourceIntakeWorkflow()

    input_schema = workflow.graph.get_input_jsonschema()

    assert set(input_schema["required"]) == {"workspace_id", "source_type"}
    assert {
        "workspace_id",
        "source_type",
        "source_url",
        "external_id",
        "title",
        "content",
    } == set(input_schema["properties"])
    assert "fetch_result" not in input_schema["properties"]
    assert "normalized" not in input_schema["properties"]


def test_workflow_registry_documents_team_extension_contracts():
    registry = get_workflow_registry()
    flow_ids = {flow["id"] for flow in registry["flows"]}

    assert registry["runtime"] == "LangGraph StateGraph"
    assert {"source_intake", "storage_preprocessing", "relation_linking", "retrieval_qa", "quality_review"} <= flow_ids
    assert any(flow["status"] == "implemented" and flow["workflow_file"] == "app/workflows/storage.py" for flow in registry["flows"])
    assert any(flow["status"] == "implemented" and flow["workflow_file"] == "app/workflows/qa.py" for flow in registry["flows"])
    assert all(flow["input_contract"] and flow["output_contract"] for flow in registry["flows"])


def test_storage_preprocessing_graph_is_available_for_local_studio():
    graph_dir = Path(__file__).resolve().parents[1] / "graphs" / "storage_preprocessing"

    assert (graph_dir / "graph.py").exists()
    assert (graph_dir / "langgraph.json").exists()
