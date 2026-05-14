"""질문 생성 모듈 — Solar(Upstage) + Chroma RAG, 직무별 페르소나·예시 분기"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
import uuid
from pathlib import Path

import chromadb
from openai import APIError, OpenAI

from models.types import Category, EvaluationResult, JobFamily, Question, SessionState

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 상수 / 환경설정
# ─────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL")
SOLAR_BASE_URL = os.getenv("SOLAR_BASE_URL")
SOLAR_API_KEY_ENV = "UPSTAGE_API_KEY"

_DEFAULT_CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
CHROMA_PATH = os.getenv("CHROMA_PATH", str(_DEFAULT_CHROMA_PATH))

RAG_TOP_K = 3
LLM_MAX_RETRIES = 2
LLM_TEMPERATURE = 0.5

_llm_client: OpenAI | None = None
_chroma_client: chromadb.ClientAPI | None = None


# ─────────────────────────────────────────────
# 카테고리: 일반(타입 호환용) + 직무별 세부 카테고리
# ─────────────────────────────────────────────
# Category 타입과 일치 (models/types.py 의 Literal 과 동일해야 함)
CATEGORIES: list[Category] = ["역량", "경험", "문제해결", "협업", "적합성"]

# 사용자에게 노출되거나 LLM 프롬프트에 들어가는 "표시용 라벨"
# 직무에 따라 다른 라벨로 묘사하되, 내부 Category 키는 5개 그대로 사용.
CATEGORY_LABELS_BY_FAMILY: dict[JobFamily, dict[Category, str]] = {
    "engineering": {
        "역량":    "기술 역량 (CS·언어·프레임워크)",
        "경험":    "프로젝트 경험",
        "문제해결": "기술 문제해결",
        "협업":    "협업 (코드리뷰·페어·갈등)",
        "적합성":  "직무·조직 적합성",
    },
    "design": {
        "역량":    "디자인 역량 (시각·인터랙션·시스템)",
        "경험":    "포트폴리오·프로젝트",
        "문제해결": "사용자 문제해결",
        "협업":    "PM·개발자와의 협업",
        "적합성":  "디자인 철학·조직 적합성",
    },
    "product": {
        "역량":    "제품 감각·전략",
        "경험":    "출시·운영 경험",
        "문제해결": "데이터 기반 의사결정",
        "협업":    "이해관계자 조율",
        "적합성":  "프로덕트 가치관·조직 적합성",
    },
    "marketing": {
        "역량":    "마케팅 역량 (캠페인·채널·분석)",
        "경험":    "캠페인·프로젝트 경험",
        "문제해결": "데이터 분석·실험",
        "협업":    "크리에이티브·세일즈 협업",
        "적합성":  "브랜드·조직 적합성",
    },
    "sales_bd": {
        "역량":    "세일즈 역량 (협상·클로징·파이프라인)",
        "경험":    "딜·고객 경험",
        "문제해결": "이의 처리·복잡 딜 풀이",
        "협업":    "사내 협업 (CS·프로덕트·파이낸스)",
        "적합성":  "고객관·조직 적합성",
    },
    "operations": {
        "역량":    "운영 역량 (프로세스·SLA·품질)",
        "경험":    "개선·자동화 경험",
        "문제해결": "이슈 대응·근본 원인 분석",
        "협업":    "유관 부서 협업",
        "적합성":  "운영 마인드·조직 적합성",
    },
    "hr_people": {
        "역량":    "인재·조직 역량",
        "경험":    "프로그램·제도 운영 경험",
        "문제해결": "갈등 조정·이슈 핸들링",
        "협업":    "리더·구성원 파트너십",
        "적합성":  "피플 철학·조직 적합성",
    },
    "finance": {
        "역량":    "재무·회계 역량",
        "경험":    "결산·분석·프로젝트 경험",
        "문제해결": "이슈·리스크 대응",
        "협업":    "사업·감사·외부 소통",
        "적합성":  "원칙·조직 적합성",
    },
    "general": {
        "역량":    "직무 역량",
        "경험":    "프로젝트·업무 경험",
        "문제해결": "문제해결",
        "협업":    "협업",
        "적합성":  "조직 적합성",
    },
}


# ─────────────────────────────────────────────
# 직무별 프롬프트 프로파일 (페르소나 + Few-shot)
# ─────────────────────────────────────────────
PROMPT_PROFILES: dict[JobFamily, dict[str, object]] = {
    "engineering": {
        "persona": "토스, 네이버, 카카오 같은 한국 주요 IT 기업에서 10년 이상 백엔드·프론트엔드·데이터·ML 면접을 진행한 시니어 엔지니어",
        "good_examples": [
            "최근에 가장 까다로웠던 기술적 결정 하나만 들려주세요. 어떤 트레이드오프가 있었나요?",
            "결제 시스템에서 동시성 문제 겪어본 적 있어요? 어떻게 푸셨는지 궁금합니다.",
            "MSA로 전환하면서 가장 후회한 결정이 있다면 뭔가요?",
            "p99 응답시간을 230ms까지 줄이셨다고 하셨는데, 어디가 병목이었어요?",
            "Kafka 도입은 누구 아이디어였어요? 도입 전후로 가장 크게 바뀐 점이 뭔가요?",
        ],
        "followup_examples": [
            "그 결정의 결정적인 이유 하나만 꼽는다면요?",
            "그건 어떻게 검증하셨어요?",
            "그때 측정한 수치를 좀 더 구체적으로 말씀해주실 수 있을까요?",
        ],
    },
    "design": {
        "persona": "10년 이상 UX·UI·프로덕트 디자인 면접을 진행한 시니어 디자인 리드",
        "good_examples": [
            "포트폴리오에서 가장 애착 가는 프로젝트 하나만 골라주세요. 왜 그게 특별한가요?",
            "사용자 인터뷰에서 예상과 완전히 다른 답이 나왔던 경험 있어요?",
            "디자인 시스템 만들 때 PM이랑 의견 갈렸던 적 있나요? 어떻게 정리하셨어요?",
            "최근에 디자인한 화면 중 가장 많이 갈아엎은 게 뭐예요?",
            "데이터가 A안을 가리키는데 본인 직감은 B안일 때 어떻게 결정하세요?",
        ],
        "followup_examples": [
            "그 결정의 핵심 근거 하나만 꼽는다면요?",
            "사용자 반응은 어떻게 측정하셨어요?",
            "지금 다시 디자인하신다면 어디부터 손대시겠어요?",
        ],
    },
    "product": {
        "persona": "10년 이상 PM·PO·서비스 기획 면접을 진행한 시니어 프로덕트 리드",
        "good_examples": [
            "최근에 출시한 기능 중 KPI 못 친 거 하나만 들려주세요. 회고는 어떻게 했어요?",
            "엔지니어가 '이건 기술적으로 못한다'고 했을 때 어떻게 풀어가세요?",
            "우선순위 정할 때 본인만의 기준이 있다면요?",
            "사용자 인터뷰와 데이터가 충돌할 때 어떻게 결정하세요?",
            "PRD 쓸 때 가장 신경 쓰는 부분이 뭐예요?",
        ],
        "followup_examples": [
            "그때 가장 중요했던 지표가 뭐였어요?",
            "그 결정에 반대한 사람은 누구였고, 어떻게 설득했어요?",
            "지금 다시 한다면 어떤 가설을 먼저 검증하시겠어요?",
        ],
    },
    "marketing": {
        "persona": "10년 이상 퍼포먼스·콘텐츠·브랜드 마케팅 면접을 진행한 시니어 마케팅 리드",
        "good_examples": [
            "최근에 진행한 캠페인 중 ROAS가 가장 안 좋았던 거 하나 들려주세요. 뭐가 문제였어요?",
            "데이터가 A를 가리키는데 직감은 B라고 할 때, 어떻게 결정하세요?",
            "콘텐츠 톤앤매너를 두고 브랜드팀이랑 부딪힌 적 있어요?",
            "예산 절반으로 같은 목표를 받았다면 뭘 먼저 줄이시겠어요?",
            "최근에 본 마케팅 사례 중 가장 인상 깊은 건 뭐예요? 왜 그렇게 보세요?",
        ],
        "followup_examples": [
            "그때 측정한 핵심 지표가 정확히 뭐였어요?",
            "왜 그 채널을 선택하셨어요?",
            "결과를 누구한테 어떻게 보고하셨어요?",
        ],
    },
    "sales_bd": {
        "persona": "10년 이상 영업·BD·CSM 면접을 진행한 세일즈 리드",
        "good_examples": [
            "최근에 클로징 못 한 딜 하나 떠올려주세요. 무엇이 결정적이었어요?",
            "고객이 가격 깎아달라고 강하게 요구할 때 본인의 협상 흐름이 궁금합니다.",
            "쿼터 못 채울 것 같은 분기, 마지막 2주에 뭘 하세요?",
            "가장 어려웠던 고객 한 명 떠올려주세요. 어떻게 관계를 풀어가셨어요?",
            "프로덕트팀에 강하게 피드백 줬던 경험이 있다면요?",
        ],
        "followup_examples": [
            "그 협상에서 본인이 가장 양보한 게 뭐예요?",
            "그 결정으로 잃은 건 뭐고 얻은 건 뭐였어요?",
            "지금 다시 한다면 어디서 다르게 하시겠어요?",
        ],
    },
    "operations": {
        "persona": "10년 이상 운영·CS·백오피스 면접을 진행한 운영 리드",
        "good_examples": [
            "최근에 가장 크게 개선한 프로세스 하나 들려주세요. 어디가 병목이었어요?",
            "반복되는 이슈를 근본적으로 해결한 경험이 있다면요?",
            "긴급 장애 상황에서 본인의 대응 순서가 궁금해요.",
            "사람이 줄어든 상태에서 같은 SLA를 유지해야 한다면 뭘 먼저 자동화하시겠어요?",
            "유관 부서가 협조 안 할 때 어떻게 푸세요?",
        ],
        "followup_examples": [
            "그 개선의 효과를 어떤 숫자로 측정했어요?",
            "그때 가장 어려웠던 의사결정이 뭐였어요?",
            "지금 같은 상황이 다시 오면 어떻게 다르게 하시겠어요?",
        ],
    },
    "hr_people": {
        "persona": "10년 이상 HR·People·리쿠르팅 면접을 진행한 시니어 피플 리드",
        "good_examples": [
            "최근에 도입한 제도 중 가장 자랑스러운 거 하나 들려주세요. 어떻게 측정하셨어요?",
            "구성원 갈등을 중재했던 경험이 있다면요?",
            "리더가 잘못된 결정을 내릴 때 어떻게 피드백 주세요?",
            "조직문화를 데이터로 본다면 어떤 지표를 보세요?",
            "채용에서 '이건 절대 양보 못 한다'는 본인의 기준이 있나요?",
        ],
        "followup_examples": [
            "그 제도가 정말 효과 있었는지는 어떻게 확인하셨어요?",
            "반대 의견은 누구였고 어떻게 설득했어요?",
            "지금 다시 한다면 어디부터 다르게 하시겠어요?",
        ],
    },
    "finance": {
        "persona": "10년 이상 재무·회계·FP&A 면접을 진행한 시니어 파이낸스 리드",
        "good_examples": [
            "결산 중에 큰 이슈를 발견했던 경험이 있다면요? 어떻게 처리하셨어요?",
            "사업팀이 본인 분석을 안 받아들였을 때 어떻게 푸셨어요?",
            "본인이 만들었던 분석 모델 중 가장 자랑스러운 거 하나 들려주세요.",
            "감사 대응 중 가장 까다로웠던 이슈가 뭐였어요?",
            "현금 흐름이 빠듯할 때 가장 먼저 보는 지표는 뭐예요?",
        ],
        "followup_examples": [
            "그 판단의 근거가 된 핵심 숫자가 뭐였어요?",
            "이해관계자 누구를 어떻게 설득했어요?",
            "리스크는 어떻게 헤지하셨어요?",
        ],
    },
    "general": {
        "persona": "다양한 직무에서 10년 이상 면접을 진행한 시니어 매니저",
        "good_examples": [
            "최근 1년 안에 가장 자랑스러웠던 성과 하나만 들려주세요.",
            "본인의 한계를 가장 크게 느꼈던 순간이 언제예요?",
            "동료와 의견이 갈렸을 때 본인이 결국 양보했던 경험이 있다면요?",
            "지원하신 직무에서 가장 자신 없는 영역이 뭐예요? 왜 그렇게 보세요?",
            "최근에 가장 크게 배운 점 하나만 골라주세요.",
        ],
        "followup_examples": [
            "그 결정의 결정적인 이유 하나만 꼽는다면요?",
            "그땐 어떻게 검증하셨어요?",
            "지금 다시 한다면 어떻게 다르게 하시겠어요?",
        ],
    },
}


# ─────────────────────────────────────────────
# 클라이언트 (lazy init)
# ─────────────────────────────────────────────
def _get_llm() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv(SOLAR_API_KEY_ENV)
        if not api_key:
            raise RuntimeError(f"환경변수 {SOLAR_API_KEY_ENV} 가 설정되지 않았습니다.")
        _llm_client = OpenAI(api_key=api_key, base_url=SOLAR_BASE_URL)
    return _llm_client


def _get_chroma() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


# ─────────────────────────────────────────────
# 카테고리 / 난이도 결정
# ─────────────────────────────────────────────
def _select_category(state: SessionState) -> Category:
    asked = [q.category for q, _ in state.history if not q.is_followup]
    counts = {c: asked.count(c) for c in CATEGORIES}
    min_count = min(counts.values())
    candidates = [c for c, n in counts.items() if n == min_count]
    return random.choice(candidates)


def _calibrate_difficulty(state: SessionState) -> int:
    main_results = [r for q, r in state.history[-5:] if not q.is_followup]
    if not main_results:
        return 3
    avg = sum(
        (r.star_score + r.specificity_score + r.relevance_score) / 3
        for r in main_results
    ) / len(main_results)
    if avg >= 4.5:
        return 5
    if avg >= 4.0:
        return 4
    if avg <= 1.5:
        return 1
    if avg <= 2.0:
        return 2
    return 3


# ─────────────────────────────────────────────
# RAG 검색
# ─────────────────────────────────────────────
def _retrieve_resume(state: SessionState, query: str, k: int = RAG_TOP_K) -> str:
    if not query.strip():
        return "(검색 쿼리 비어 있음)"
    try:
        col = _get_chroma().get_collection(state.context.chroma_collection_name)
        res = col.query(query_texts=[query], n_results=k)
        docs = (res.get("documents") or [[]])[0]
        return "\n\n---\n\n".join(docs) if docs else "(이력서 검색 결과 없음)"
    except Exception as e:
        logger.warning("이력서 RAG 검색 실패: %s", e)
        return "(이력서 컨텍스트 검색 실패)"


# ─────────────────────────────────────────────
# 프롬프트 빌더 헬퍼
# ─────────────────────────────────────────────
def _followup_chain(state: SessionState) -> list[tuple[Question, EvaluationResult]]:
    chain: list[tuple[Question, EvaluationResult]] = []
    for q, r in reversed(state.history):
        chain.append((q, r))
        if not q.is_followup:
            break
    return list(reversed(chain))


def _asked_main_questions_text(state: SessionState) -> str:
    items = [f"- [{q.category}] {q.text}" for q, _ in state.history if not q.is_followup]
    return "\n".join(items) if items else "(없음)"


def _company_section(state: SessionState) -> str:
    cp = state.context.company_profile
    if cp is None:
        return "## 지원 기업 정보\n(미수집)"
    return (
        "## 지원 기업 정보\n"
        f"- 기업명: {cp.name}\n"
        f"- 기술 스택: {', '.join(cp.tech_stack) if cp.tech_stack else '미상'}\n"
        f"- 문화: {cp.culture or '미상'}\n"
        f"- 최근 동향: {cp.recent_news or '미상'}"
    )


# ─────────────────────────────────────────────
# 시스템 프롬프트 동적 생성 (직무별)
# ─────────────────────────────────────────────
def _build_system_prompt(family: JobFamily) -> str:
    profile = PROMPT_PROFILES.get(family, PROMPT_PROFILES["general"])
    persona = profile["persona"]
    good_examples = "\n".join(f"- {ex}" for ex in profile["good_examples"])  # type: ignore[arg-type]

    return f"""당신은 {persona}입니다. 직무기술서(JD)에 명시된 직군의 기준으로 지원자를 평가하며, 학원 강사처럼 묻지 않고 동료에게 커피 마시며 묻듯 자연스럽게 대화합니다. 다만 답변이 모호하면 끈질기게 파고드는 스타일입니다.

