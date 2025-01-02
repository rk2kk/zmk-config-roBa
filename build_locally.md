# roBa ローカルビルド手順
roBaのファームウェアをGitHub Actionsを使わずローカルPCでビルドするための手順です。

コンテナや一部の中間ファイルを使いまわすことが可能になりビルド時間が短縮されることに加え、ビルド結果のダウンロード・解凍の手間を省くことができます。

- [roBa ローカルビルド手順](#roba-ローカルビルド手順)
	- [環境構築](#環境構築)
		- [事前準備](#事前準備)
		- [Dockerコンテナの用意](#dockerコンテナの用意)
			- [zmk-configのvolume作成](#zmk-configのvolume作成)
			- [ZMKのコンテナ作成](#zmkのコンテナ作成)
		- [Westの初期化](#westの初期化)
	- [ビルド](#ビルド)
		- [ビルドスクリプト](#ビルドスクリプト)


## 環境構築
[ZMK公式ドキュメント](https://zmk.dev/docs/development/local-toolchain/setup/container) に書かれている内容の通りだが、一応日本語で書き写しておく。

### 事前準備
- Docker Desktopをインストールする
- VSCodeをインストールする
- VSCodeのRemote Containersエクステンションをインストールする

### Dockerコンテナの用意
zmk-configのvolumeとZMKのコンテナを作成する。

#### zmk-configのvolume作成
以下のコマンドを実行する。`/absolute/path/to/zmk-config/`は各自のzmk-configへのパスに置き換えること。
```sh
docker volume create --driver local -o o=bind -o type=none -o device="/absolute/path/to/zmk-config/" zmk-config
```

#### ZMKのコンテナ作成
ZMKのリポジトリをクローンし、VSCodeで開く。以下のコマンドを実行する。
```sh
git clone https://github.com/zmkfirmware/zmk.git
code zmk
```

ZMKリポジトリ内にコンテナの設定が書かれているので、そのコンテナをVSCodeで開く。

### Westの初期化
※以降のコマンドは全てコンテナ内で行うこと。

以下のコマンドを順に実行する。
```sh
west init -l app
west update
```

## ビルド
以下のコマンドを実行
```sh
# 右手用
west build -s /workspaces/zmk/app -d build/right -b seeeduino_xiao_ble -- -DZMK_CONFIG=/workspaces/zmk-config/config -DSHIELD=roBa_R -DZMK_EXTRA_MODULES=/workspaces/zmk-config
# 左手用
west build -s /workspaces/zmk/app -d build/left -b seeeduino_xiao_ble -- -DZMK_CONFIG=/workspaces/zmk-config/config -DSHIELD=roBa_L -DZMK_EXTRA_MODULES=/workspaces/zmk-config
# リセット用
west build -s /workspaces/zmk/app -d build/reset -b seeeduino_xiao_ble -- -DZMK_CONFIG=/workspaces/zmk-config/config -DSHIELD=settings_reset -DZMK_EXTRA_MODULES=/workspaces/zmk-config
```

2回目以降のビルドでは、`-b`以降のオプションを省略してビルドを高速化できる。
```sh
# 左手用
west build -s /workspaces/zmk/app -d build/right
# 右手用
west build -s /workspaces/zmk/app -d build/left
# リセット用
west build -s /workspaces/zmk/app -d build/reset
```

### ビルドスクリプト
このリポジトリの`build.sh`は上記3つのビルドを同時並行で行い、結果を`zmk-config-roBa/build`に保存するスクリプトである。
以下のコマンドで実行できる。
```sh
# 初回ビルド
./build.sh -f

# 2回目以降の省略ビルド
./build.sh
```