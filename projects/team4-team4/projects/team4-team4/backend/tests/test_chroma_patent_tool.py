import json
import unittest

from backend.app.tools import ChromaPatentTool, getChromaTools


KNOWN_PATENT_ID = "690dc67fa424e6f6ab885b4a"
KNOWN_TITLE = "풀러렌 부가체를 포함하는 3중 혼합물 광활성화층을 이용한 유기물 태양전지"


class ChromaPatentToolIntegrationTest(unittest.TestCase):
    """실제 localhost:8001 ChromaDB에 적재된 migration collection을 조회합니다."""

    @classmethod
    def setUpClass(cls):
        cls.tool = ChromaPatentTool()

    def test_count_reads_real_chroma_collection(self):
        count = self.tool.count()

        print(f"\n[ChromaPatentTool] count={count}")
        self.assertGreater(count, 0)

    def test_get_by_id_reads_known_migrated_patent(self):
        document = self.tool.get_by_id(KNOWN_PATENT_ID)

        self.assertIsNotNone(document)
        print(
            "\n[ChromaPatentTool] get_by_id "
            f"id={document.id} title={document.title} "
            f"source={document.metadata.get('source_collection')}"
        )
        print(f"[ChromaPatentTool] description={document.description[:120]}")
        self.assertEqual(document.id, KNOWN_PATENT_ID)
        self.assertEqual(document.mongo_id, KNOWN_PATENT_ID)
        self.assertEqual(document.title, KNOWN_TITLE)
        self.assertEqual(document.metadata.get("source_collection"), "crawler_db.kipris_patents")
        self.assertIn("전력 변환 효율", document.description)

    def test_list_documents_reads_real_chroma_documents(self):
        documents = self.tool.list_documents(limit=3)

        print(f"\n[ChromaPatentTool] list_documents returned={len(documents)}")
        for index, document in enumerate(documents, start=1):
            print(
                f"  {index}. id={document.id} title={document.title} "
                f"source={document.metadata.get('source_collection')}"
            )
        self.assertGreaterEqual(len(documents), 1)
        self.assertLessEqual(len(documents), 3)
        self.assertTrue(documents[0].id)
        self.assertTrue(documents[0].document)
        self.assertEqual(documents[0].metadata.get("source_collection"), "crawler_db.kipris_patents")

    def test_query_by_embedding_reads_real_chroma_matches(self):
        matches = self.tool.query_by_embedding([0.0] * 4096, match_count=2)

        print(f"\n[ChromaPatentTool] query_by_embedding returned={len(matches)}")
        for index, match in enumerate(matches, start=1):
            print(
                f"  {index}. id={match.id} distance={match.distance} "
                f"title={match.title}"
            )
        self.assertGreaterEqual(len(matches), 1)
        self.assertLessEqual(len(matches), 2)
        self.assertTrue(matches[0].id)
        self.assertTrue(matches[0].document)
        self.assertIsNotNone(matches[0].distance)

    def test_get_tools_returns_langchain_tools_for_real_database(self):
        try:
            import langchain  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("langchain 패키지가 없어 LangChain Tool 테스트를 건너뜁니다.")

        tools = getChromaTools(self.tool)
        tools_by_name = {tool.name: tool for tool in tools}

        self.assertIn("count_kipris_patents_chroma", tools_by_name)
        self.assertIn("get_kipris_patent_by_id", tools_by_name)

        count_payload = json.loads(tools_by_name["count_kipris_patents_chroma"].run(""))
        print(f"\n[LangChain Tool] count payload={count_payload}")
        self.assertGreater(count_payload["count"], 0)

        patent_payload = json.loads(
            tools_by_name["get_kipris_patent_by_id"].run(KNOWN_PATENT_ID)
        )
        print(f"[LangChain Tool] get_by_id payload={patent_payload}")
        self.assertTrue(patent_payload["found"])
        self.assertEqual(patent_payload["result"]["mongo_id"], KNOWN_PATENT_ID)


if __name__ == "__main__":
    unittest.main()
