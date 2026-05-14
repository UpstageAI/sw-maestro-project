from newspick_ai.report.clustering import cluster_articles


def test_cluster_articles_uses_real_hdbscan_with_deterministic_embeddings():
    articles = [
        {"id": "a1", "embedding": [0.0, 0.0]},
        {"id": "a2", "embedding": [0.1, 0.1]},
        {"id": "a3", "embedding": [0.05, 0.05]},
        {"id": "b1", "embedding": [10.0, 10.0]},
        {"id": "b2", "embedding": [10.1, 10.1]},
        {"id": "b3", "embedding": [10.05, 10.05]},
    ]

    result = cluster_articles(articles, min_cluster_size=2)

    non_noise = [a for a in result if a["clusterId"] is not None]
    cluster_ids = set(a["clusterId"] for a in non_noise)
    assert len(cluster_ids) == 2

    for cid in cluster_ids:
        members = [a for a in non_noise if a["clusterId"] == cid]
        assert len(members) >= 2

    result2 = cluster_articles(articles, min_cluster_size=2)
    for r1, r2 in zip(result, result2):
        assert r1["clusterId"] == r2["clusterId"]
