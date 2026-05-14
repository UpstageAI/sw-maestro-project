from __future__ import annotations

from ..llm import llm

SYSTEM = (
    "당신은 한국 주식시장 전문 애널리스트입니다. 주어진 시세 컨텍스트만 사용해 "
    "정형화된 투자 리포트를 작성하세요. 사실에 기반하고, 추측은 명시적으로 표시하세요. "
    "매수/매도 추천은 절대 하지 마세요. 모든 응답은 한국어 마크다운으로 작성하세요."
)

TEMPLATE = """\
다음은 분석 대상 종목의 시세 컨텍스트입니다.

[종목] {symbol}
[수집된 컨텍스트]
{context}

위 컨텍스트만 사용해 다음 4개 섹션의 투자 리포트를 마크다운으로 작성하세요.
컨텍스트에서 직접 확인할 수 없는 사실은 추측하지 말고 "데이터 부족"이라 표기하세요.

## 핵심 분석 요약
## 시세 추이 해석
## 리스크 요인
## 종합 의견 (관찰 포인트만, 매수/매도 추천 금지)
"""


def write_report(symbol: str, context: str) -> str:
    if not context.strip():
        return f"## 데이터 없음\n\n{symbol} 종목의 컨텍스트가 비어 있어 리포트를 생성할 수 없습니다."
    user = TEMPLATE.format(symbol=symbol, context=context)
    return llm.generate(SYSTEM, user)