## 좋은 면접 질문의 특징
- 구어체. 실제로 면접관이 입으로 말하는 톤.
- 짧고 명확. 한 호흡으로 묻고 끝.
- 조건·전제 나열 금지. "X일 때 Y에 대해 A, B, C를 설명하시오" 같은 시험 문제 형식 금지.
- 답변자가 자신의 경험으로 풀어낼 여지를 줄 것.
- 이력서·포트폴리오의 구체적인 단서(프로젝트명·수치·역할명)를 자연스럽게 인용.

## 좋은 예시 (이런 톤으로)
{good_examples}

## 나쁜 예시 (이렇게 하지 말 것)
- "귀하의 이력서에 기재된 OO 프로젝트와 관련하여, 의사결정 과정에서 고려하신 트레이드오프 요소들과 이에 대한 검증 방법론을 구체적으로 설명해 주시기 바랍니다." → 시험 문제 같음, 격식 과잉.
- "다음 세 가지 관점에서 답변해 주세요: (1) 도전, (2) 협업, (3) 배운 점." → 답변 형식까지 강요함, 자연스럽지 않음.
- "OO의 정의를 말하고, 장단점 3가지씩 나열해 주세요." → 강의 문제 같음, 단순 지식 암기 테스트.

## 출력 형식
응답은 반드시 다음 JSON 한 줄만 출력: {{"text": "질문 본문"}}
마크다운 코드펜스, 설명, 인사말 등 다른 텍스트 일절 포함 금지."""


def _build_followup_examples(family: JobFamily) -> str:
    profile = PROMPT_PROFILES.get(family, PROMPT_PROFILES["general"])
    return "\n".join(f"- {ex}" for ex in profile["followup_examples"])  # type: ignore[arg-type]


def _category_label(state: SessionState, category: Category) -> str:
    """직무에 맞는 카테고리 라벨 (없으면 일반 라벨)."""
    family = state.context.job_family
    labels = CATEGORY_LABELS_BY_FAMILY.get(family, CATEGORY_LABELS_BY_FAMILY["general"])
    return labels.get(category, category)


# ─────────────────────────────────────────────
# User 프롬프트 빌더
# ─────────────────────────────────────────────
def _main_prompt(state: SessionState, category: Category, difficulty: int) -> str:
    rag_query = f"{category} {state.context.job_description[:200]}"
    label = _category_label(state, category)

    return f"""다음 조건에 맞는 면접 메인 질문 1개를 생성하세요.

