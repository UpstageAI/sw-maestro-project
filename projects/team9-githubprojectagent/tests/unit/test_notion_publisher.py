"""notion_publisher.py 단위 테스트 — Notion API 호출 모킹."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.services.notion_publisher import publish, _backup_local
from src.models.repo import RepoContext
from src.models.story import Section, StoryDraft
from src.templates import get as get_template


@pytest.fixture
def ctx():
    return RepoContext(owner="testuser", name="testrepo", description="테스트 레포")


@pytest.fixture
def story():
    return StoryDraft(
        problem=Section(name="problem", title="문제 인식", content="문제 내용 " * 20),
        status=Section(name="status", title="현황 파악", content="현황 내용 " * 15),
        cause=Section(name="cause", title="원인 분석", content="원인 내용 " * 20),
        result=Section(name="result", title="결과 정리", content="결과 내용 " * 15),
    )


@pytest.fixture
def template():
    return get_template("star")


class TestBackupLocal:
    def test_creates_file(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            path = _backup_local(ctx, story, template)
        assert path.exists()

    def test_filename_contains_repo_name(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            path = _backup_local(ctx, story, template)
        assert "testrepo" in path.name

    def test_file_contains_full_name(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            path = _backup_local(ctx, story, template)
        content = path.read_text(encoding="utf-8")
        assert "testuser/testrepo" in content

    def test_file_contains_sections(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            path = _backup_local(ctx, story, template)
        content = path.read_text(encoding="utf-8")
        assert "문제 인식" in content


class TestPublish:
    def test_no_token_returns_failure(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            mock_cfg.NOTION_TOKEN = ""
            mock_cfg.NOTION_PARENT_PAGE_ID = ""
            result = publish(story, ctx, template)
        assert result["success"] is False
        assert "자격증명" in result["error"]

    def test_no_parent_page_returns_failure(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            mock_cfg.NOTION_TOKEN = "some-token"
            mock_cfg.NOTION_PARENT_PAGE_ID = ""
            result = publish(story, ctx, template, notion_token="some-token")
        assert result["success"] is False

    def test_backup_path_always_returned(self, ctx, story, template, tmp_path):
        with patch("src.services.notion_publisher.config") as mock_cfg:
            mock_cfg.OUTPUT_DIR = tmp_path
            mock_cfg.NOTION_TOKEN = ""
            mock_cfg.NOTION_PARENT_PAGE_ID = ""
            result = publish(story, ctx, template)
        assert "backup_path" in result
        assert result["backup_path"] is not None

    def test_with_mocked_notion_client_success(self, ctx, story, template, tmp_path):
        mock_page = {"id": "page-123", "url": "https://notion.so/page-123"}
        with patch("src.services.notion_publisher.config") as mock_cfg, \
             patch("src.services.notion_publisher.Client") as MockClient:
            mock_cfg.OUTPUT_DIR = tmp_path
            mock_cfg.NOTION_TOKEN = ""
            mock_cfg.NOTION_PARENT_PAGE_ID = ""
            mock_instance = MockClient.return_value
            mock_instance.pages.create.return_value = mock_page
            result = publish(
                story, ctx, template,
                parent_page_id="parent-page-id",
                notion_token="valid-token",
            )
        assert result["success"] is True
        assert result["page_url"] == "https://notion.so/page-123"

    def test_with_mocked_notion_client_api_error(self, ctx, story, template, tmp_path):
        from notion_client.errors import APIResponseError
        with patch("src.services.notion_publisher.config") as mock_cfg, \
             patch("src.services.notion_publisher.Client") as MockClient:
            mock_cfg.OUTPUT_DIR = tmp_path
            mock_cfg.NOTION_TOKEN = ""
            mock_cfg.NOTION_PARENT_PAGE_ID = ""
            mock_instance = MockClient.return_value
            # APIResponseError 시뮬레이션
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "Invalid request", "code": "validation_error"}
            mock_instance.pages.create.side_effect = APIResponseError(mock_response, "Invalid request", "validation_error")
            result = publish(
                story, ctx, template,
                parent_page_id="parent-page-id",
                notion_token="valid-token",
            )
        assert result["success"] is False
        assert "error" in result
