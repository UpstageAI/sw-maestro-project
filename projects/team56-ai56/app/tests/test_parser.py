from app.services.parser import ResumeParser


def test_parser_extracts_section_summaries() -> None:
    parser = ResumeParser()
    parsed = parser.parse_text(
        """
        [한 줄 소개]
        Python과 FastAPI 중심의 백엔드 지원자입니다.

        [기술]
        Python, FastAPI, SQL

        [프로젝트 1]
        FastAPI 기반 주문 API 구현
        SQLite 저장소 설계

        [경력]
        백엔드 스터디 운영
        API 설계 세션 진행

        [학력]
        컴퓨터공학과 재학
        데이터베이스 수업 수강

        [협업]
        GitHub PR 리뷰와 README 문서화 경험
        """
    )

    assert parsed.profile.section_summaries["summary"][0] == "Python과 FastAPI 중심의 백엔드 지원자입니다."
    assert parsed.profile.section_summaries["projects"][0] == "FastAPI 기반 주문 API 구현"
    assert parsed.profile.section_summaries["collaboration"][0] == "GitHub PR 리뷰와 README 문서화 경험"
    assert parsed.profile.projects[0] == "FastAPI 기반 주문 API 구현"
    assert parsed.profile.structured_projects[0].name == "FastAPI 기반 주문 API 구현"
    assert set(parsed.profile.structured_projects[0].skills) >= {"python", "fastapi", "sql"}
    assert parsed.profile.structured_experience[0].title == "백엔드 스터디 운영"
    assert parsed.profile.structured_education[0].title == "컴퓨터공학과 재학"
