import numpy as np
import hdbscan


def cluster_articles(articles: list[dict], min_cluster_size: int = 2) -> list[dict]:
    if not articles:
        return []

    embeddings = np.array([a["embedding"] for a in articles], dtype=np.float64)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    return [
        {**article, "clusterId": None if label == -1 else int(label)}
        for article, label in zip(articles, labels)
    ]
