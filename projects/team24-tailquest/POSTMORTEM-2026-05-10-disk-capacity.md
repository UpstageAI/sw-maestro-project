# 회고: EC2 디스크 용량 부족으로 인한 Docker Hub 배포 롤백

**날짜**: 2026-05-10
**영향 범위**: 운영 배포 파이프라인 (소스 변경 0)
**다운타임**: 약 25분 (systemd → docker compose 전환 시도 ↔ 즉시 systemd 복구)
**최종 결정**: Docker Hub 레지스트리 방식 폐기, rsync + systemd 패턴으로 원복

---

## TL;DR

`backend` 컨테이너 이미지를 EC2에 pull 받는 도중 `no space left on device`로 실패했다. 8GB EBS의 OS·앱·docker daemon 차감 후 남은 1.2GB가 chromadb 스택을 포함한 backend 이미지(압축 해제 후 ~1.5GB)를 받기엔 부족했다. 단기적으로는 EBS 증설 비용·시간을 회피하기 위해 **Docker Hub 레지스트리 도입을 롤백하고 rsync + systemd 패턴으로 원복**했다. 장기적으로는 EBS 확장 후 다시 컨테이너화하는 것이 합리적이지만 영상 시연 일정 우선순위 때문에 미뤘다.

---

## 발생 원인

### 1. 인프라 측면 — EBS 8GB의 빠른 소진

| 사용처 | 크기 |
|---|---|
| Ubuntu 26.04 OS + 기본 패키지 | ~3.5GB |
| Python 3.12 (uv-managed) | ~150MB |
| Node 22.22 + 기본 npm 캐시 | ~250MB |
| nginx + certbot | ~50MB |
| Backend `.venv` (chromadb·tokenizers·langgraph·langchain-upstage) | **382MB** |
| Frontend `node_modules` + `.next` | **571MB** |
| `docker.io` + `docker-compose-v2` + `containerd` (이번에 추가) | **350MB** |
| Chroma 영구 저장소(`backend/.chroma/`) | ~6MB |
| Materials(`backend/.materials/`) | ~4.5MB |
| SQLite(`backend/data/tq.db`) | ~57KB |
| **총 사용량** | **~5.4GB** |
| **남은 공간** | **~1.2GB (xvda1 6.7GB 기준)** |

### 2. 이미지 측면 — backend의 ML 의존성 누적

`backend/pyproject.toml`이 끌어오는 무거운 패키지들:

| 패키지 | 설치 후 디스크 점유 | 이유 |
|---|---|---|
| `chromadb>=0.5.0` | ~600MB (전이 의존성 포함) | 벡터 DB |
| → `onnxruntime` | ~200MB | Chroma 기본 임베딩(미사용이지만 패키지로 끌려옴) |
| → `tokenizers` (HF) | ~50MB | PyO3 native, ONNX와 결합 |
| → `sentence-transformers` (chromadb 일부 path) | ~150MB | 사용 안 함 |
| `langchain-core` + `langgraph` | ~80MB | StateGraph·structured output |
| `langchain-upstage` | ~30MB | Solar embeddings |
| `pypdf` + `langchain-text-splitters` | ~25MB | PDF/MD 청크 |
| 기타 (fastapi, sqlalchemy, pydantic, openai 등) | ~100MB | 코어 |

**결론**: 압축 해제된 이미지 약 1.3~1.5GB. 1.2GB 디스크에 들어가지 못함.

### 3. 시스템 측면 — Docker pull의 작동 방식

Docker는 이미지 pull 시:
1. registry에서 `tar.gz` 레이어 다운로드 → `/var/lib/docker/tmp` (또는 buildkit 캐시)
2. 각 레이어 압축 해제 → `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/`
3. 레이어 병합 후 컨테이너 root filesystem 구성

→ **다운로드 + 압축 해제** 둘 다 동시에 디스크에 존재. 압축 비율 ~2:1 가정 시, 압축 해제된 1.3GB 이미지는 다운로드 + 해제 시점에 일시적으로 ~2GB+ 필요.

실제 에러:
```
failed to extract layer ... no space left on device:
write /var/lib/containerd/.../site-packages/zstandard/backend_c.cpython-311-x86_64-linux-gnu.so
```

마지막 큰 레이어(Python site-packages)에서 디스크 고갈로 추출 실패.

---

## 가능했던 해결 방법들

### A. EBS 볼륨 확장 (8GB → 16GB)

