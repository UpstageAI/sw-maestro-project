import unittest

from backend.app.generator import generate_patent_document


class GeneratorTest(unittest.TestCase):
    def test_generate_patent_document_returns_contract_shape(self):
        result = generate_patent_document("방구로 가는 자동차")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["input"]["idea"], "방구로 가는 자동차")
        self.assertIn("document", result)
        self.assertIn("title", result["document"])
        self.assertIn("claims", result["document"])
        self.assertEqual(len(result["document"]["claims"]), 4)
        self.assertIn("warnings", result)


if __name__ == "__main__":
    unittest.main()