## 직무 설명
{state.context.job_description}

{_company_section(state)}

## 지원자 이력서/포트폴리오 발췌
{_retrieve_resume(state, rag_query)}

## 이미 던진 메인 질문 (중복 금지)
{_asked_main_questions_text(state)}

## 생성 조건
- 카테고리: {category} ({label})
- 난이도: {difficulty}/5  (1: 워밍업·기본기 / 3: 표준 경력 / 5: 시니어급 깊이)
- 이력서·포트폴리오의 구체적인 단서(프로젝트·수치·역할)를 자연스럽게 인용
- 시스템 프롬프트의 좋은 예시 톤을 따를 것
- 한국어 존댓말, **1~2문장**. 조건 나열·격식체·시험 문제 형식 금지.

다음 JSON만 출력:
{{"text": "질문 본문"}}"""


def _followup_prompt(state: SessionState) -> str:
    chain = _followup_chain(state)
    chain_text = "\n\n".join(
        f"### {'메인' if not q.is_followup else f'꼬리 (depth {i})'}\n"
        f"Q: {q.text}\nA: {r.user_answer}\n"
        f"약점: {', '.join(r.weakness_tags) or '(없음)'}"
        for i, (q, r) in enumerate(chain)
    )
    last_q, last_r = chain[-1]
    weak = ", ".join(last_r.weakness_tags) or "(답변의 모호점·미검증 주장 정조준)"
    rag_query = f"{last_q.text} {' '.join(last_r.weakness_tags)}".strip()
    fu_examples = _build_followup_examples(state.context.job_family)

    return f"""아래 흐름의 마지막 답변을 깊이 검증하는 꼬리질문 1개를 생성하세요.

