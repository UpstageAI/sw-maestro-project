from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any


KIPRIS_ADVANCED_SEARCH_URL = (
    "http://plus.kipris.or.kr/kipo-api/kipi/"
    "patUtiModInfoSearchSevice/getAdvancedSearch"
)
KIPRIS_DEFAULT_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class KiprisPatentRecord:
    """KIPRIS getAdvancedSearch 결과 특허 1건입니다."""

    index_no: str = ""
    register_status: str = ""
    invention_title: str = ""
    ipc_number: str = ""
    register_number: str = ""
    register_date: str = ""
    application_number: str = ""
    application_date: str = ""
    open_number: str = ""
    open_date: str = ""
    publication_number: str = ""
    publication_date: str = ""
    abstract: str = ""
    drawing: str = ""
    big_drawing: str = ""
    applicant_name: str = ""
    raw: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """LangChain tool 응답으로 직렬화하기 쉬운 dict로 변환합니다."""
        return {
            "index_no": self.index_no,
            "register_status": self.register_status,
            "invention_title": self.invention_title,
            "ipc_number": self.ipc_number,
            "register_number": self.register_number,
            "register_date": self.register_date,
            "application_number": self.application_number,
            "application_date": self.application_date,
            "open_number": self.open_number,
            "open_date": self.open_date,
            "publication_number": self.publication_number,
            "publication_date": self.publication_date,
            "abstract": self.abstract,
            "drawing": self.drawing,
            "big_drawing": self.big_drawing,
            "applicant_name": self.applicant_name,
        }


@dataclass(frozen=True)
class KiprisSearchResult:
    """KIPRIS getAdvancedSearch 응답 전체를 backend에서 쓰기 쉽게 정리한 값입니다."""

    result_code: str
    result_message: str
    success: bool
    total_count: int | None
    page_no: int | None
    num_of_rows: int | None
    records: list[KiprisPatentRecord]
    raw_header: dict[str, str]
    raw_count: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """LangChain tool 응답으로 직렬화하기 쉬운 dict로 변환합니다."""
        return {
            "result_code": self.result_code,
            "result_message": self.result_message,
            "success": self.success,
            "total_count": self.total_count,
            "page_no": self.page_no,
            "num_of_rows": self.num_of_rows,
            "records": [record.to_dict() for record in self.records],
        }


