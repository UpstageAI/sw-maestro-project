from __future__ import annotations

import pytest

from agent.agent2.nodes.filter_noise import filter_noise_node
from models.schema import NewsArticle, SECFiling


class TestFilterNoiseNode:
    def test_deduplicates_news_by_title(self, agent_state):
        # collected_data fixture has 2 articles with same title "Apple hits new record"
        result = filter_noise_node(agent_state)
        titles = [a.title for a in result["collected_data"].news_articles]
        assert titles.count("Apple hits new record") == 1

    def test_removes_empty_title_or_url(self, agent_state):
        result = filter_noise_node(agent_state)
        for a in result["collected_data"].news_articles:
            assert a.title.strip() != ""
            assert a.url != ""

    def test_deduplicates_filings_by_url(self, agent_state):
        # collected_data fixture has 2 filings with same url
        result = filter_noise_node(agent_state)
        urls = [f.url for f in result["collected_data"].sec_filings]
        assert len(urls) == len(set(urls))

    def test_keeps_valid_unique_articles(self, agent_state):
        result = filter_noise_node(agent_state)
        titles = [a.title for a in result["collected_data"].news_articles]
        assert "Apple Q1 earnings preview" in titles

    def test_preserves_other_collected_data_fields(self, agent_state):
        result = filter_noise_node(agent_state)
        cd = result["collected_data"]
        assert cd.ticker == "AAPL"
        assert cd.price_stats is not None
        assert len(cd.benchmarks) == 2

    def test_empty_news_and_filings(self, agent_state):
        agent_state["collected_data"] = agent_state["collected_data"].model_copy(
            update={"news_articles": [], "sec_filings": []}
        )
        result = filter_noise_node(agent_state)
        assert result["collected_data"].news_articles == []
        assert result["collected_data"].sec_filings == []
