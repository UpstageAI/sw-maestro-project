#!/usr/bin/env bash
set -euo pipefail

# 역할: Parquet dump 파일을 로컬 ChromaDB collection에 다시 적재하는 wrapper입니다.
# 파라미터는 command argument 대신 환경 변수로 받습니다.
# CHROMA_URL: ChromaDB 서버 주소입니다. 기본값은 http://localhost:8001 입니다.
# CHROMA_TENANT: ChromaDB tenant 이름입니다. 기본값은 default_tenant 입니다.
# CHROMA_DATABASE: restore할 database 이름입니다. 기본값은 brainrot_patent 입니다.
# CHROMA_COLLECTION: restore할 collection 이름입니다. 기본값은 kipris_patents_v2 입니다.
# INIT_BATCH_SIZE: ChromaDB에 한 번에 upsert할 row 수입니다. 기본값은 100 입니다.
# DUMP_FILE: 읽을 Parquet dump 파일 경로입니다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYDEPS_DIR="${SCRIPT_DIR}/pydeps"
DUMPS_DIR="${SCRIPT_DIR}/dumps"

CHROMA_URL="${CHROMA_URL:-http://localhost:8001}"
CHROMA_TENANT="${CHROMA_TENANT:-default_tenant}"
CHROMA_DATABASE="${CHROMA_DATABASE:-brainrot_patent}"
CHROMA_COLLECTION="${CHROMA_COLLECTION:-kipris_patents_v2}"
INIT_BATCH_SIZE="${INIT_BATCH_SIZE:-100}"
DUMP_FILE="${DUMP_FILE:-${DUMPS_DIR}/kipris_patents_v2.parquet}"

# pydeps에는 이 스크립트 전용 Python 의존성을 설치합니다.
# repo 전체 Python 환경을 건드리지 않기 위한 로컬 vendor 폴더입니다.
mkdir -p "${PYDEPS_DIR}"

# dump 파일이 없으면 restore할 수 없으므로 즉시 종료합니다.
if [ ! -f "${DUMP_FILE}" ]; then
  echo "Parquet dump not found: ${DUMP_FILE}" >&2
  echo "Create it first with ./migration/dump_database.sh" >&2
  exit 1
fi

# pyarrow가 없으면 migration/requirements.txt 기준으로 pydeps에 설치합니다.
if ! PYTHONPATH="${PYDEPS_DIR}" python3 -c "import pyarrow, pyarrow.parquet" >/dev/null 2>&1; then
  python3 -m pip install --target "${PYDEPS_DIR}" -r "${SCRIPT_DIR}/requirements.txt"
fi

# 실제 restore 로직은 Python 스크립트에 위임합니다.
cd "${REPO_ROOT}"
PYTHONPATH="${PYDEPS_DIR}" python3 "${SCRIPT_DIR}/init_database.py" \
  --input "${DUMP_FILE}" \
  --chroma-url "${CHROMA_URL}" \
  --tenant "${CHROMA_TENANT}" \
  --database "${CHROMA_DATABASE}" \
  --collection "${CHROMA_COLLECTION}" \
  --batch-size "${INIT_BATCH_SIZE}"
