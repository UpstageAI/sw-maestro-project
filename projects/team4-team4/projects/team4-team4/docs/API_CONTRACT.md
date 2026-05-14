# API Contract

## Base URL

개발 중 기본값은 다음 중 하나로 통일합니다.

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## POST `/api/generate`

사용자의 아이디어를 받아 특허 명세서 초안을 생성합니다.

### Request

```json
{
  "idea": "방구로 가는 자동차",
  "tone": "serious",
  "use_search": true
}
```

### Request Fields

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `idea` | string | yes | 사용자의 발명 아이디어, 한국어 1~3문장 |
| `tone` | string | no | `serious`, `absurd`, `short` 중 하나 |
| `use_search` | boolean | no | 검색 근거 사용 여부 |

### Success Response

```json
{
  "id": "demo-001",
  "status": "completed",
  "input": {
    "idea": "방구로 가는 자동차",
    "tone": "serious",
    "use_search": true
  },
  "document": {
    "title": "생체 가스 배출 압력을 이용한 친환경 추진 차량",
    "technical_field": "본 발명은 생체 유래 가스의 압력 에너지를 차량 추진력으로 변환하는 친환경 추진 시스템에 관한 것이다.",
    "background": "기존 내연기관 차량은 화석연료 연소에 의존하여 배출가스 문제가 발생한다. 또한 생체 유래 가스는 일반적으로 폐기되거나 대기 중으로 방출되어 에너지 자원으로 활용되지 못하였다.",
    "problem": "본 발명은 생체 가스의 순간 배출 압력을 회수하여 보조 추진력으로 전환함으로써 에너지 활용 효율을 개선하는 것을 목적으로 한다.",
    "configuration": "본 발명은 생체 가스 포집부, 압력 안정화 챔버, 추진 노즐, 악취 저감 필터 및 제어부를 포함한다.",
    "claims": [
      "생체 가스 배출 압력을 포집하는 포집부와, 상기 포집부로부터 유입된 압력을 저장하는 압력 안정화 챔버와, 상기 압력을 차량 추진력으로 변환하는 추진 노즐을 포함하는 친환경 추진 차량.",
      "제1항에 있어서, 상기 포집부는 착석부 하부에 배치되는 것을 특징으로 하는 친환경 추진 차량.",
      "제1항에 있어서, 상기 압력 안정화 챔버는 역류 방지 밸브를 포함하는 것을 특징으로 하는 친환경 추진 차량.",
      "제1항에 있어서, 상기 추진 노즐은 악취 저감 필터를 거친 가스를 배출하는 것을 특징으로 하는 친환경 추진 차량."
    ],
    "summary": "본 발명은 생체 가스 배출 압력을 차량의 보조 추진 에너지로 활용하는 친환경 추진 차량에 관한 것이다."
  },
  "sources": [
    {
      "title": "검색 결과 제목",
      "url": "https://example.com",
      "snippet": "검색 결과 요약"
    }
  ],
  "warnings": [
    "본 결과물은 엔터테인먼트 목적이며 실제 특허 출원 자문이 아닙니다."
  ]
}
```

### Error Response

```json
{
  "status": "error",
  "code": "INVALID_INPUT",
  "message": "한국어로 1~3문장의 아이디어를 입력해주세요."
}
```

## Error Codes

| 코드 | 상황 |
| --- | --- |
| `INVALID_INPUT` | 입력이 비었거나 너무 김 |
| `UNSUPPORTED_LANGUAGE` | 한국어가 아닌 입력 |
| `UNSAFE_TOPIC` | 무기, 의약품, 금융사기 등 거부 주제 |
| `GENERATION_FAILED` | LLM 호출 실패 |
| `SEARCH_FAILED` | 검색 API 실패. 이 경우 검색 없이 생성해도 됨 |

## Frontend 표시 규칙

- `document.title`은 결과 화면 최상단에 크게 표시합니다.
- `claims`는 번호가 붙은 목록으로 표시합니다.
- `sources`가 비어 있으면 "검색 근거 없이 생성된 데모 결과입니다"를 표시합니다.
- `warnings`는 결과 하단에 항상 표시합니다.

