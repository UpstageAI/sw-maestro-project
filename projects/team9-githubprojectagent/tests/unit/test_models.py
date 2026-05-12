"""Pydantic 모델 단위 테스트."""
import pytest
from pydantic import ValidationError
from src.models.story import Section, SectionScore, StoryDraft, Verdict, SECTION_ORDER
from src.models.repo import RepoContext, CommitInfo
from datetime import datetime


class TestSection:
    def test_create_valid_section(self):
        s = Section(name="problem", title="문제 인식", content="문제 내용입니다.")
        assert s.name == "problem"
        assert s.title == "문제 인식"

    def test_section_name_must_be_valid(self):
        with pytest.raises(ValidationError):
            Section(name="invalid_name", title="제목", content="내용")

    def test_section_sources_default_empty(self):
        s = Section(name="status", title="현황", content="내용")
        assert s.sources == []

    def test_section_sources_can_be_set(self):
        s = Section(name="cause", title="원인", content="내용", sources=["파일1.py", "파일2.py"])
        assert len(s.sources) == 2

    def test_all_valid_section_names(self):
        for name in ["problem", "status", "cause", "result"]:
            s = Section(name=name, title="제목", content="내용")
            assert s.name == name


class TestSectionScore:
    def test_create_valid_score(self):
        ss = SectionScore(name="problem", score=85, rationale="좋은 내용")
        assert ss.score == 85

    def test_score_minimum_is_zero(self):
        ss = SectionScore(name="problem", score=0, rationale="미흡")
        assert ss.score == 0

    def test_score_maximum_is_100(self):
        ss = SectionScore(name="result", score=100, rationale="완벽")
        assert ss.score == 100

    def test_score_below_zero_raises(self):
        with pytest.raises(ValidationError):
            SectionScore(name="problem", score=-1, rationale="잘못된 점수")

    def test_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            SectionScore(name="problem", score=101, rationale="잘못된 점수")


class TestStoryDraft:
    def test_create_empty_draft(self):
        draft = StoryDraft()
        assert draft.problem is None
        assert draft.status is None
        assert draft.cause is None
        assert draft.result is None
        assert draft.merged is None

    def test_set_and_get_section(self):
        draft = StoryDraft()
        section = Section(name="problem", title="문제 인식", content="내용")
        draft.set("problem", section)
        assert draft.get("problem") is section

    def test_set_all_sections(self):
        draft = StoryDraft()
        for name in SECTION_ORDER:
            s = Section(name=name, title="제목", content="내용")
            draft.set(name, s)
        for name in SECTION_ORDER:
            assert draft.get(name) is not None

    def test_architecture_and_dataflow_optional(self):
        draft = StoryDraft(
            architecture="```mermaid\ngraph TD\n  A-->B\n```",
            dataflow="```mermaid\nsequenceDiagram\n  A->>B: call\n```",
        )
        assert "mermaid" in draft.architecture
        assert "sequenceDiagram" in draft.dataflow

    def test_section_order_constant(self):
        assert SECTION_ORDER == ["problem", "status", "cause", "result"]


class TestVerdict:
    def test_create_passing_verdict(self):
        v = Verdict(
            scores=[SectionScore(name="problem", score=95, rationale="우수")],
            overall_pass=True,
            weakest="problem",
        )
        assert v.overall_pass is True

    def test_create_failing_verdict(self):
        v = Verdict(
            scores=[SectionScore(name="cause", score=60, rationale="미흡")],
            overall_pass=False,
            weakest="cause",
        )
        assert v.overall_pass is False

    def test_verdict_model_dump(self):
        v = Verdict(
            scores=[SectionScore(name="result", score=88, rationale="양호")],
            overall_pass=True,
            weakest="result",
        )
        d = v.model_dump()
        assert "scores" in d
        assert "overall_pass" in d
        assert "weakest" in d


class TestRepoContext:
    def test_full_name_property(self):
        ctx = RepoContext(owner="myuser", name="myrepo")
        assert ctx.full_name == "myuser/myrepo"

    def test_default_values(self):
        ctx = RepoContext(owner="a", name="b")
        assert ctx.stars == 0
        assert ctx.forks == 0
        assert ctx.is_private is False
        assert ctx.commits == []

    def test_create_with_all_fields(self):
        ctx = RepoContext(
            owner="octocat",
            name="Hello-World",
            description="테스트 레포",
            primary_language="Python",
            stars=100,
            readme="# Hello World",
        )
        assert ctx.description == "테스트 레포"
        assert ctx.stars == 100
