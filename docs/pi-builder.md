# Pi ビルダー運用ガイド

Raspberry Pi 5 のセルフホストランナーで ZMK ファームウェアをビルドし、
公開リポジトリの Release に成果物を配布する構成の説明です。

## 1. 全体構成

| リポジトリ | 公開範囲 | 役割 |
|---|---|---|
| `rk2kk/zmk-config-roBa-private` | private | 設定の正本。ランナーを接続し、push で自動ビルド |
| `rk2kk/zmk-config-roBa` | public | 配布用。ビルド成果物の Release と、private のミラー |

```
[private] push (main / 任意ブランチ)
   │
   ├─ Pi ランナー: docker で ZMK ビルド
   │     └─ artifacts/*.uf2
   │
   ├─ public へミラー (git push)
   │
   └─ public の Release に uf2 を添付
         main        → firmware-latest
         その他ブランチ → firmware-<ブランチ名>
```

ランナーは private リポジトリにのみ登録されています。公開リポジトリ側から
セルフホストランナーのジョブが実行されることはありません。

## 2. ビルドの流れ

`.github/workflows/build-pi.yml`

1. **Checkout** — `fetch-depth: 0`（ミラー時に履歴が必要）
2. **Resolve release tag** — `main` は `firmware-latest`、それ以外は `firmware-<branch>`
3. **Check release token** — Secret 未設定なら以降の添付・ミラーをスキップ
4. **Build** — `.github/scripts/build-pi.sh` が docker を起動
5. **Mirror** — ビルドしたコミットを公開リポジトリの同名ブランチへ push
6. **Attach** — `.github/scripts/upload-release.py` が uf2 を Release に添付

ミラーを Release より先に行うのは、Release のタグが公開リポジトリ側に
存在するコミットを指す必要があるためです。

### keymap 描画とミラー

`Draw Keymap` は private リポジトリで実行し、生成物を自動コミットします。
このコミットは `GITHUB_TOKEN` による push のため、他のワークフロー
（`build-pi`）を起動しません。そこで `mirror-public.yml` が
「Draw Keymap 完了時」と「30分ごと」に main を公開リポジトリへミラーします。

公開リポジトリ側の `Draw Keymap` と `Build firmware (Pi)` は無効化しています
（ミラーされたコピーでの二重実行・コミット分岐を防ぐため）。

### 実行条件

- `push`（全ブランチ）、`workflow_dispatch`
- ジョブ先頭の `if: github.repository == 'rk2kk/zmk-config-roBa-private'` により、
  公開リポジトリへミラーされたコピーでは実行されません（スキップ扱い）

## 3. ランナー（Raspberry Pi 5）

- ユーザー: 専用ユーザー（docker グループ所属）
- 設置先: `~/actions-runner`
- サービス: `gh-runner.service`（systemd user、linger 有効）
- ラベル: `self-hosted, linux, arm64, zmk, pi5`
- ビルドキャッシュ: `~/zmk-cache`（west ワークスペース兼ビルドディレクトリ）

### ユニットファイル

`~/.config/systemd/user/gh-runner.service`

```ini
[Unit]
Description=GitHub Actions runner (rk2kk/zmk-config-roBa-private)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/actions-runner
ExecStart=%h/actions-runner/run.sh
Restart=always
RestartSec=10
KillSignal=SIGTERM
TimeoutStopSec=300

[Install]
WantedBy=default.target
```

`KillMode=process` は使いません。子プロセスの `Runner.Listener` に
シグナルが届かず、停止が5分待ちになるためです。

### 操作

```sh
systemctl --user status gh-runner.service
systemctl --user restart gh-runner.service
journalctl --user -u gh-runner.service -n 50 --no-pager
```

キャッシュを作り直す場合（初回と同じく数分かかります）:

```sh
rm -rf ~/zmk-cache
```

## 4. ビルドスクリプト

### `build-pi.sh`（ホスト側）

- `~/zmk-cache` を `/ci`、リポジトリを `/src:ro`、成果物を `/artifacts` にマウント
- コンテナは `-u $(id -u):$(id -g) -e HOME=/tmp` で実行
  （root 所有ファイルを作らせないため）
- 実行前に `artifacts/` を消去（古い uf2 の誤アップロード防止）

### `build-pi-container.sh`（コンテナ側）

- `config/` と `build.yaml` を `/ci` にコピーして `west init -l config`
- `west update --narrow -o=--depth=1` → `west zephyr-export`
- `build.yaml` の `include` を python3 + PyYAML で読み、全ターゲットを順にビルド
- ターゲット名は `artifact-name`、無ければ `<shield>-<board>` をサニタイズ
- 区切り文字はタブではなく `0x1f`（タブは空フィールドが潰れるため）

主なビルド引数:

```
-DZMK_CONFIG=/ci/config
-DZMK_EXTRA_MODULES=/src
-DSHIELD="<shield>"
```

## 5. Secret

| 名前 | 登録先 | 内容 |
|---|---|---|
| `PUBLIC_REPO_TOKEN` | `zmk-config-roBa-private` | 公開リポジトリ限定の fine-grained PAT（Contents: Read and write） |

- 期限切れ時は再発行し、Secret を更新する
- `Workflows` 権限は不要（付与しなくてもタグ更新は警告のみで継続）
- 未設定でもビルドは成功し、添付とミラーだけがスキップされる

## 6. 運用手順

### 手動ビルド

```sh
gh workflow run build-pi.yml -R rk2kk/zmk-config-roBa-private --ref main
gh run watch -R rk2kk/zmk-config-roBa-private
```

### ブランチで試す

```sh
git push private <branch>
```

- ビルド成功後、公開リポジトリの同名ブランチへミラーされる
- 成果物は `firmware-<branch>` という Release に添付される

### 失敗したジョブの再実行

```sh
gh run rerun <run-id> -R rk2kk/zmk-config-roBa-private
```

## 7. トラブルシューティング

| 症状 | 原因 / 対処 |
|---|---|
| `Invalid SHIELD` | `-DZMK_EXTRA_MODULES` 不足。`build-pi-container.sh` を確認 |
| `recursive 'source' of 'Kconfig.zephyr'` | リポジトリを west のトップに置いている。`/src` と `/ci` を分離する |
| ターゲット名が空 / 引数がずれる | TSV の区切りにタブを使っている。`0x1f` を使う |
| アップロードが 401 | トークンが無効・期限切れ・再生成済み。Secret を更新 |
| アップロードが 403 | `Contents: Read and write` が無い |
| `tag_name is not a valid tag` | ミラー前に Release を作っている。順序をミラー→添付にする |
| `systemctl stop` が5分待ち | ユニットの `KillMode=process` を外す |

## 8. セキュリティ上の注意

- 公開リポジトリにセルフホストランナーを登録しない（本構成の前提）
- 公開リポジトリの既定ワークフロー権限は `read`、PR 実行は不可のまま
- Actions はコミット SHA でピン留めする
- `PUBLIC_REPO_TOKEN` は公開リポジトリのみ・Contents のみに限定する
- 旧セルフホスト実行のログには Pi のユーザー名とパスが残るため、
  役目が終わった run は削除する