| 항목 | 평가 |
|---|---|
| **소요 시간** | AWS Console에서 5분(클릭) + EC2 SSH로 `growpart` + `resize2fs` 1분 |
| **추가 비용** | 월 약 $0.8 (AWS Seoul gp3 0.0922 USD/GB/month × 8GB) |
| **위험도** | 낮음 — 가동 중 확장 가능, OS 인식만 시키면 됨 |
| **장점** | Docker Hub 레지스트리 + 컨테이너 격리·이식성 그대로 유지. ML 패키지 더 추가해도 여유 있음 |
| **단점** | AWS Console 접근 필요(작업자가 다름), 약간의 비용 |

### B. Backend 이미지 슬림화 (Multi-stage + 의존성 정리)

| 항목 | 평가 |
|---|---|
| **소요 시간** | 30분~1시간 (검증 포함) |
| **절약 가능량** | ~200~400MB (아래 분석) |
| **위험도** | 중간 — chromadb 전이 의존성을 잘못 자르면 임베딩 실패 |

세부 옵션:
- Multi-stage 빌드로 `build-essential`(~250MB) 제거 → ~200MB 절감
- chromadb의 `onnxruntime` 의존을 우회 (Solar embedding 직접 사용 — 우리 코드는 이미 Solar embedding 사용 중) → ~200MB 절감 가능
- Python 3.11 → 3.12 slim 변경 (~30MB 차이, marginal)

**최종 추정**: 1.5GB → 1.0~1.1GB. **여전히 1.2GB 디스크에 빠듯**, 빌드 캐시 + 압축 해제 임시 공간까지 고려하면 부족.

### C. 하이브리드 — frontend만 컨테이너화, backend는 systemd 유지

| 항목 | 평가 |
|---|---|
| **Frontend 이미지 크기** | ~500MB (node_modules + .next) |
| **소요 시간** | 1~2시간 (workflow 분리 + nginx 라우팅 검토) |
| **장점** | Frontend는 Docker로 일관성 유지, backend는 venv 그대로 |
| **단점** | 절반만 컨테이너화 — 의도한 "이미지 레지스트리 운영"의 정합성 흐릿함. 운영 복잡도만 늘어남 |

### D. Docker 완전 롤백 — rsync + systemd 패턴 복귀 ✓ 선택됨

| 항목 | 평가 |
|---|---|
| **소요 시간** | 즉시 (이미 검증된 패턴) |
| **추가 비용** | $0 |
| **위험도** | 가장 낮음 — 이전에 작동하던 구성 복귀 |
| **장점** | 디스크 545M 여유. CI 24초 만에 끝나는 빠른 deploy. 실패 시 롤백도 동일 패턴 |
| **단점** | 이미지 격리·이식성 포기. 컨테이너 표준 운영 학습 기회 상실. 사용자 환경(EC2 Linux native 의존성 그대로 노출) |

### E. 별도 EBS 볼륨 마운트 (`/var/lib/docker`만 분리)

| 항목 | 평가 |
|---|---|
| **소요 시간** | 30분 (AWS Console + 마운트 + docker daemon 데이터 dir 변경) |
| **장점** | OS 디스크와 컨테이너 디스크 분리 — 한쪽 이슈가 다른 쪽 안 건드림 |
| **단점** | 결국 비용은 발생(EBS 추가 8GB ~$0.8/mo). A보다 복잡 |

---

## 실제 선택 — 옵션 D (롤백)

### 결정 사유

1. **시간 압박**: 데모 영상 녹화 직전이라 인프라 불확실성을 빠르게 차단해야 했다. EBS 확장은 AWS Console 접근이 필요하고, 확장 후 OS 인식 + Docker pull 재시도까지 ~10분 + 첫 빌드 5~10분이 필요하다.
2. **검증된 패턴**: rsync + systemd는 본 프로젝트가 1주일간 안정 운영했던 구성이다. 롤백 자체가 새로운 위험을 도입하지 않는다.
3. **Docker의 ROI 재평가**: 단일 호스트 단일 테넌트 데모에서 컨테이너 격리의 실효 가치가 낮다. 이식성·재현성 이점은 향후 멀티 호스트로 확장할 때 비로소 유의미해진다.
4. **상기성 보존**: 모든 Docker 자산(`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.override.yml`)을 레포에 그대로 남겨 향후 EBS 확장 후 재활성화 비용을 최소화했다. CI 워크플로만 rsync 패턴으로 교체.

### 수행 단계

