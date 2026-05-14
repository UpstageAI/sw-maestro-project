#!/usr/bin/env bash
set -euo pipefail

SUBTREE_DIR=".subtrees"
GLOBAL_CONFIG="global.config"

# ---------- 전역 설정 읽기 ----------
if [[ -f "$GLOBAL_CONFIG" ]]; then
  echo "🌐 전역 설정 파일을 로드합니다: $GLOBAL_CONFIG"
  while IFS='=' read -r key val; do
    [[ -z "${key// }" ]] && continue
    [[ "${key#\#}" != "$key" ]] && continue
    key="$(echo "$key" | xargs)"
    val="$(echo "${val:-}" | xargs)"
    case "$key" in
      ENTIRE_GIT_GROUP) ENTIRE_GIT_GROUP="$val" ;;
      ENTIRE_GIT_NAME) ENTIRE_GIT_NAME="$val" ;;
      DEFAULT_BRANCH) DEFAULT_BRANCH="$val" ;;
      AUTO_PUSH) AUTO_PUSH="$val" ;;
    esac
  done < "$GLOBAL_CONFIG"
else
  echo "⚠️  전역 설정 파일($GLOBAL_CONFIG)을 찾을 수 없습니다. global.config을 추가하고 재실행하세요."
  exit 1
fi

# ---------- 유틸 ----------
normalize_prefix() {
  local p="$1"
  echo "${p#./}"
}

has_head() {
  git rev-parse --verify HEAD >/dev/null 2>&1
}

ensure_initial_commit() {
  if ! has_head; then
    echo "ℹ️  첫 커밋이 없어 빈 커밋을 생성합니다."
    git commit --allow-empty -m "[$ENTIRE_GIT_NAME] chore: initial commit"
  fi
}

ensure_clean_worktree() {
  if has_head; then
    if ! git diff-index --quiet HEAD --; then
      echo "❌ 워킹트리에 변경사항이 있습니다. 커밋하거나 스태시 후 재실행하세요."
      exit 1
    fi
  else
    if [[ -n "$(git status --porcelain)" ]]; then
      echo "❌ 워킹트리에 변경사항이 있습니다. 커밋하거나 스태시 후 재실행하세요."
      exit 1
    fi
  fi
}

derive_remote_name() {
  local url="$1"
  local prefix="$2"
  # URL에서 basename(.git 제거) 추출
  local base="${url##*/}"
  base="${base%.git}"
  if [[ -n "$base" ]]; then
    echo "$base"
  else
    echo "$prefix"
  fi
}

# ---------- 메인 ----------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ 여기는 git 레포가 아닙니다. 'git init'을 실행합니다."
  git init
  git branch -M main                                                               
  git remote add origin $ENTIRE_GIT_GROUP/$ENTIRE_GIT_NAME.git
fi

if [[ ! -d "$SUBTREE_DIR" ]]; then
  echo "❌ '$SUBTREE_DIR' 디렉터리가 없습니다. 먼저 생성하고 .config 파일을 넣어주세요."
  exit 1
fi

ensure_initial_commit
ensure_clean_worktree

shopt -s nullglob
CONFIGS=( $(find "$SUBTREE_DIR" -type f -name "*.config") )
shopt -u nullglob

