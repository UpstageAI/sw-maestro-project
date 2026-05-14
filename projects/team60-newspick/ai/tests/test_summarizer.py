import json

from newspick_ai.graph.summarizer import Summarizer


class FakeChatClient:
    def __init__(self):
        self.prompts = []

    def complete(self, messages):
        self.prompts.append(messages[-1]["content"])
        return """{
          "summary": [
            "AI 뉴스 자동화가 업무 흐름을 바꾸고 있어요.",
            "언론 제작 과정에서 AI 활용이 확대되고 있어요.",
            "관련 서비스 경쟁도 빨라지고 있어요."
          ],
          "keywords": ["AI", "뉴스", "자동화"],
          "importance": "AI가 기사 작성과 배포 업무에 들어오면 언론사의 제작 방식과 기자 역할이 달라질 수 있어요.",
          "context": "언론사는 기사 추천, 요약, 초안 작성에 AI를 활용하는 실험을 이어가고 있어요.",
          "importanceScore": 8
        }"""


class SequenceChatClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def complete(self, messages):
        self.prompts.append(messages[-1]["content"])
        return self.responses.pop(0)


class FailingChatClient:
    def complete(self, messages):
        raise RuntimeError("too_many_requests")


def test_summarizer_writes_three_sentence_summary():
    fake = FakeChatClient()
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "content": "첫 문단입니다.\n\n둘째 문단입니다.\n\n셋째 문단입니다.",
            }
        ],
        "events": [],
    }

    output = Summarizer(chat_client=fake).run(state)

    article = output["articles"][0]
    assert article["summary"] == [
        "AI 뉴스 자동화가 업무 흐름을 바꾸고 있어요.",
        "언론 제작 과정에서 AI 활용이 확대되고 있어요.",
        "관련 서비스 경쟁도 빨라지고 있어요.",
    ]
    assert article["keywords"] == ["AI", "뉴스", "자동화"]
    assert article["importance"] == "AI가 기사 작성과 배포 업무에 들어오면 언론사의 제작 방식과 기자 역할이 달라질 수 있어요."
    assert article["context"] == "언론사는 기사 추천, 요약, 초안 작성에 AI를 활용하는 실험을 이어가고 있어요."
    assert article["importanceScore"] == 8
    assert "AI 뉴스" in fake.prompts[0]
    assert "첫 문단입니다." in fake.prompts[0]
    assert "summary는 사실 중심 한국어 해요체 문장 정확히 3개 배열" in fake.prompts[0]
    assert "반드시 '요.'로 끝내시오" in fake.prompts[0]
    assert "'~하고 있어요', '~되고 있어요', '~보이고 있어요'" in fake.prompts[0]
    assert "홈 기사 카드에서 3줄 안팎" in fake.prompts[0]
    assert "무엇에 어떤 변화가 생기는지" in fake.prompts[0]
    assert "형식적 표현을 쓰지 마시오" in fake.prompts[0]
    assert "친화적인 해요체 1~2문장" in fake.prompts[0]
    assert "본문 전체, HTML, JSON, URL, 코드 조각을 넣지 마시오" in fake.prompts[0]
    assert "원문에 없는 정보, 추측, 평가, 과장 표현을 포함하지 마시오." in fake.prompts[0]
    assert output["events"][0]["stage"] == "summarize"


def test_summarizer_fills_enrichment_when_model_returns_plain_summary():
    fake = SequenceChatClient(
        [
            "문장1. 문장2. 문장3.",
            """{
              "summary": [
                "문장1을 전하고 있어요.",
                "문장2를 전하고 있어요.",
                "문장3을 전하고 있어요."
              ]
            }""",
        ]
    )
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "content": "첫 문단입니다.\n\n둘째 문단입니다.\n\n셋째 문단입니다.",
            }
        ],
        "events": [],
    }

    article = Summarizer(chat_client=fake).run(state)["articles"][0]

    assert article["summary"] == [
        "문장1을 전하고 있어요.",
        "문장2를 전하고 있어요.",
        "문장3을 전하고 있어요.",
    ]
    assert len(fake.prompts) == 2
    assert "기존 summary" in fake.prompts[1]
    assert article["keywords"]
    assert article["importance"]
    assert article["context"] == "AI·뉴스는 이 기사를 이해하는 핵심 배경이에요. 문장1에 대해 먼저 알아두면 좋아요."
    assert article["importanceScore"] == 5


