#!/usr/bin/env bash
set -euo pipefail

# 역할: 현재 실행 중인 ChromaDB collection을 Parquet dump 파일로 내보내는 wrapper입니다.
# 파라미터는 command argument 대신 환경 변수로 받습니다.
# CHROMA_URL: ChromaDB 서버 주소입니다. 기본값은 http://localhost:8001 입니다.
# CHROMA_TENANT: ChromaDB tenant 이름입니다. 기본값은 default_tenant 입니다.
# CHROMA_DATABASE: dump할 database 이름입니다. 기본값은 brainrot_patent 입니다.
# CHROMA_COLLECTION: dump할 collection 이름입니다. 기본값은 kipris_patents_v2 입니다.
# DUMP_BATCH_SIZE: ChromaDB에서 한 번에 읽을 row 수입니다. 기본값은 250 입니다.
# DUMP_FILE: 최종 Parquet dump 파일 경로입니다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYDEPS_DIR="${SCRIPT_DIR}/pydeps"
DUMPS_DIR="${SCRIPT_DIR}/dumps"

CHROMA_URL="${CHROMA_URL:-http://localhost:8001}"
CHROMA_TENANT="${CHROMA_TENANT:-default_tenant}"
CHROMA_DATABASE="${CHROMA_DATABASE:-brainrot_patent}"
CHROMA_COLLECTION="${CHROMA_COLLECTION:-kipris_patents_v2}"
DUMP_BATCH_SIZE="${DUMP_BATCH_SIZE:-250}"
DUMP_FILE="${DUMP_FILE:-${DUMPS_DIR}/kipris_patents_v2.parquet}"
TMP_DUMP_FILE="${DUMP_FILE}.tmp"

# pydeps에는 이 스크립트 전용 Python 의존성을 설치합니다.
# repo 전체 Python 환경을 더럽히지 않기 위한 로컬 vendor 폴더입니다.
mkdir -p "${PYDEPS_DIR}" "${DUMPS_DIR}"

# pyarrow가 없으면 migration/requirements.txt 기준으로 pydeps에 설치합니다.
if ! PYTHONPATH="${PYDEPS_DIR}" python3 -c "import pyarrow, pyarrow.parquet" >/dev/null 2>&1; then
  python3 -m pip install --target "${PYDEPS_DIR}" -r "${SCRIPT_DIR}/requirements.txt"
fi

# 기존 최종 dump는 새 dump가 끝까지 성공할 때까지 보존합니다.
# 새 dump는 .tmp에 만들고 성공했을 때만 최종 파일명으로 교체합니다.
rm -f "${TMP_DUMP_FILE}"

# 실제 dump 로직은 Python 스크립트에 위임합니다.
cd "${REPO_ROOT}"
if ! PYTHONPATH="${PYDEPS_DIR}" python3 "${SCRIPT_DIR}/dump_database.py" \
  --chroma-url "${CHROMA_URL}" \
  --tenant "${CHROMA_TENANT}" \
  --database "${CHROMA_DATABASE}" \
  --collection "${CHROMA_COLLECTION}" \
  --batch-size "${DUMP_BATCH_SIZE}" \
  --output "${TMP_DUMP_FILE}"; then
  echo "Dump did not complete. Existing final dump was preserved." >&2
  echo "Partial dump, if written, remains at: ${TMP_DUMP_FILE}" >&2
  exit 1
fi

# Python dump가 끝까지 성공한 경우에만 .tmp를 최종 parquet 파일로 교체합니다.
mv "${TMP_DUMP_FILE}" "${DUMP_FILE}"

# 마지막으로 Parquet metadata를 읽어 row 수를 출력해 dump가 정상 파일인지 확인합니다.
PYTHONPATH="${PYDEPS_DIR}" python3 -c "import pyarrow.parquet as pq; f=pq.ParquetFile('${DUMP_FILE}'); print({'dump': '${DUMP_FILE}', 'rows': f.metadata.num_rows, 'row_groups': f.metadata.num_row_groups})"