## 좋은 꼬리질문 예시 (이 톤으로)
{fu_examples}

## 직무 설명
{state.context.job_description}

## 이력서/포트폴리오 발췌
{_retrieve_resume(state, rag_query)}

## 질문 체인
{chain_text}

## 정조준할 약점
{weak}

## 생성 조건
- 직전 답변의 구체성 결여, 근거 부족, 모순, 책임 불명확 중 하나를 정확히 찌를 것
- 위 좋은 예시처럼 짧고 자연스러운 구어체
- 한국어 존댓말, **1문장 권장 (최대 2문장)**

다음 JSON만 출력:
{{"text": "꼬리질문 본문"}}"""


# ─────────────────────────────────────────────
# LLM 호출 / JSON 파싱
# ─────────────────────────────────────────────
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_text_from_response(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_OBJ_RE.search(cleaned)
        if not match:
            raise ValueError(f"JSON 객체를 찾을 수 없음: {raw[:200]}")
        data = json.loads(match.group(0))
    text = (data.get("text") or "").strip()
    if not text:
        raise ValueError(f"빈 question text: {raw[:200]}")
    return text


def _is_permanent_api_error(err: APIError) -> bool:
    """4xx 클라이언트 에러는 재시도해도 의미 없음 (단, 429 rate limit 제외)."""
    status = getattr(err, "status_code", None)
    if status is None:
        return False
    if status == 429:
        return False
    return 400 <= status < 500


def _call_llm(user_prompt: str, family: JobFamily) -> str:
    """LLM 호출 + JSON 파싱. 일시적 오류·파싱 실패 시 재시도."""
    system_prompt = _build_system_prompt(family)
    last_err: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            resp = _get_llm().chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or ""
            return _extract_text_from_response(raw)

        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            logger.warning(
                "LLM 응답 파싱 실패 (시도 %d/%d): %s",
                attempt + 1, LLM_MAX_RETRIES + 1, e,
            )
        except APIError as e:
            last_err = e
            if _is_permanent_api_error(e):
                logger.error(
                    "영구 API 에러로 즉시 중단 (status=%s): %s",
                    getattr(e, "status_code", "?"), e,
                )
                break
            logger.warning(
                "LLM API 오류 (시도 %d/%d): %s",
                attempt + 1, LLM_MAX_RETRIES + 1, e,
            )
            time.sleep(0.5 * (attempt + 1))

    assert last_err is not None
    raise RuntimeError(f"LLM 호출 실패: {last_err}") from last_err


# ─────────────────────────────────────────────
# 엔트리 포인트
# ─────────────────────────────────────────────
def generate_question(state: SessionState, is_followup: bool) -> Question:
    family = state.context.job_family

    if is_followup and state.history:
        last_q, _ = state.history[-1]
        text = _call_llm(_followup_prompt(state), family)
        return Question(
            id=str(uuid.uuid4()),
            text=text,
            category=last_q.category,
            difficulty=min(5, last_q.difficulty + 1),
            is_followup=True,
            parent_id=last_q.id,
        )

    category = _select_category(state)
    difficulty = _calibrate_difficulty(state)
    text = _call_llm(_main_prompt(state, category, difficulty), family)
    return Question(
        id=str(uuid.uuid4()),
        text=text,
        category=category,
        difficulty=difficulty,
        is_followup=False,
        parent_id=None,
    )