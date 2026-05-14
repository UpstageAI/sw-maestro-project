import unittest

from backend.app.storage import ChromaDBConnection


KNOWN_PATENT_ID = "690dc67fa424e6f6ab885b4a"


class ChormaDbIntegrationTest(unittest.TestCase):
    """storage 연결 객체가 실제 ChromaDB migration collection을 읽는지 확인합니다."""

    @classmethod
    def setUpClass(cls):
        cls.db = ChromaDBConnection.from_env()

    def test_collection_id_is_resolved_from_real_database(self):
        collection_id = self.db.collection_id

        print(f"\n[ChromaDBConnection] collection_id={collection_id}")
        self.assertTrue(collection_id)

    def test_count_reads_real_database(self):
        count = self.db.count()

        print(f"\n[ChromaDBConnection] count={count}")
        self.assertGreater(count, 0)

    def test_get_documents_reads_known_patent(self):
        documents = self.db.get_documents(ids=[KNOWN_PATENT_ID])

        print(f"\n[ChromaDBConnection] get_documents returned={len(documents)}")
        for document in documents:
            print(
                f"  id={document.id} title={document.metadata.get('inventionTitle')} "
                f"source={document.metadata.get('source_collection')}"
            )
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].id, KNOWN_PATENT_ID)
        self.assertEqual(documents[0].metadata.get("mongo_id"), KNOWN_PATENT_ID)
        self.assertEqual(documents[0].metadata.get("source_collection"), "crawler_db.kipris_patents")

    def test_query_embeddings_reads_real_database(self):
        documents = self.db.query_embeddings(query_embeddings=[[0.0] * 4096], n_results=1)

        print(f"\n[ChromaDBConnection] query_embeddings returned={len(documents)}")
        for document in documents:
            print(
                f"  id={document.id} distance={document.distance} "
                f"title={document.metadata.get('inventionTitle')}"
            )
        self.assertEqual(len(documents), 1)
        self.assertTrue(documents[0].id)
        self.assertTrue(documents[0].document)
        self.assertIsNotNone(documents[0].distance)


if __name__ == "__main__":
    unittest.main()
