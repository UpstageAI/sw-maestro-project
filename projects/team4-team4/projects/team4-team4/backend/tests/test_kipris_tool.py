import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

from backend.app.tools import KiprisTool, getKiprisTools
from backend.app.tools.kipris_tool import _parse_advanced_search_xml

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


class KiprisToolTest(unittest.TestCase):
    def test_build_advanced_search_params_maps_document_fields(self):
        tool = KiprisTool(api_key="test-key")

        params = tool._build_advanced_search_params(
            word="자동차",
            invention_title="엔진",
            astrt_cont="초록",
            claim_scope="청구",
            ipc_number="B60",
            application_number="1020240000000",
            open_number="1020250000000",
            publication_number="1020250000001",
            register_number="1000000000000",
            priority_application_number="PCT-1",
            international_application_number="PCT/KR2024/1",
            internation_open_number="WO2024/1",
            application_date="20240101",
            open_date="20250101",
            publication_date="20250201",
            register_date="20250301",
            priority_application_date="20231201",
            international_application_date="20240102",
            internation_open_date="20250102",
            applicant="현대자동차",
            inventors="홍길동",
            agent="대리인",
            right_holer="권리자",
            patent=True,
            utility=False,
            lastvalue="A",
            page_no=2,
            num_of_rows=50,
            sort_spec="AD",
            desc_sort=False,
        )

        self.assertEqual(params["word"], "자동차")
        self.assertEqual(params["inventionTitle"], "엔진")
        self.assertEqual(params["astrtCont"], "초록")
        self.assertEqual(params["claimScope"], "청구")
        self.assertEqual(params["ipcNumber"], "B60")
        self.assertEqual(params["applicationNumber"], "1020240000000")
        self.assertEqual(params["internationOpenNumber"], "WO2024/1")
        self.assertEqual(params["internationOpenDate"], "20250102")
        self.assertEqual(params["rightHoler"], "권리자")
        self.assertEqual(params["patent"], "true")
        self.assertEqual(params["utility"], "false")
        self.assertEqual(params["pageNo"], "2")
        self.assertEqual(params["numOfRows"], "50")
        self.assertEqual(params["descSort"], "false")
        self.assertEqual(params["ServiceKey"], "test-key")

    def test_parse_advanced_search_xml_returns_records_and_count(self):
        xml_text = """
        <response>
          <header>
            <resultCode>00</resultCode>
            <resultMsg>NORMAL_SERVICE</resultMsg>
          </header>
          <body>
            <items>
              <item>
                <indexNo>1</indexNo>
                <registerStatus>등록</registerStatus>
                <inventionTitle>자동차 엔진 제어 장치</inventionTitle>
                <ipcNumber>B60W</ipcNumber>
                <registerNumber>1000000000000</registerNumber>
                <registerDate>20250101</registerDate>
                <applicationNumber>1020240000000</applicationNumber>
                <applicationDate>20240101</applicationDate>
                <openNumber>1020250000000</openNumber>
                <openDate>20250115</openDate>
                <publicationNumber>1020250000001</publicationNumber>
                <publicationDate>20250201</publicationDate>
                <astrtCont>자동차 엔진을 제어하는 장치에 관한 것이다.</astrtCont>
                <drawing>drawing-url</drawing>
                <bigDrawing>big-drawing-url</bigDrawing>
                <applicantName>현대자동차</applicantName>
              </item>
            </items>
          </body>
          <count>
            <numOfRows>30</numOfRows>
            <pageNo>1</pageNo>
            <totalCount>1</totalCount>
          </count>
        </response>
        """

        result = _parse_advanced_search_xml(xml_text)

        print("\n[KIPRIS sample XML parse]")
        print(f"result_code: {result.result_code}")
        print(f"result_message: {result.result_message}")
        print(f"success: {result.success}")
        print(f"total_count: {result.total_count}")
        print(f"records: {len(result.records)}")
        for record in result.records:
            print(f"- index_no: {record.index_no}")
            print(f"  application_number: {record.application_number}")
            print(f"  invention_title: {record.invention_title}")
            print(f"  applicant_name: {record.applicant_name}")
            print(f"  abstract: {record.abstract}")

        self.assertTrue(result.success)
        self.assertEqual(result.result_code, "00")
        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.page_no, 1)
        self.assertEqual(result.num_of_rows, 30)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].invention_title, "자동차 엔진 제어 장치")
        self.assertEqual(result.records[0].applicant_name, "현대자동차")
        self.assertEqual(result.records[0].abstract, "자동차 엔진을 제어하는 장치에 관한 것이다.")

    def test_live_advanced_search_returns_real_records(self):
        """실제 KIPRIS 서버에서 records가 1건 이상 나오는 쿼리 조합을 찾습니다."""
        load_dotenv(ROOT_DIR / ".env")
        load_dotenv(BACKEND_DIR / ".env", override=True)
        if not os.getenv("KIPRIS_API_KEY"):
            raise unittest.SkipTest("필수 환경 변수가 없어 테스트를 건너뜁니다: KIPRIS_API_KEY")

        tool = KiprisTool()
        candidate_queries = [
            {"word": "자동차", "page_no": 1, "num_of_rows": 3},
            {"invention_title": "자동차", "page_no": 1, "num_of_rows": 3},
            {"applicant": "현대자동차", "page_no": 1, "num_of_rows": 3},
            {"word": "이차전지", "page_no": 1, "num_of_rows": 3},
            {"word": "반도체", "page_no": 1, "num_of_rows": 3},
            {"word": "엔진", "page_no": 1, "num_of_rows": 3},
        ]
        failures = []

        print("\n[KIPRIS getAdvancedSearch live query candidates]")
        for index, query in enumerate(candidate_queries, start=1):
            result = tool.get_advanced_search(**query)
            print(f"\n후보 {index}: {query}")
            print(f"result_code: {result.result_code}")
            print(f"result_message: {result.result_message}")
            print(f"success: {result.success}")
            print(f"total_count: {result.total_count}")
            print(f"records: {len(result.records)}")
            for record in result.records[:3]:
                print(
                    "- "
                    f"{record.application_number} / "
                    f"{record.invention_title} / "
                    f"{record.applicant_name}"
                )

            if result.success and result.records:
                self.assertIsNotNone(result.total_count)
                self.assertGreater(result.total_count, 0)
                return

            failures.append(
                {
                    "query": query,
                    "result_code": result.result_code,
                    "result_message": result.result_message,
                    "raw_header": result.raw_header,
                }
            )

        self.fail(f"KIPRIS records를 반환한 후보 쿼리가 없습니다: {failures}")

    def test_get_kipris_tools_returns_langchain_tools(self):
        try:
            import langchain  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("langchain 패키지가 없어 LangChain Tool 테스트를 건너뜁니다.")

        load_dotenv(ROOT_DIR / ".env")
        load_dotenv(BACKEND_DIR / ".env", override=True)
        if not os.getenv("KIPRIS_API_KEY"):
            raise unittest.SkipTest("필수 환경 변수가 없어 테스트를 건너뜁니다: KIPRIS_API_KEY")

        tools = getKiprisTools(KiprisTool())
        tools_by_name = {tool.name: tool for tool in tools}

        self.assertIn("search_kipris_patents", tools_by_name)
        self.assertIn("search_kipris_patents_by_title", tools_by_name)
        self.assertIn("search_kipris_patents_by_applicant", tools_by_name)


if __name__ == "__main__":
    unittest.main()