1. **Docker pull 중단 + 컨테이너 정리**: `docker compose down`, `docker system prune -af`
2. **systemd 서비스 재활성화**: 직전에 disable해둔 `tq-backend.service`, `tq-frontend.service` 다시 enable + start
3. **`.venv` 재구축**: `uv venv --python 3.12 .venv` + `uv pip install -e .` (~2분)
4. **Frontend 재빌드**: `npm ci` + `npm run build` (~1분)
5. **`docker.io` + `containerd` purge**: `apt-get remove --purge` + `/var/lib/docker` 삭제 → 350MB 회수
6. **CI 워크플로 rsync 패턴으로 교체**: `.github/workflows/deploy-{backend,frontend}.yml` 재작성 (3개 파일 변경)
7. **`pyproject.toml` 패키지 검색 명시화**: `[tool.setuptools.packages.find] include = ["app", "app.*"]` — runtime 생성된 `data/` 디렉토리가 setuptools에 의해 패키지로 오인되는 것 차단
8. **검증**: CI 24초 안에 success, 라이브 `/api/backend/health` 응답 확인

### 결과

- 디스크 여유: 1.2GB → **545MB → 다시 충분** (Docker 제거 후)
- Backend boot_id `VI0w1Kt5-3E`로 가동
- 데모 로그(`🚀 [BOOT]` 등) 정상 출력
- CI/CD 정상 동작 (push → 24초 deploy)

---

## 교훈

### 잘한 점

1. **빠른 결정 + 즉시 롤백**: "이건 가능한가?"에 매달리지 않고 "지금 시점에 의미 있는가?"로 판단했다. 인프라 의사결정에서 시간 가치는 종종 비용 가치보다 크다.
2. **자산 보존**: Dockerfile들과 compose 파일을 레포에 남겨, 향후 재활성화 시 GitHub commit `9023efc`만 cherry-pick 하면 된다는 git 사용성을 활용했다.
3. **회복 가능 상태에서만 실험**: 시도 전 EBS 백업(또는 코드 백업)을 갖추지는 못했지만, 운영 데이터(`.chroma`, `data/tq.db`)는 별도 디렉토리로 분리되어 있어 docker 전환 작업이 데이터에 영향 주지 않는 구조였다.

### 못한 점 / 개선할 점

1. **사전 용량 점검 없이 작업 시작**: Docker 도입 결정 전에 `df -h /` + 이미지 크기 추정만 했어도 1.2GB 부족을 미리 알 수 있었다. 인프라 변경의 첫 단계는 "현재 capacity 측정"이 되어야 한다.
2. **이미지 크기 추정 학습 비용**: chromadb가 onnxruntime + sentence-transformers를 끌어온다는 사실을 빌드 후에야 인지했다. ML 패키지의 의존성 그래프를 사전에 `pipdeptree --json` 등으로 점검할 필요가 있었다.
3. **EC2 인스턴스 사이즈 의사결정의 누적 비용**: 8GB가 디폴트라서 그대로 썼지만, 이번 프로젝트의 ML 의존성을 고려하면 16GB 또는 20GB가 합리적이었다. **비용 최적화는 사용 패턴이 안정된 후에 하는 것이 정석**이라는 원칙을 어겼다.

### 후속 액션 아이템

| 우선순위 | 항목 | 트리거 |
|---|---|---|
| 낮음 | EBS 8GB → 16GB 확장 + Docker Hub 패턴 재활성화 | 데모 영상 녹화 완료 후, 또는 멀티 호스트 확장 필요 시점 |
| 중간 | `pyproject.toml` 의존성 정리 — chromadb의 ML 부산물 줄일 수 있는지 검토 | 시간 여유 있을 때 |
| 낮음 | 운영 디스크 모니터링 알람 (`df -h /` < 1GB일 때 알림) | 운영 안정화 페이즈 |
| 중간 | `backend/pyproject.toml`의 `[tool.setuptools.packages.find]` 변경분을 `lockfile`이나 명시적 install 가이드에 반영 | 새 개발자 온보딩 시 setuptools 오류 재현 가능성 |

---

## 부록 — 참조 커밋

| Commit | 내용 |
|---|---|
| `9023efc` | Docker Hub 레지스트리 도입 (실패한 시도, 자료 보존용) |
| `ce801c6` | 본 회고 대상의 롤백 commit |
| `892fe47` | 원래 `Docker` 자산이 처음 추가된 commit (참고용) |
