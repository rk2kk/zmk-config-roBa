#!/usr/bin/env python3
"""ビルド成果物 (uf2) を GitHub Releases に添付する。

- RELEASE_TAG（既定: firmware-latest）の Release を作成または更新する
- 同じ名前のアセットがあれば削除してから再アップロードする
- タグは常にビルドしたコミットを指すように force 更新する

必要な環境変数: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA
"""

from __future__ import annotations

import glob
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
SHA = os.environ["GITHUB_SHA"]
TAG = os.environ.get("RELEASE_TAG", "firmware-latest")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
ART_DIR = sys.argv[1] if len(sys.argv) > 1 else "artifacts"

API = f"https://api.github.com/repos/{REPO}"
UPLOADS = f"https://uploads.github.com/repos/{REPO}"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "zmk-pi-release",
}


def request(method: str, url: str, payload: dict | None = None):
    headers = dict(HEADERS)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def upload(url: str, path: str) -> tuple[int, object]:
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/octet-stream"
    with open(path, "rb") as fh:
        data = fh.read()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def main() -> int:
    files = sorted(glob.glob(os.path.join(ART_DIR, "*.uf2")))
    if not files:
        print(f"エラー: {ART_DIR} に uf2 がありません", file=sys.stderr)
        return 1

    run_url = f"{SERVER}/{REPO}/actions/runs/{RUN_ID}" if RUN_ID else ""
    body = f"commit: `{SHA}`"
    if run_url:
        body += f"\n\nbuild: {run_url}"

    status, release = request("GET", f"{API}/releases/tags/{TAG}")
    if status == 200:
        release_id = release["id"]
        print(f"release 更新: {TAG} (id={release_id})")
        request("PATCH", f"{API}/releases/{release_id}", {"body": body})
    elif status == 404:
        print(f"release 作成: {TAG}")
        status, release = request(
            "POST",
            f"{API}/releases",
            {
                "tag_name": TAG,
                "target_commitish": SHA,
                "name": f"Firmware ({TAG})",
                "body": body,
            },
        )
        if status not in (200, 201):
            print(f"エラー: release 作成に失敗 {status}: {release}", file=sys.stderr)
            return 1
        release_id = release["id"]
    else:
        print(f"エラー: release 取得に失敗 {status}: {release}", file=sys.stderr)
        return 1

    # タグを今回のコミットへ移動（Release はタグ名に紐づく）
    status, _ = request(
        "PATCH", f"{API}/git/refs/tags/{TAG}", {"sha": SHA, "force": True}
    )
    if status not in (200, 201):
        print(f"警告: タグ {TAG} の更新に失敗 ({status})", file=sys.stderr)

    status, assets = request("GET", f"{API}/releases/{release_id}/assets?per_page=100")
    existing = {}
    if status == 200:
        existing = {a["name"]: a["id"] for a in assets}

    for path in files:
        name = os.path.basename(path)
        if name in existing:
            request("DELETE", f"{API}/releases/assets/{existing[name]}")
        url = f"{UPLOADS}/releases/{release_id}/assets?name={urllib.parse.quote(name)}"
        status, result = upload(url, path)
        if status not in (200, 201):
            print(f"エラー: {name} のアップロード失敗 {status}: {result}", file=sys.stderr)
            return 1
        print(f"添付: {name} ({os.path.getsize(path)} bytes)")

    print(f"完了: {SERVER}/{REPO}/releases/tag/{TAG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
