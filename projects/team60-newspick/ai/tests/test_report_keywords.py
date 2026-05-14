from newspick_ai.report.keywords import KeywordGenerator


def test_keyword_generator_returns_unique_keywords_with_weight_2_to_9():
    articles = [
        {"summary": ["AI 기술이 빠르게 발전하고 있다. AI는 미래의 핵심이다."]},
        {"summary": ["반도체 시장에서 AI 수요가 급증했다."]},
        {"summary": ["환율 변동이 반도체 수출에 영향을 미쳤다."]},
    ]

    result = KeywordGenerator().generate(articles)

    texts = [k.text for k in result]
    assert len(texts) == len(set(texts))

    for kw in result:
        assert 2 <= kw.weight <= 9
        assert isinstance(kw.weight, int)

    assert len(result) <= 12
    assert result[0].text == "AI"
