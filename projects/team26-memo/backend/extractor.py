"""오프라인 휴리스틱 추출기.

LLM API 키가 없거나 호출이 실패한 경우에도 동작하는 한국어 회의록
분석기. 데모/테스트/개발 환경에서 결정론적인 결과를 보장한다.

다음 정보를 추출한다:
  - 한국어 인명 (2~4자, 흔한 성씨 기반)
  - 날짜 (YYYY-MM-DD, M월 D일, 다음주, 내일, 모레, 이번주 X요일 등)
  - 액션 문장 (할당/마감/요청 패턴)
  - 안건 비교 (안건 vs 녹취록 키워드 교집합)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# 정규식 / 사전
# ---------------------------------------------------------------------------

# 한국어 흔한 성씨 (상위 약 60개) - 100% 정확하지 않지만 휴리스틱 용도로 충분
_KOREAN_SURNAMES = (
    "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노"
    "정하곽성차주우구민유진지엄채원천방공현함변염양변여추도소석선설"
    "마길주연방위표명기반왕금옥육인맹제모탁국어은편구용"
)

# 한국 이름: 성씨(1자) + 이름(1~3자), 한글만
_NAME_RE = re.compile(rf"[{_KOREAN_SURNAMES}][가-힣]{{1,2}}")

# Honorific 패턴: "X 님이", "X님께서", "X 씨가" 등 — 담당자 신호로 가장 확실
_OWNER_HONORIFIC_RE = re.compile(
    rf"([{_KOREAN_SURNAMES}][가-힣]{{1,2}})\s*(?:님(?:이|께서|에게|은|이가)?|씨(?:가|께서)?)"
)

# 조사 + 동사 어절 패턴: "이름이/가 ... 하겠습니다/주세요/마무리/정리/작성/공유"
# 동사 어미를 같이 요구해 일반 명사+조사를 거른다.
_OWNER_PARTICLE_RE = re.compile(
    rf"([{_KOREAN_SURNAMES}][가-힣]{{1,2}})\s*(?:께서|이가|이|가|은|는)\s+"
    r"(?:[^\s]+\s+){0,6}?"
    r"(?:정리|공유|작성|검토|확인|발표|준비|제출|전달|마무리|마감|완성|조사|분석|보고|리뷰|기획|설계|구현|테스트|배포|회신|답변|확정|결정|하겠|할게|할께|해주|드리|드릴)"
)

# 인명 정규식이 잘못 잡는 일반 명사들 (false positive 방지)
_NAME_BLOCKLIST = {
    # 일반 명사
    "신규", "전체", "전혀", "전부", "전반", "전달", "최근", "최초", "최종",
    "조금", "조직", "조사", "오늘", "오후", "오전", "내용", "내일", "내년",
    "마지막", "마감", "마무리", "마케팅", "고객", "고려", "공유", "공지",
    "방안", "방향", "방법", "방식", "방문", "방금",
    "구체", "구현", "구성", "구글", "구분", "구입", "구사항",
    "정리", "정확", "정도", "정말", "정상", "정의", "정기",
    "검토", "검색", "검증", "결정", "결과", "결제", "결국",
    "기능", "기획", "기준", "기존", "기간", "기술", "기대", "기쁨",
    "한정", "한국", "한국어", "한번", "한참", "한쪽",
    "강의", "강조", "강제", "강력",
    "주요", "주간", "주제", "주로", "주의", "주말", "주차",
    "회의", "회사", "회신", "회수",
    "차주", "차후", "차이", "차원",
    "임시", "임원", "임팩트",
    "박스", "박람",
    "성능", "성장", "성공", "성과", "성격",
    "양쪽", "양측", "양해",
    "백엔드", "백업",
    "민감", "민원",
    "원래", "원래대로", "원본", "원격",
    "도구", "도움", "도입", "도착", "도전",
    "남기", "남은",
    "송신", "송출",
    "심리", "심층",
    "오류", "오픈", "오케이",
    "임의", "임의로",
    "황당",
    "현재", "현장", "현황", "현실",
    # 회의에서 자주 등장하는 명사
    "문서", "문제", "문의",
    "제안", "제출", "제품", "제휴", "제공", "제외",
    "보고", "보안", "보장",
    "예산", "예상", "예시", "예약", "예정",
    "초안", "초기", "초반",
    "분석", "분기", "분야", "분류",
    "전략", "전송", "전환", "전화",
    "계획", "계약", "계정", "계속",
    "프로", "프론", "프레",
    "안건", "안내",
    "개발", "개선", "개인", "개념", "개시",
    "사용", "사항", "사례", "사실", "사이", "사전", "사후",
    "광고", "광역",
    "내부", "외부",
    "이번", "이전", "이후", "이외", "이슈",
    "우선", "우리",
    "제안", "제외", "제거", "제기",
    "노력", "노출",
    "수정", "수행", "수신", "수용", "수치",
    "확장", "확인", "확정", "확보",
    "진행", "진단",
    "논의", "논리",
    "적용", "적정",
    "활용", "활동",
    "공식", "공지", "공간", "공통", "공급",
    "행사", "행동",
    "입력", "입니다",
    "출력", "출시", "출장",
    "향후", "향상",
    "안전", "안정",
    "동의", "동안", "동시",
    "실행", "실제", "실시", "실수",
}

# 날짜 표현
_DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b"),  # 2026-05-10
    re.compile(r"\b(20\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일"),    # 2026년 5월 10일
    re.compile(r"(?<!\d)(\d{1,2})월\s*(\d{1,2})일"),              # 5월 10일
]

_RELATIVE_DATE_KEYWORDS = {
    "오늘": 0,
    "내일": 1,
    "모레": 2,
    "글피": 3,
    "다음주": 7,
    "다다음주": 14,
    "이번주말": 5,
    "다음달": 30,
}

_WEEKDAYS = {
    "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3,
    "금요일": 4, "토요일": 5, "일요일": 6,
}

# 액션 동사/패턴 - 누가 무엇을 해야 한다는 신호
_ACTION_KEYWORDS = (
    "주세요", "부탁드립니다", "부탁드려요", "부탁해요", "해주세요",
    "하기로", "하겠습니다", "할게요", "할께요", "맡아", "담당",
    "정리", "공유", "작성", "검토", "확인", "발표", "준비",
    "제출", "전달", "마무리", "마감", "완성", "조사", "분석",
    "보고", "리뷰", "기획", "설계", "구현", "테스트", "배포",
    "회신", "답변", "확정", "결정",
)

# 화자 라인: "[10:00] 이름:" 또는 "이름:" 형태
_SPEAKER_LINE_RE = re.compile(
    r"^(?:\[[^\]]+\]\s*)?([가-힣A-Za-z][가-힣A-Za-z0-9_ ]{0,20})\s*[:：]\s*(.+)$"
)


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass
class ExtractedAction:
    who: str
    when: str
    what: str


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def _today() -> date:
    """테스트에서 monkeypatch 가 가능하도록 함수로 분리."""
    return date.today()


def _split_sentences(text: str) -> List[str]:
    """녹취록을 문장 단위로 분리. 화자 라인을 우선 보존한다."""
    if not text:
        return []
    # 화자 라인 분리
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sentences: List[str] = []
    for line in raw_lines:
        m = _SPEAKER_LINE_RE.match(line)
        body = m.group(2) if m else line
        # 마침표/물음표/느낌표 + 공백 기준
        for chunk in re.split(r"(?<=[.!?。])\s+", body):
            chunk = chunk.strip()
            if not chunk:
                continue
            if m:
                sentences.append(f"{m.group(1).strip()}: {chunk}")
            else:
                sentences.append(chunk)
    return sentences


def _extract_speaker(sentence: str) -> Tuple[Optional[str], str]:
    """'이영희: ...' 형태에서 (화자, 본문) 분리."""
    m = re.match(r"^([가-힣A-Za-z][가-힣A-Za-z0-9_ ]{0,20})\s*[:：]\s*(.+)$", sentence)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, sentence


def parse_date(text: str, base: Optional[date] = None) -> Optional[str]:
    """문장 안에서 가장 그럴듯한 날짜를 찾아 YYYY-MM-DD 로 반환."""
    if base is None:
        base = _today()

    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        groups = m.groups()
        try:
            if len(groups) == 3:
                y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
            else:
                y, mo, d = base.year, int(groups[0]), int(groups[1])
            parsed = date(y, mo, d)
            # 과거이고 연도가 추정이면 다음 해로
            if len(groups) == 2 and parsed < base:
                parsed = date(y + 1, mo, d)
            return parsed.isoformat()
        except (ValueError, TypeError):
            continue

    # 상대 키워드
    for kw, delta in _RELATIVE_DATE_KEYWORDS.items():
        if kw in text:
            return (base + timedelta(days=delta)).isoformat()

    # 다음주 X요일
    for wd_name, wd_num in _WEEKDAYS.items():
        if wd_name in text:
            today_wd = base.weekday()
            ahead = (wd_num - today_wd) % 7
            if ahead == 0:
                ahead = 7
            if "다음주" in text or "차주" in text:
                ahead += 7 - ((wd_num - today_wd) % 7) if ahead < 7 else ahead
            return (base + timedelta(days=ahead)).isoformat()

    return None


def extract_persons(text: str) -> List[str]:
    """문장에서 한국 인명 후보들을 추출 (등장 순서, 중복 제거).

    NAME_BLOCKLIST 로 일반 명사를 걸러낸다.
    """
    found: List[str] = []
    seen = set()
    for m in _NAME_RE.finditer(text):
        name = m.group(0)
        if not (2 <= len(name) <= 4):
            continue
        if name in _NAME_BLOCKLIST:
            continue
        if name in seen:
            continue
        seen.add(name)
        found.append(name)
    return found


def is_action_sentence(sentence: str) -> bool:
    return any(kw in sentence for kw in _ACTION_KEYWORDS)


def _guess_owner(sentence: str, speaker: Optional[str]) -> str:
    """문장에서 담당자 추정.

    우선순위:
      1) Honorific 패턴 ('X 님이', 'X 씨가') 의 첫 매칭
      2) 문장에 등장한 인명 중 화자가 아닌 첫 번째 사람
      3) 화자 자신 (본인이 하기로 한 경우)
    """
    # 1) honorific 가 가장 확실한 신호
    m = _OWNER_HONORIFIC_RE.search(sentence)
    if m:
        candidate = m.group(1)
        if candidate not in _NAME_BLOCKLIST:
            return candidate

    # 2) 조사 + 동사 어절 패턴 ('김민수가 ... 마무리하겠습니다')
    m = _OWNER_PARTICLE_RE.search(sentence)
    if m:
        candidate = m.group(1)
        if candidate not in _NAME_BLOCKLIST:
            return candidate

    persons = extract_persons(sentence)
    others = [p for p in persons if p != speaker]
    if others:
        return others[0]
    if persons:
        return persons[0]
    if speaker and re.fullmatch(r"[가-힣]{2,4}", speaker):
        return speaker
    return ""


def _clean_action_what(sentence: str) -> str:
    """액션 본문 정리: 화자 prefix 제거, 너무 긴 경우 핵심부만 유지."""
    _, body = _extract_speaker(sentence)
    body = body.strip().rstrip(".")
    # 너무 긴 경우 마지막 클로즈에서 컷
    if len(body) > 120:
        body = body[:117] + "…"
    return body


# ---------------------------------------------------------------------------
# 메인 추출 함수
# ---------------------------------------------------------------------------


def extract_action_items(transcript: str, base_date: Optional[date] = None) -> List[ExtractedAction]:
    """녹취록에서 액션 아이템 후보들을 추출."""
    sentences = _split_sentences(transcript)
    items: List[ExtractedAction] = []
    seen_what = set()

    for sent in sentences:
        if not is_action_sentence(sent):
            continue
        speaker, body = _extract_speaker(sent)
        what = _clean_action_what(sent)
        # 중복 방지 (동일 본문)
        what_key = re.sub(r"\s+", "", what)[:60]
        if what_key in seen_what:
            continue
        seen_what.add(what_key)

        when = parse_date(body, base=base_date) or ""
        who = _guess_owner(body, speaker)
        items.append(ExtractedAction(who=who, when=when, what=what))

    return items


def extract_summary(transcript: str, max_chars: int = 280) -> str:
    """녹취록 요약 (휴리스틱).

    화자/타임스탬프를 제거한 본문에서 가장 정보량 많은 앞쪽 문장들을
    선별해 요약문을 만든다.
    """
    sentences = _split_sentences(transcript)
    if not sentences:
        return ""

    # 너무 짧은 인사/끝맺음 문장 제거
    candidates: List[str] = []
    for s in sentences:
        _, body = _extract_speaker(s)
        body = body.strip()
        if len(body) < 10:
            continue
        if any(g in body for g in ("안녕하세요", "오늘 회의 시작", "회의 마치", "수고하셨습니다")):
            continue
        candidates.append(body)

    if not candidates:
        candidates = [body for _, body in (_extract_speaker(s) for s in sentences)]

    # 액션 문장 우선, 그 외 정보 문장 보조
    action_first = [c for c in candidates if is_action_sentence(c)]
    others = [c for c in candidates if c not in action_first]

    summary_parts: List[str] = []
    used = 0
    for pool in (others, action_first):
        for c in pool:
            if used + len(c) > max_chars:
                continue
            summary_parts.append(c)
            used += len(c) + 2
            if used >= max_chars:
                break
        if used >= max_chars:
            break

    if not summary_parts:
        return candidates[0][:max_chars]

    return " ".join(summary_parts).strip()


def split_agenda_items(agenda: str) -> List[str]:
    """안건 텍스트를 항목 리스트로 분리."""
    if not agenda or not agenda.strip():
        return []
    items: List[str] = []
    for line in re.split(r"[\n;]+", agenda):
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^\s*(?:\d+[.)]|[-•*])\s*", "", line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _keywords_of(text: str) -> set[str]:
    """간단한 키워드 추출: 2자 이상 한글/영문 토큰."""
    tokens = re.findall(r"[가-힣A-Za-z]{2,}", text or "")
    # 너무 일반적인 단어 제거
    stop = {"논의", "회의", "관련", "내용", "방안", "검토", "공유", "확인", "진행"}
    return {t for t in tokens if t not in stop}


def find_missed_agenda(agenda: str, transcript: str, threshold: float = 0.25) -> List[str]:
    """안건 항목 중 녹취록과 키워드 겹침이 적은 것을 '누락'으로 분류."""
    items = split_agenda_items(agenda)
    if not items:
        return []
    transcript_kw = _keywords_of(transcript)
    if not transcript_kw:
        return items

    missed: List[str] = []
    for item in items:
        item_kw = _keywords_of(item)
        if not item_kw:
            continue
        overlap = len(item_kw & transcript_kw) / max(len(item_kw), 1)
        if overlap < threshold:
            missed.append(item)
    return missed


def suggest_next_agenda(
    agenda: str, transcript: str, missed: List[str], actions: List[ExtractedAction]
) -> List[str]:
    """다음 회의 안건 제안.

    - 누락된 안건은 그대로 다음 회의로 이월
    - 액션 아이템 중 마감일이 임박한 것의 진행 점검
    - '다음 회의', '차주', '추후 논의' 등 명시된 항목
    """
    suggestions: List[str] = []
    seen = set()

    def _add(item: str):
        key = re.sub(r"\s+", "", item)[:50]
        if key and key not in seen:
            seen.add(key)
            suggestions.append(item)

    # 누락 안건 이월
    for m in missed:
        _add(f"{m} (이월)")

    # 명시적 다음 회의 키워드 문장
    for sent in _split_sentences(transcript):
        _, body = _extract_speaker(sent)
        if any(k in body for k in ("다음 회의", "차주 회의", "추후 논의", "다음에 논의", "다음번 회의")):
            cleaned = _clean_action_what(sent)
            _add(cleaned)

    # 액션 아이템 진행 점검
    for a in actions[:3]:
        if a.what:
            short = a.what[:40]
            _add(f"{short} 진행 상황 점검")

    return suggestions[:5]
