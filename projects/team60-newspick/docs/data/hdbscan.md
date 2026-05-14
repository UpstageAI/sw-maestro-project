# HDBSCAN

데일리 리포트의 헤드라인·서브 기사 선정에 사용한다. 코드 출처: [architecture/pipeline-design.md](../architecture/pipeline-design.md) 의 ArticleClusterer 섹션.

## 사용 위치

- ReportPipeline 의 `ArticleClusterer` 노드 (Python).
- 입력: 오늘 수집된 기사들의 4096차원 Solar 임베딩.
- 출력: 클러스터 리스트 (각 클러스터는 같은 이슈를 다룬 기사들의 묶음).

## 라이브러리

```bash
# Python AI 서비스 측
pip install hdbscan numpy
# 또는 uv
uv add hdbscan numpy
```

## 핵심 파라미터

| 파라미터 | 값 | 근거 |
|---|---|---|
| `min_cluster_size` | 2 | 하루 20~30건 환경에서 같은 이슈를 다룬 기사가 2개 이상이면 클러스터로 인정 |
| `metric` | `euclidean` | Solar 임베딩이 L2 정규화되어 있으면 euclidean ≈ cosine 과 등가. 정규화 안 되어 있다면 사전에 정규화 후 euclidean 사용 |
| `min_samples` | 기본값 (= `min_cluster_size`) | 별도 튜닝 불요 |

`label == -1` 은 단독 기사(노이즈) — 헤드라인 후보에서 제외한다.

## 정규화

Solar 임베딩이 단위 벡터로 출력되는지 확인 후, 안 되어 있으면 클러스터링 전에 L2 정규화:

```python
import numpy as np

embeddings = np.array([a["embedding"] for a in articles])
embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
```

> 정규화하면 euclidean 거리 = √(2 - 2·cos_sim) 이 되어 cosine 정렬과 동일한 클러스터가 나온다.

## 운영 시 결정사항 (Phase B 이후)

- 클러스터 결과의 안정성 평가 — 같은 데이터로 여러 번 돌려도 같은 클러스터가 나오는지.
- `min_cluster_size` 변경 시 영향 — 1로 두면 모든 기사가 단독 클러스터, 3+ 면 클러스터 자체가 잘 안 생김.
- 매체별 가중치 — 같은 이슈를 종합 매체 3곳·전문 매체 1곳이 다뤘을 때 클러스터 크기는 4지만, 헤드라인 정렬 시 어떻게 평가할지.

## 주의점

- HDBSCAN 은 `min_cluster_size` 미만의 점은 모두 노이즈(`-1`)로 분류 — 단독 기사는 헤드라인에 절대 못 나옴. 큰 이슈가 한 매체만 다룬 경우에도 노이즈가 되니 발표 시연 데이터 준비 시 같은 이슈를 여러 매체가 다루는지 사전 확인 필요.
- 4096차원에서 거리 계산은 점 100개 기준으로도 매우 빠름 (밀리초).
- Python `hdbscan` 패키지는 numpy 호환. `scikit-learn` 1.3+ 의 `HDBSCAN` 도 동일 알고리즘이지만 외부 패키지 쪽이 옵션이 더 많음.

## 레퍼런스

- hdbscan: https://hdbscan.readthedocs.io/
- 알고리즘 논문: https://link.springer.com/chapter/10.1007/978-3-642-37456-2_14