def test_summarizer_rewrites_non_friendly_summary_once():
    fake = SequenceChatClient(
        [
            """{
              "summary": [
                "정부가 AI 반도체 지원책을 확대한다고 밝혔다.",
                "기업 투자가 늘면서 기술 경쟁이 빨라졌다.",
                "업계는 후속 지원 방향을 지켜보고 있다."
              ],
              "keywords": ["AI 반도체", "정부 지원", "기업 투자"],
              "importance": "AI 반도체 지원 정책의 변화를 보여준다.",
              "context": "정부와 기업의 AI 반도체 투자 흐름을 다룬 기사다.",
              "importanceScore": 8
            }""",
            """{
              "summary": [
                "정부가 AI 반도체 지원책을 확대하고 있어요.",
                "기업 투자가 늘면서 기술 경쟁도 빨라지고 있어요.",
                "업계는 후속 지원 방향을 지켜보고 있어요."
              ]
            }""",
        ]
    )
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 반도체 지원 확대",
                "content": "정부가 AI 반도체 지원책을 확대한다고 밝혔다.",
            }
        ],
        "events": [],
    }

    article = Summarizer(chat_client=fake).run(state)["articles"][0]

    assert article["summary"] == [
        "정부가 AI 반도체 지원책을 확대하고 있어요.",
        "기업 투자가 늘면서 기술 경쟁도 빨라지고 있어요.",
        "업계는 후속 지원 방향을 지켜보고 있어요.",
    ]
    assert all(sentence.endswith("요.") for sentence in article["summary"])
    assert article["keywords"] == ["AI 반도체", "정부 지원", "기업 투자"]
    assert len(fake.prompts) == 2
    assert "새 사실, 추측, 평가, 과장 표현을 추가하지 마시오." in fake.prompts[1]


def test_summarizer_extracts_summary_from_fenced_json_response():
    fake = FakeChatClient()
    fake.complete = lambda messages: """```json
{
  "summary": [
    "강소라는 20kg 체중 감량 후 식단 관리와 함께 죽염을 챙기고 있어요.",
    "강소라는 아침 공복에 죽염 1포를 섭취한다고 설명하고 있어요.",
    "강소라는 죽염 섭취 후 몸이 가벼워진 느낌을 받았다고 말하고 있어요."
  ],
  "keywords": ["강소라", "20kg 감량", "죽염"],
  "importance": "죽염을 활용한 건강 관리 습관을 소개했기 때문에 중요하다.",
  "context": ["강소라는 체중 감량 경험을 공유했다."],
  "importanceScore": 5
}
```"""
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "강소라 죽염",
                "content": "강소라는 체중 감량 후 죽염을 챙긴다고 말했다.",
            }
        ],
        "events": [],
    }

    article = Summarizer(chat_client=fake).run(state)["articles"][0]

    assert article["summary"] == [
        "강소라는 20kg 체중 감량 후 식단 관리와 함께 죽염을 챙기고 있어요.",
        "강소라는 아침 공복에 죽염 1포를 섭취한다고 설명하고 있어요.",
        "강소라는 죽염 섭취 후 몸이 가벼워진 느낌을 받았다고 말하고 있어요.",
    ]
    assert article["importance"] == "죽염을 활용한 건강 관리 습관을 소개했기 때문에 중요하다."
    assert article["context"] == "강소라는 체중 감량 경험을 공유했다."
    assert not article["summary"][0].startswith("```json")


def test_summarizer_replaces_raw_context_with_friendly_background():
    raw_context = '{"content":"<div>본문 첫 문단입니다.</div>","rawText":"본문 둘째 문단입니다."}'
    fake = SequenceChatClient(
        [
            f"""{{
              "summary": [
                "AI 에이전트 도입이 업무 자동화 경쟁을 키우고 있어요.",
                "기업들은 이메일 작성과 파일 관리 같은 반복 작업을 자동화하고 있어요.",
                "국내 서비스도 관련 기능을 준비하고 있어요."
              ],
              "keywords": ["AI 에이전트", "업무 자동화", "서비스 경쟁"],
              "importance": "AI 에이전트가 실제 업무 도구로 들어오면 기업의 반복 업무 방식과 관련 직무 수요가 달라질 수 있어요.",
              "context": {json.dumps(raw_context, ensure_ascii=False)},
              "importanceScore": 8
            }}"""
        ]
    )
    content = (
        "AI 에이전트가 이메일 작성과 파일 관리 같은 업무를 자동화하고 있다. "
        "기업들이 관련 기능을 도입하고 있다. "
        "국내 서비스도 시장 진입을 준비하고 있다. "
        "이 문장은 raw fallback으로 복사되면 안 된다."
    )
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 에이전트 경쟁",
                "content": content,
            }
        ],
        "events": [],
    }

    article = Summarizer(chat_client=fake).run(state)["articles"][0]

    assert article["context"] == (
        "AI 에이전트·업무 자동화는 이 기사를 이해하는 핵심 배경이에요. "
        "AI 에이전트 도입이 업무 자동화 경쟁을 키우고 있어요."
    )
    assert raw_context not in article["context"]


def test_summarizer_uses_local_fallback_when_model_rate_limited():
    content = (
        "function track(){ window.dataLayer.push({event:'ad'}); } "
        "AI 에이전트가 이메일 작성과 파일 정리를 자동화하고 있어요. "
        "기업들이 반복 업무를 줄이기 위해 관련 기능을 도입하고 있어요. "
        "국내 서비스도 업무 도구 경쟁에 들어가고 있어요."
    )
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 에이전트 경쟁",
                "content": content,
            }
        ],
        "events": [],
    }

    article = Summarizer(chat_client=FailingChatClient()).run(state)["articles"][0]

    assert len(article["summary"]) == 3
    assert all(sentence.endswith("요.") for sentence in article["summary"])
    assert "function" not in " ".join(article["summary"])
    assert "window" not in article["context"]
    assert article["context"].endswith("요.")
    assert article["importance"]
