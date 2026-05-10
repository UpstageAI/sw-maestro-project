"""모든 템플릿 preview_md / render 단위 테스트."""
import pytest
from src.models.repo import RepoContext
from src.models.story import Section, StoryDraft
from src.templates import get, list_all
from src.templates import star, minimal, detailed, cover, project_record, troubleshooting


@pytest.fixture
def ctx():
    return RepoContext(
        owner="testuser",
        name="testrepo",
        description="테스트용 포트폴리오 레포",
        primary_language="Python",
        stars=10,
    )


@pytest.fixture
def full_draft():
    return StoryDraft(
        problem=Section(name="problem", title="문제 인식", content="문제 상황을 설명합니다. " * 10),
        status=Section(name="status", title="현황 파악", content="현재 기술 스택을 설명합니다. " * 10),
        cause=Section(name="cause", title="원인 분석", content="원인을 분석하고 해결책을 제시합니다. " * 10),
        result=Section(name="result", title="결과 정리", content="최종 결과와 성과를 정리합니다. " * 10),
        architecture="```mermaid\ngraph TD\n  A[Client] --> B[FastAPI]\n```",
        dataflow="```mermaid\nsequenceDiagram\n  Client->>API: POST /session\n```",
        merged="## 전체 내용\n\n최종 병합된 내용입니다.",
    )


@pytest.fixture
def partial_draft():
    return StoryDraft(
        problem=Section(name="problem", title="문제 인식", content="문제 내용"),
        # status, cause, result 없음
    )


# ──────────────────────────────────────────────
# templates/__init__
# ──────────────────────────────────────────────

class TestTemplateRegistry:
    def test_get_valid_template(self):
        t = get("star")
        assert t.id == "star"

    def test_get_invalid_raises(self):
        with pytest.raises(ValueError, match="unknown template"):
            get("nonexistent")

    def test_list_all_returns_all_templates(self):
        templates = list_all()
        assert len(templates) == 6

    def test_all_template_ids_unique(self):
        ids = [t.id for t in list_all()]
        assert len(ids) == len(set(ids))

    def test_all_templates_have_name(self):
        for t in list_all():
            assert t.name


# ──────────────────────────────────────────────
# STAR 템플릿
# ──────────────────────────────────────────────

class TestStarTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = star.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_preview_contains_full_name(self, full_draft, ctx):
        assert "testuser/testrepo" in star.preview(full_draft, ctx)

    def test_preview_contains_star_labels(self, full_draft, ctx):
        result = star.preview(full_draft, ctx)
        assert "[S]" in result
        assert "[T]" in result
        assert "[A]" in result
        assert "[R]" in result

    def test_preview_contains_architecture(self, full_draft, ctx):
        assert "mermaid" in star.preview(full_draft, ctx)

    def test_render_returns_list(self, full_draft, ctx):
        blocks = star.render(full_draft, ctx)
        assert isinstance(blocks, list)
        assert len(blocks) > 0

    def test_render_partial_draft(self, partial_draft, ctx):
        # 일부 섹션만 있어도 오류 없이 동작
        blocks = star.render(partial_draft, ctx)
        assert isinstance(blocks, list)

    def test_preview_without_architecture(self, ctx):
        draft = StoryDraft(
            problem=Section(name="problem", title="문제", content="내용")
        )
        result = star.preview(draft, ctx)
        assert "참고 — 시스템 아키텍처" not in result


# ──────────────────────────────────────────────
# Minimal 템플릿
# ──────────────────────────────────────────────

class TestMinimalTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = minimal.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_preview_contains_full_name(self, full_draft, ctx):
        assert "testuser/testrepo" in minimal.preview(full_draft, ctx)

    def test_render_returns_blocks(self, full_draft, ctx):
        blocks = minimal.render(full_draft, ctx)
        assert isinstance(blocks, list)


# ──────────────────────────────────────────────
# Detailed 템플릿
# ──────────────────────────────────────────────

class TestDetailedTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = detailed.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_render_returns_blocks(self, full_draft, ctx):
        blocks = detailed.render(full_draft, ctx)
        assert isinstance(blocks, list)

    def test_preview_contains_sections(self, full_draft, ctx):
        result = detailed.preview(full_draft, ctx)
        assert "문제 인식" in result or "problem" in result.lower()


# ──────────────────────────────────────────────
# Cover 템플릿
# ──────────────────────────────────────────────

class TestCoverTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = cover.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_render_returns_blocks(self, full_draft, ctx):
        blocks = cover.render(full_draft, ctx)
        assert isinstance(blocks, list)


# ──────────────────────────────────────────────
# Project Record 템플릿
# ──────────────────────────────────────────────

class TestProjectRecordTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = project_record.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_render_returns_blocks(self, full_draft, ctx):
        blocks = project_record.render(full_draft, ctx)
        assert isinstance(blocks, list)


# ──────────────────────────────────────────────
# Troubleshooting 템플릿
# ──────────────────────────────────────────────

class TestTroubleshootingTemplate:
    def test_preview_returns_string(self, full_draft, ctx):
        result = troubleshooting.preview(full_draft, ctx)
        assert isinstance(result, str)

    def test_render_returns_blocks(self, full_draft, ctx):
        blocks = troubleshooting.render(full_draft, ctx)
        assert isinstance(blocks, list)

    def test_render_partial_draft_no_error(self, partial_draft, ctx):
        blocks = troubleshooting.render(partial_draft, ctx)
        assert isinstance(blocks, list)
