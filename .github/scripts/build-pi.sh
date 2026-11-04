#!/usr/bin/env bash
# ホスト側: ZMK コンテナを起動して build-pi-container.sh を実行する。
# 依存: docker（ランナーユーザーが docker グループに入っていること）
set -euo pipefail

IMG="${ZMK_IMAGE:-zmkfirmware/zmk-build-arm:4.1-branch}"
WS="${GITHUB_WORKSPACE:-$(pwd)}"
CACHE="${ZMK_CACHE_DIR:-$HOME/zmk-cache}"

# 前回実行の成果物が残っていると、失敗時でも古い uf2 を上げてしまう
rm -rf "$WS/artifacts"
mkdir -p "$CACHE" "$WS/artifacts"

echo "image : $IMG"
echo "cache : $CACHE"

docker run --rm \
    --name "zmk-build-$$" \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -v "$CACHE:/ci" \
    -v "$WS:/src:ro" \
    -v "$WS/artifacts:/artifacts" \
    -w /ci \
    "$IMG" \
    bash /src/.github/scripts/build-pi-container.sh

echo "== artifacts =="
ls -l "$WS/artifacts"
