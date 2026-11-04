#!/usr/bin/env bash
# コンテナ側: /src（リポジトリ, 読み取り専用）から /ci の作業領域で全ターゲットをビルドする。
# 公式 zmkfirmware/zmk の build-user-config.yml と同じ手順を、複数ターゲット一括版にしたもの。
set -euo pipefail

SRC=/src
CI=/ci
ART=/artifacts
SEP=$'\x1f'

mkdir -p "$CI" "$ART"

# west のマニフェストは config/ 配下（self: path: config）
rm -rf "$CI/config"
cp -a "$SRC/config" "$CI/config"
cp -a "$SRC/build.yaml" "$CI/build.yaml"

cd "$CI"

if [ ! -d .west ]; then
    echo "== west init =="
    west init -l "$CI/config"
fi

echo "== west update ($(date +%T)) =="
west update --narrow -o=--depth=1

echo "== zephyr export =="
west zephyr-export

echo "== ターゲット一覧 =="
python3 - "$CI/build.yaml" <<'PY' > /tmp/targets.tsv
import re
import sys

import yaml

SEP = chr(0x1F)


def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


with open(sys.argv[1], encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

for item in data.get("include") or []:
    board = item.get("board") or ""
    if not board:
        continue
    shield = item.get("shield") or ""
    snippet = item.get("snippet") or ""
    cmake = item.get("cmake-args") or ""
    name = item.get("artifact-name") or (
        f"{shield}-{board}" if shield else board
    )
    name = sanitize(name)
    print(SEP.join([board, shield, snippet, cmake, name]))
PY
cat /tmp/targets.tsv | tr '\037' '|'

failed=0
while IFS="$SEP" read -r board shield snippet cmake name; do
    [ -z "$board" ] && continue
    echo ""
    echo "==== build: $name ($board / $shield) ===="
    args=(-s zmk/app -d "$CI/builds/$name" -b "$board")
    if [ -n "$snippet" ]; then
        args+=(-S "$snippet")
    fi
    cmake_args=(-DZMK_CONFIG="$CI/config" "-DZMK_EXTRA_MODULES=$SRC")
    if [ -n "$shield" ]; then
        cmake_args+=("-DSHIELD=$shield")
    fi
    if [ -n "$cmake" ]; then
        # shellcheck disable=SC2206
        cmake_args+=($cmake)
    fi
    if west build "${args[@]}" -- "${cmake_args[@]}"; then
        cp "$CI/builds/$name/zephyr/zmk.uf2" "$ART/$name.uf2"
        echo "OK: $name"
    else
        echo "FAILED: $name"
        failed=1
    fi
done < /tmp/targets.tsv

echo ""
echo "== artifacts =="
ls -l "$ART"

exit "$failed"
