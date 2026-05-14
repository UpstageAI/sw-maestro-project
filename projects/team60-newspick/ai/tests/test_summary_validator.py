from newspick_ai.graph.summary_validator import SummaryValidator


def test_summary_validator_rejects_empty_or_too_long_summary():
    validator = SummaryValidator()

    valid = validator.run(
        {
            "articles": [
                {
                    "id": "article_valid",
                    "summary": "문장1. 문장2. 문장3.",
                }
            ],
            "events": [],
        }
    )
    blank = validator.run(
        {
            "articles": [
                {
                    "id": "article_blank",
                    "summary": "",
                }
            ],
            "events": [],
        }
    )
    too_long = validator.run(
        {
            "articles": [
                {
                    "id": "article_long",
                    "summary": "가" * 800,
                }
            ],
            "events": [],
        }
    )

    assert valid["articles"][0]["status"] == "summarized"
    assert blank["articles"][0]["status"] == "summary_invalid"
    assert too_long["articles"][0]["status"] == "summary_invalid"