if (( ${#CONFIGS[@]} == 0 )); then
  echo "ℹ️  '$SUBTREE_DIR' 안에 .config 파일이 없습니다. 작업 없이 종료합니다."
  exit 0
fi

echo "📦 총 ${#CONFIGS[@]}개의 config를 처리합니다."
echo

for cfg in "${CONFIGS[@]}"; do
  echo "=============================="
  echo "▶ 처리 파일: $cfg"

  # 기본값 초기화
  REPO_URL=""
  BRANCH=""
  PREFIX=""
  REMOTE_NAME=""
  SQUASH="false"
  MODE="auto"
  PUSH_BRANCH=""

  # 안전하게 읽기 (주석/공백 무시)
  while IFS='=' read -r key val; do
    # 주석/빈줄 스킵
    [[ -z "${key// }" ]] && continue
    [[ "${key#\#}" != "$key" ]] && continue
    key="$(echo "$key" | xargs)"
    val="$(echo "${val:-}" | xargs)"
    case "$key" in
      REPO_URL) REPO_URL="$val" ;;
      BRANCH) BRANCH="$val" ;;
      PREFIX) PREFIX="$val" ;;
      REMOTE_NAME) REMOTE_NAME="$val" ;;
      SQUASH) SQUASH="$val" ;;
      MODE) MODE="$val" ;;
      PUSH_BRANCH) PUSH_BRANCH="$val" ;;
    esac
  done < "$cfg"

  # 필수값 검증
  if [[ -z "$REPO_URL" || -z "$BRANCH" || -z "$PREFIX" ]]; then
    echo "❌ REPO_URL/BRANCH/PREFIX 중 누락이 있습니다. 스킵합니다."
    echo
    continue
  fi

  PREFIX="$(normalize_prefix "$PREFIX")"
  if [[ -z "$REMOTE_NAME" ]]; then
    REMOTE_NAME="$(derive_remote_name "$REPO_URL" "$PREFIX")"
  fi
  SQUASH_ARG=""
  if [[ "${SQUASH,,}" == "true" || "${SQUASH,,}" == "yes" || "${SQUASH}" == "1" ]]; then
    SQUASH_ARG="--squash"
  fi
  if [[ -z "$PUSH_BRANCH" ]]; then
    PUSH_BRANCH="$BRANCH"
  fi

  echo "  ▸ REPO_URL   = $REPO_URL"
  echo "  ▸ BRANCH     = $BRANCH"
  echo "  ▸ PREFIX     = $PREFIX"
  echo "  ▸ REMOTE     = $REMOTE_NAME"
  echo "  ▸ SQUASH     = ${SQUASH_ARG:-<none>}"
  echo "  ▸ MODE       = $MODE"
  [[ "$MODE" == "push" ]] && echo "  ▸ PUSH_BRANCH= $PUSH_BRANCH"
  echo

  # 워킹트리 깨끗한지 확인
  ensure_clean_worktree

  # remote 등록
  if git remote | grep -qx "$REMOTE_NAME"; then
    echo "✔️  remote '$REMOTE_NAME' 이미 존재"
  else
    git remote add "$REMOTE_NAME" "$REPO_URL"
    echo "✔️  remote '$REMOTE_NAME' 추가: $REPO_URL"
  fi

  # fetch
  git fetch "$REMOTE_NAME" "$BRANCH"
  echo "✔️  fetched: $REMOTE_NAME/$BRANCH"

  # 모드 결정
  case "$MODE" in
    auto)
      if [[ -d "$PREFIX" ]]; then
        echo "🔄 auto 모드: '$PREFIX' 존재 → pull 실행"
        ensure_clean_worktree
        git subtree pull --prefix="$PREFIX" "$REMOTE_NAME" "$BRANCH" ${SQUASH_ARG:+$SQUASH_ARG}
      else
        echo "🧱 auto 모드: '$PREFIX' 없음 → add 실행"
        ensure_clean_worktree
        git subtree add  --prefix="$PREFIX" "$REMOTE_NAME" "$BRANCH" ${SQUASH_ARG:+$SQUASH_ARG}
      fi
      ;;
    add)
      echo "➕ add 모드 실행"
      ensure_clean_worktree
      git subtree add  --prefix="$PREFIX" "$REMOTE_NAME" "$BRANCH" ${SQUASH_ARG:+$SQUASH_ARG}
      ;;
    pull)
      echo "🔄 pull 모드 실행"
      ensure_clean_worktree
      git subtree pull --prefix="$PREFIX" "$REMOTE_NAME" "$BRANCH" ${SQUASH_ARG:+$SQUASH_ARG}
      ;;
    push)
      echo "📤 push 모드 실행 (-> $REMOTE_NAME $PUSH_BRANCH)"
      ensure_clean_worktree
      git subtree push --prefix="$PREFIX" "$REMOTE_NAME" "$PUSH_BRANCH"
      ;;
    *)
      echo "❌ 알 수 없는 MODE='$MODE' 입니다. (auto|add|pull|push 중 선택)"
      ;;
  esac

  echo
done

echo "✅ 모든 .config 처리 완료!"

# ---------- 전체 Push ----------
if [[ "${AUTO_PUSH,,}" =~ ^(true|yes|1)$ ]]; then
  git push -u origin "${DEFAULT_BRANCH:-main}"
  echo "✅ origin(${DEFAULT_BRANCH})으로 push 완료"
else
  echo "ℹ️  AUTO_PUSH=false → push 생략됨"
fi

echo "🎉 모든 Subtree 처리 완료!"
