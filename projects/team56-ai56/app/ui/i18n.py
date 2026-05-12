from __future__ import annotations


TRANSLATIONS = {
    "ko": {
        "page_title": "HireProof MVP",
        "caption": "개인정보 보호 중심 채용 검토 데모",
        "mode": "모드",
        "language": "언어",
        "evaluator": "평가 엔진",
        "mock_notice": "현재 빌드는 Upstage 연동 전까지 mock 평가기를 기본으로 사용합니다.",
        "create_job": "1. 채용 공고 만들기",
        "job_title": "채용 포지션명",
        "jd_text": "JD 본문",
        "create_job_button": "채용 공고 생성",
        "job_required": "포지션명과 JD 본문이 모두 필요합니다.",
        "job_created": "채용 공고가 생성되었습니다:",
        "no_jobs": "아직 생성된 채용 공고가 없습니다. 위에서 먼저 만들어주세요.",
        "select_job": "채용 공고 선택",
        "criteria_review": "2. 추천 평가 기준 검토",
        "criterion": "기준",
        "criterion_name": "기준 이름",
        "criterion_description": "기준 설명",
        "criterion_weight": "가중치",
        "confirm_criteria": "이 채용 공고 기준 확정",
        "criteria_confirmed": "평가 기준이 확정되었습니다.",
        "add_candidate": "3. 후보자 추가",
        "resume_file": "이력서 파일",
        "resume_text_fallback": "이력서 텍스트 대체 입력",
        "resume_text_placeholder": "파일이 없으면 이력서나 자기소개서 텍스트를 붙여넣어 주세요.",
        "candidate_name": "후보자 이름",
        "candidate_name_hint": "이 값은 로컬에만 저장됩니다.",
        "github_url": "GitHub URL",
        "portfolio_url": "포트폴리오 URL",
        "parsed_profile": "파싱된 프로필",
        "detected_urls": "감지된 URL",
        "masking_preview": "마스킹 미리보기",
        "llm_safe": "LLM 전송 가능 여부",
        "add_candidate_button": "후보자 추가 및 평가 실행",
        "candidate_evaluated": "후보자 평가가 완료되었습니다.",
        "candidate_input_required": "평가 전에 이력서 파일을 올리거나 텍스트를 입력해 주세요.",
        "ranking": "4. 랭킹",
        "job_overview": "진행 요약",
        "total_candidates": "후보 수",
        "evaluated_candidates": "평가 완료",
        "github_fetched": "GitHub 조회 성공",
        "avg_jd_score": "평균 JD 점수",
        "avg_alignment_score": "평균 정합도 점수",
        "job_status": "채용 공고 상태",
        "no_evaluations": "아직 평가 결과가 없습니다.",
        "candidate_detail": "후보자 상세",
        "rank": "순위",
        "fit_band": "적합도 밴드",
        "projects": "프로젝트",
        "experience": "경력",
        "education": "학력",
        "sort_by": "정렬 기준",
        "sort_jd_score": "JD 점수",
        "sort_alignment_score": "정합도 점수",
        "sort_name": "이름",
        "compare_candidates": "후보 비교",
        "left_candidate": "왼쪽 후보",
        "right_candidate": "오른쪽 후보",
        "github_status_label": "GitHub 상태",
        "audit_filter": "감사 로그 필터",
        "audit_search": "감사 로그 검색",
        "audit_limit": "표시 개수",
        "all": "전체",
        "status_fetched": "조회 성공",
        "status_failed": "조회 실패",
        "status_skipped": "건너뜀",
        "status_not_requested": "미요청",
        "status_top": "상위",
        "status_mid": "중간",
        "status_review": "검토 필요",
        "evaluation_summary": "평가 요약",
        "evidence": "근거",
        "candidate_profile": "후보자 프로필",
        "structured_resume": "구조화 이력서 JSON",
        "section_summaries": "섹션 요약",
        "extracted_urls": "추출된 URL",
        "github_verification": "GitHub 검증",
        "github_repo_analysis": "GitHub 레포 분석",
        "detected_frameworks": "감지된 프레임워크/신호",
        "sample_code_paths": "샘플 코드 경로",
        "status": "상태",
        "token_mappings": "토큰 매핑",
        "no_token_mappings": "기록된 토큰 매핑이 없습니다.",
        "original_resume": "원본 이력서 텍스트",
        "masked_resume": "마스킹된 이력서 텍스트",
        "audit_logs": "5. 감사 로그",
        "no_audit_logs": "이 채용 공고에는 아직 감사 로그가 없습니다.",
        "chat_title": "HireProof Chat",
        "chat_subtitle": "대화로 채용 평가를 진행합니다.",
        "chat_new_job": "+ 새 채용 공고 시작",
        "chat_input_placeholder": "메시지를 입력하세요. /help 로 도움말 보기",
        "chat_intro": (
            "안녕하세요! HireProof 채용 평가를 시작합니다.\n\n"
            "먼저 새 **채용 공고**를 만들어 볼게요. 채용 포지션명을 한 줄로 입력하거나, 첫 줄에 포지션명·둘째 줄부터 JD 본문을 한 번에 붙여넣어 주세요.\n\n"
            "예: `백엔드 인턴`"
        ),
        "chat_help_global": (
            "**전역 명령어**\n"
            "- `/restart` 새 공고로 다시 시작\n"
            "- `/help` 도움말\n"
            "- `/results` 현재 공고 평가 결과 보기\n\n"
            "**기준 검토 단계**: `/confirm`, `/weight N <0~100>`, `/edit N <이름>|<설명>|<가중치>`, `/remove N`\n\n"
            "**후보자 단계**: `/name <이름>`, `/github <URL>`, `/portfolio <URL>`, 그리고 입력창 위에서 이력서 파일 업로드. 200자 이상의 텍스트를 직접 붙여넣어도 평가됩니다 (`/name` 으로 이름 먼저 등록).\n\n"
            "**결과 단계**: `/detail N`, `/back` (후보자 추가로 돌아가기)"
        ),
        "chat_ask_jd_body": "포지션 `{title}` 으로 진행할게요. 이제 **JD 본문**을 붙여넣어 주세요.",
        "chat_jd_required": "포지션명과 JD 본문이 모두 필요합니다.",
        "chat_job_created": "채용 공고 **{title}** 가 생성되었습니다. 추천 평가 기준은 다음과 같습니다.",
        "chat_no_criteria": "추천 기준이 없습니다.",
        "chat_criteria_help": (
            "기준이 마음에 들면 `/confirm` 으로 확정하세요.\n"
            "수정: `/weight N 30` · `/edit N 새이름|새설명|가중치` · `/remove N`"
        ),
        "chat_criteria_confirmed_next": (
            "평가 기준이 확정되었습니다. 이제 **후보자**를 추가해 주세요.\n\n"
            "1. 입력창 위에서 이력서 파일을 업로드하고 후보자 이름을 입력한 뒤 `평가 시작` 버튼을 누르거나,\n"
            "2. `/name <이름>` 후 200자 이상의 이력서 텍스트를 붙여넣으세요.\n\n"
            "끝났다면 `/done` 으로 결과를 확인할 수 있습니다."
        ),
        "chat_candidate_help": (
            "후보자를 추가하려면:\n"
            "- 입력창 위 업로더로 이력서 파일을 올린 뒤 이름을 입력하고 `평가 시작` 클릭\n"
            "- 또는 `/name <이름>`, `/github <URL>` 등으로 메타데이터를 등록한 뒤 이력서 텍스트(200자 이상)를 붙여넣기\n\n"
            "다음 단계로: `/done` (결과 보기)"
        ),
        "chat_candidate_name_set": "후보자 이름을 `{name}` 로 설정했습니다.",
        "chat_candidate_github_set": "GitHub URL을 `{url}` 로 설정했습니다.",
        "chat_candidate_portfolio_set": "포트폴리오 URL을 `{url}` 로 설정했습니다.",
        "chat_candidate_added": "**{name}** 후보자가 등록·평가되었습니다.",
        "chat_next_candidate": "다음 후보자를 추가하거나, `/done` 으로 랭킹을 확인하세요.",
        "chat_results_help": "명령: `/detail N` 상세 보기 · `/back` 후보자 추가로 돌아가기 · `/restart` 새 공고",
        "chat_no_job": "현재 활성화된 공고가 없습니다. `/restart` 로 새 공고를 시작하세요.",
        "chat_upload_section": "이력서 파일 업로드",
        "chat_start_evaluation": "평가 시작",
        "chat_upload_hint": "파일을 올리고 후보자 이름을 입력한 뒤 `평가 시작` 버튼을 눌러주세요.",
    },
    "en": {
        "page_title": "HireProof MVP",
        "caption": "Privacy-first hiring review demo",
        "mode": "Mode",
        "language": "Language",
        "evaluator": "Evaluator",
        "mock_notice": "This build uses the mock evaluator until the Upstage integration is enabled.",
        "create_job": "1. Create Job",
        "job_title": "Job title",
        "jd_text": "JD text",
        "create_job_button": "Create job",
        "job_required": "Job title and JD text are both required.",
        "job_created": "Created job:",
        "no_jobs": "No jobs yet. Create one above to start.",
        "select_job": "Select job",
        "criteria_review": "2. Review Suggested Criteria",
        "criterion": "Criterion",
        "criterion_name": "Criterion name",
        "criterion_description": "Criterion description",
        "criterion_weight": "Weight",
        "confirm_criteria": "Confirm criteria for this job",
        "criteria_confirmed": "Criteria confirmed.",
        "add_candidate": "3. Add Candidate",
        "resume_file": "Resume file",
        "resume_text_fallback": "Resume text fallback",
        "resume_text_placeholder": "Paste resume or self-introduction text here if you are not uploading a file.",
        "candidate_name": "Candidate name",
        "candidate_name_hint": "This stays local only.",
        "github_url": "GitHub URL",
        "portfolio_url": "Portfolio URL",
        "parsed_profile": "Parsed profile",
        "detected_urls": "Detected URLs",
        "masking_preview": "Masking preview",
        "llm_safe": "LLM safe",
        "add_candidate_button": "Add candidate and evaluate",
        "candidate_evaluated": "Candidate evaluated.",
        "candidate_input_required": "Upload a resume file or paste resume text before evaluating.",
        "ranking": "4. Ranking",
        "job_overview": "Job Overview",
        "total_candidates": "Candidates",
        "evaluated_candidates": "Evaluated",
        "github_fetched": "GitHub fetched",
        "avg_jd_score": "Avg JD score",
        "avg_alignment_score": "Avg alignment score",
        "job_status": "Job status",
        "no_evaluations": "No evaluations yet.",
        "candidate_detail": "Candidate detail",
        "rank": "Rank",
        "fit_band": "Fit band",
        "projects": "Projects",
        "experience": "Experience",
        "education": "Education",
        "sort_by": "Sort by",
        "sort_jd_score": "JD score",
        "sort_alignment_score": "Alignment score",
        "sort_name": "Name",
        "compare_candidates": "Compare candidates",
        "left_candidate": "Left candidate",
        "right_candidate": "Right candidate",
        "github_status_label": "GitHub status",
        "audit_filter": "Audit filter",
        "audit_search": "Audit search",
        "audit_limit": "Limit",
        "all": "All",
        "status_fetched": "Fetched",
        "status_failed": "Failed",
        "status_skipped": "Skipped",
        "status_not_requested": "Not requested",
        "status_top": "Top",
        "status_mid": "Mid",
        "status_review": "Review",
        "evaluation_summary": "Evaluation summary",
        "evidence": "Evidence",
        "candidate_profile": "Candidate profile",
        "structured_resume": "Structured resume JSON",
        "section_summaries": "Section summaries",
        "extracted_urls": "Extracted URLs",
        "github_verification": "GitHub verification",
        "github_repo_analysis": "GitHub repo analysis",
        "detected_frameworks": "Detected frameworks/signals",
        "sample_code_paths": "Sample code paths",
        "status": "Status",
        "token_mappings": "Token mappings",
        "no_token_mappings": "No token mappings recorded.",
        "original_resume": "Original resume text",
        "masked_resume": "Masked resume text",
        "audit_logs": "5. Audit Logs",
        "no_audit_logs": "No audit logs for this job yet.",
        "chat_title": "HireProof Chat",
        "chat_subtitle": "Run a hiring evaluation through conversation.",
        "chat_new_job": "+ Start new job",
        "chat_input_placeholder": "Type a message. /help for commands",
        "chat_intro": (
            "Hi! Let's start a HireProof evaluation.\n\n"
            "First, create a **job posting**. Send the job title on a single line, or paste the title on the first line and the JD body on the following lines.\n\n"
            "Example: `Backend Engineer Intern`"
        ),
        "chat_help_global": (
            "**Global commands**\n"
            "- `/restart` start a new job\n"
            "- `/help` show this help\n"
            "- `/results` view current ranking\n\n"
            "**Criteria stage**: `/confirm`, `/weight N <0-100>`, `/edit N <name>|<desc>|<weight>`, `/remove N`\n\n"
            "**Candidate stage**: `/name <name>`, `/github <url>`, `/portfolio <url>`. Upload a resume file from the panel above the input, or paste 200+ chars of resume text after setting `/name`.\n\n"
            "**Results stage**: `/detail N`, `/back` (return to candidate intake)"
        ),
        "chat_ask_jd_body": "Got it — title is `{title}`. Now paste the **JD body**.",
        "chat_jd_required": "Both title and JD body are required.",
        "chat_job_created": "Created job **{title}**. Suggested criteria:",
        "chat_no_criteria": "No criteria suggested.",
        "chat_criteria_help": (
            "If the criteria look good, send `/confirm`.\n"
            "Edit: `/weight N 30` · `/edit N name|desc|weight` · `/remove N`"
        ),
        "chat_criteria_confirmed_next": (
            "Criteria confirmed. Now add **candidates**.\n\n"
            "1. Upload a resume file from the panel above the input, type a name, and click `Start evaluation`, or\n"
            "2. Send `/name <name>` then paste 200+ chars of resume text.\n\n"
            "Send `/done` when finished to see the ranking."
        ),
        "chat_candidate_help": (
            "Add a candidate by:\n"
            "- Uploading a resume file in the panel above, entering a name, and clicking `Start evaluation`, or\n"
            "- Setting metadata with `/name <name>`, `/github <url>`, then pasting resume text (200+ chars)\n\n"
            "Next step: `/done` to view ranking"
        ),
        "chat_candidate_name_set": "Candidate name set to `{name}`.",
        "chat_candidate_github_set": "GitHub URL set to `{url}`.",
        "chat_candidate_portfolio_set": "Portfolio URL set to `{url}`.",
        "chat_candidate_added": "Candidate **{name}** ingested and evaluated.",
        "chat_next_candidate": "Add another candidate, or send `/done` to view the ranking.",
        "chat_results_help": "Commands: `/detail N` show detail · `/back` add another candidate · `/restart` new job",
        "chat_no_job": "No active job. Send `/restart` to start a new one.",
        "chat_upload_section": "Resume file upload",
        "chat_start_evaluation": "Start evaluation",
        "chat_upload_hint": "Upload a file, enter the candidate name, then click `Start evaluation`.",
    },
}


def get_translator(language: str):
    bundle = TRANSLATIONS.get(language, TRANSLATIONS["en"])

    def t(key: str) -> str:
        return bundle.get(key, key)

    return t