class KiprisTool:
    """KIPRIS 특허·실용 공개·등록공보 REST 항목별검색 도구입니다.

    현재는 `getAdvancedSearch`만 직접 호출합니다. 외부 langchain_kipris_tools 패키지를 쓰지 않고
    표준 라이브러리로 요청과 XML 파싱을 처리해 MVP backend에서 의존성 없이 사용할 수 있게 했습니다.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: int = KIPRIS_DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key or os.getenv("KIPRIS_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing required environment variable: KIPRIS_API_KEY")
        self.timeout_seconds = timeout_seconds

    def get_advanced_search(
        self,
        word: str = "",
        invention_title: str = "",
        astrt_cont: str = "",
        claim_scope: str = "",
        ipc_number: str = "",
        application_number: str = "",
        open_number: str = "",
        publication_number: str = "",
        register_number: str = "",
        priority_application_number: str = "",
        international_application_number: str = "",
        internation_open_number: str = "",
        application_date: str = "",
        open_date: str = "",
        publication_date: str = "",
        register_date: str = "",
        priority_application_date: str = "",
        international_application_date: str = "",
        internation_open_date: str = "",
        applicant: str = "",
        inventors: str = "",
        agent: str = "",
        right_holer: str = "",
        patent: bool = True,
        utility: bool = True,
        lastvalue: str = "",
        page_no: int = 1,
        num_of_rows: int = 30,
        sort_spec: str = "AD",
        desc_sort: bool = True,
    ) -> KiprisSearchResult:
        """KIPRIS getAdvancedSearch를 호출합니다.

        Args는 KIPRIS 문서의 입력값을 Python snake_case로 옮긴 값입니다.
        KIPRIS 원문에 오타처럼 보이는 `internationOpenNumber`, `internationOpenDate`,
        `rightHoler`는 실제 요청 파라미터명과 맞추기 위해 그대로 매핑합니다.
        """
        params = self._build_advanced_search_params(
            word=word,
            invention_title=invention_title,
            astrt_cont=astrt_cont,
            claim_scope=claim_scope,
            ipc_number=ipc_number,
            application_number=application_number,
            open_number=open_number,
            publication_number=publication_number,
            register_number=register_number,
            priority_application_number=priority_application_number,
            international_application_number=international_application_number,
            internation_open_number=internation_open_number,
            application_date=application_date,
            open_date=open_date,
            publication_date=publication_date,
            register_date=register_date,
            priority_application_date=priority_application_date,
            international_application_date=international_application_date,
            internation_open_date=internation_open_date,
            applicant=applicant,
            inventors=inventors,
            agent=agent,
            right_holer=right_holer,
            patent=patent,
            utility=utility,
            lastvalue=lastvalue,
            page_no=page_no,
            num_of_rows=num_of_rows,
            sort_spec=sort_spec,
            desc_sort=desc_sort,
        )
        xml_text = self._request_xml(KIPRIS_ADVANCED_SEARCH_URL, params)
        return _parse_advanced_search_xml(xml_text)

    def search_for_context(self, query: str) -> str:
        """LangChain agent가 쓰기 좋은 JSON 문자열 KIPRIS 검색 결과를 반환합니다.

        입력은 일반 문자열이면 `word` 자유검색으로 처리합니다.
        JSON 문자열이면 `word`, `invention_title`, `applicant`, `ipc_number`,
        `application_number`, `register_number`, `num_of_rows`를 선택적으로 받을 수 있습니다.
        """
        payload = _parse_tool_input(query)
        result = self.get_advanced_search(
            word=payload.get("word", ""),
            invention_title=payload.get("invention_title", ""),
            ipc_number=payload.get("ipc_number", ""),
            application_number=payload.get("application_number", ""),
            register_number=payload.get("register_number", ""),
            applicant=payload.get("applicant", ""),
            page_no=int(payload.get("page_no", 1)),
            num_of_rows=_coerce_num_of_rows(payload.get("num_of_rows", 5)),
        )
        return _to_json(
            {
                "query": payload,
                "source": "KIPRIS getAdvancedSearch",
                **result.to_dict(),
            }
        )

    def search_title_for_context(self, invention_title: str) -> str:
        """발명의 명칭 기준 KIPRIS 검색 결과를 JSON 문자열로 반환합니다."""
        result = self.get_advanced_search(
            invention_title=invention_title.strip(),
            page_no=1,
            num_of_rows=5,
        )
        return _to_json(
            {
                "query": {"invention_title": invention_title.strip()},
                "source": "KIPRIS getAdvancedSearch",
                **result.to_dict(),
            }
        )

    def search_applicant_for_context(self, applicant: str) -> str:
        """출원인 기준 KIPRIS 검색 결과를 JSON 문자열로 반환합니다."""
        result = self.get_advanced_search(
            applicant=applicant.strip(),
            page_no=1,
            num_of_rows=5,
        )
        return _to_json(
            {
                "query": {"applicant": applicant.strip()},
                "source": "KIPRIS getAdvancedSearch",
                **result.to_dict(),
            }
        )

    def _build_advanced_search_params(self, **kwargs: Any) -> dict[str, str]:
        params = {
            "word": kwargs["word"],
            "inventionTitle": kwargs["invention_title"],
            "astrtCont": kwargs["astrt_cont"],
            "claimScope": kwargs["claim_scope"],
            "ipcNumber": kwargs["ipc_number"],
            "applicationNumber": kwargs["application_number"],
            "openNumber": kwargs["open_number"],
            "publicationNumber": kwargs["publication_number"],
            "registerNumber": kwargs["register_number"],
            "priorityApplicationNumber": kwargs["priority_application_number"],
            "internationalApplicationNumber": kwargs["international_application_number"],
            "internationOpenNumber": kwargs["internation_open_number"],
            "applicationDate": kwargs["application_date"],
            "openDate": kwargs["open_date"],
            "publicationDate": kwargs["publication_date"],
            "registerDate": kwargs["register_date"],
            "priorityApplicationDate": kwargs["priority_application_date"],
            "internationalApplicationDate": kwargs["international_application_date"],
            "internationOpenDate": kwargs["internation_open_date"],
            "applicant": kwargs["applicant"],
            "inventors": kwargs["inventors"],
            "agent": kwargs["agent"],
            "rightHoler": kwargs["right_holer"],
            "patent": _bool_to_kipris(kwargs["patent"]),
            "utility": _bool_to_kipris(kwargs["utility"]),
            "lastvalue": kwargs["lastvalue"],
            "pageNo": str(kwargs["page_no"]),
            "numOfRows": str(kwargs["num_of_rows"]),
            "sortSpec": kwargs["sort_spec"],
            "descSort": _bool_to_kipris(kwargs["desc_sort"]),
            "ServiceKey": self.api_key,
        }
        return {key: value for key, value in params.items() if value not in ("", None)}

    def _request_xml(self, url: str, params: dict[str, str]) -> str:
        os.environ.pop("SSLKEYLOGFILE", None)
        query = urllib.parse.urlencode(params)
        request_url = f"{url}?{query}"
        with urllib.request.urlopen(request_url, timeout=self.timeout_seconds) as response:
            body = response.read()
        return body.decode("utf-8", errors="replace")


def getTools(tool: KiprisTool | None = None) -> list[Any]:
    """LangChain agent가 사용할 KIPRIS Tool 목록을 반환합니다."""
    try:
        from langchain.tools import Tool
    except ImportError:
        from langchain_core.tools import Tool

    kipris_tool = tool or KiprisTool()

    return [
        Tool.from_function(
            name="search_kipris_patents",
            description=(
                "KIPRIS getAdvancedSearch API로 특허/실용 공개·등록공보를 검색합니다. "
                "입력은 일반 검색어 문자열이거나 JSON 문자열입니다. JSON 예: "
                '{"word":"자동차","applicant":"현대자동차","num_of_rows":5}'
            ),
            func=kipris_tool.search_for_context,
        ),
        Tool.from_function(
            name="search_kipris_patents_by_title",
            description="발명의 명칭으로 KIPRIS 특허를 검색합니다. 입력은 발명의 명칭 검색어입니다.",
            func=kipris_tool.search_title_for_context,
        ),
        Tool.from_function(
            name="search_kipris_patents_by_applicant",
            description="출원인 이름으로 KIPRIS 특허를 검색합니다. 입력은 출원인 이름입니다.",
            func=kipris_tool.search_applicant_for_context,
        ),
    ]


def _parse_advanced_search_xml(xml_text: str) -> KiprisSearchResult:
    root = ET.fromstring(xml_text)
    header = _children_text(root.find("header"))
    count = _children_text(root.find("count"))
    records = [_parse_patent_item(item) for item in root.findall(".//items/item")]
    result_code = header.get("resultCode", "")

    return KiprisSearchResult(
        result_code=result_code,
        result_message=header.get("resultMsg", ""),
        success=result_code == "00",
        total_count=_to_int_or_none(count.get("totalCount")),
        page_no=_to_int_or_none(count.get("pageNo")),
        num_of_rows=_to_int_or_none(count.get("numOfRows")),
        records=records,
        raw_header=header,
        raw_count=count,
    )


def _parse_patent_item(item: ET.Element) -> KiprisPatentRecord:
    raw = _children_text(item)
    return KiprisPatentRecord(
        index_no=raw.get("indexNo", ""),
        register_status=raw.get("registerStatus", ""),
        invention_title=raw.get("inventionTitle", ""),
        ipc_number=raw.get("ipcNumber", ""),
        register_number=raw.get("registerNumber", ""),
        register_date=raw.get("registerDate", ""),
        application_number=raw.get("applicationNumber", ""),
        application_date=raw.get("applicationDate", ""),
        open_number=raw.get("openNumber", ""),
        open_date=raw.get("openDate", ""),
        publication_number=raw.get("publicationNumber", ""),
        publication_date=raw.get("publicationDate", ""),
        abstract=raw.get("astrtCont", ""),
        drawing=raw.get("drawing", ""),
        big_drawing=raw.get("bigDrawing", ""),
        applicant_name=raw.get("applicantName", ""),
        raw=raw,
    )


def _children_text(element: ET.Element | None) -> dict[str, str]:
    if element is None:
        return {}
    return {
        child.tag: (child.text or "").strip()
        for child in list(element)
    }


def _to_int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _bool_to_kipris(value: bool) -> str:
    return "true" if value else "false"


def _parse_tool_input(value: str) -> dict[str, Any]:
    raw_value = value.strip()
    if not raw_value:
        return {}

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {"word": raw_value}

    if not isinstance(parsed, dict):
        return {"word": raw_value}

    allowed_fields = {
        "word",
        "invention_title",
        "applicant",
        "ipc_number",
        "application_number",
        "register_number",
        "page_no",
        "num_of_rows",
    }
    return {
        key: value
        for key, value in parsed.items()
        if key in allowed_fields and value not in ("", None)
    }


def _coerce_num_of_rows(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 5
    return min(max(number, 1), 10)


def _to_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)
