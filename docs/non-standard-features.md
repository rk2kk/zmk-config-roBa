# ZMK 標準外の機能一覧(外部モジュール / フォーク由来)

このリポジトリの keymap / shield / Kconfig が読み込んでいる機能のうち、
**ZMK 本家(zmkfirmware/zmk)に存在しないもの**の一覧です。
「標準かどうか」は 2026-11 時点の GitHub 上の zmkfirmware/zmk の実物
(behaviors バインディング一覧・input processors・コード検索)で照合しています。

- 定義ファイル: [config/roBa.keymap](../config/roBa.keymap), [config/west.yml](../config/west.yml)
- 各ハーフの設定: [boards/shields/roBa/](../boards/shields/roBa)

> **前提**: ビルドは ZMK 本家ではなく **cormoran/zmk フォーク (`main+dya`)** で行います。
> このフォーク経由で入る拡張(特に ZMK Studio の RPC 拡張)も「標準外」に含めて扱います。
> 逆に、本家 main には最近入った機能(input processors / key-toggle / macro パラメータ版
> など)も使っていますが、そちらはこの文書では「標準」として分類しています。

---

## 1. ビルド基盤(フォーク)

| プロジェクト | revision | 備考 |
|---|---|---|
| cormoran/zmk | `main+dya` | ZMK 本家のフォーク。Studio RPC 拡張(custom subsystem)や split relay などが入る |
| cormoran/zephyr | `v4.1.0+zmk-fixes+nrf-half-duplex-uart` | Zephyr もフォーク(nRF 半二重 UART 修正含む) |
| cormoran/zmk-west-commands | (default=main) | west ビルドコマンド拡張 |

注意: どちらも**ブランチ追従**のため、同じこのリポジトリのコミットでもビルド結果が
実行日で変わる可能性があります(CI の action を SHA ピン留めした話と同じ議論)。

---

## 2. keymap で読み込む標準外 include / ビヘイビアー

| 読み込み / 使用シンボル | 提供モジュール ([config/west.yml](../config/west.yml)) | 役割 |
|---|---|---|
| `#include <mouse-gesture.dtsi>` | `zmk-mouse-gesture` (kot149) | マウスジェスチャ |
| `#include <scroll-snap.dtsi>`, `&zip_scroll_snap`(プロパティ設定) | `zmk-scroll-snap` (kot149) | スクロールスナップ |
| `#include <dt-bindings/zmk/trackball_gestures.h>`, `#include <behaviors/gesture.dtsi>`, `CONFIG_ZMK_TRACKBALL_GESTURES_*` | `zmk-trackball-gestures-module` (minhe7735) | トラックボールジェスチャ |
| `#include <behaviors/runtime_macro.dtsi>`, `CONFIG_ZMK_RUNTIME_MACRO*` | `zmk-feature-runtime-macro` (cormoran) | ZMK Studio から実行時にマクロを定義 |
| `#include <behaviors/runtime-input-processor.dtsi>`, `&mouse_runtime_input_processor`, `CONFIG_ZMK_RUNTIME_INPUT_PROCESSOR*` | `zmk-module-runtime-input-processor` (cormoran) | マウスレイヤー用ランタイム入力処理 |
| `#include <input/processors/report_rate_limit.dtsi>`, `&zip_report_rate_limit 15` | `zmk-input-processor-report-rate-limit` (badjeff) | 入力レポートのレート制限 |
| `zmk,input-processor-keybind` 互換ノード `&zip_arrows` `&zip_volume` `&zip_alt_tab` `&zip_ctrl_tab` | `zmk-input-processor-keybind` (zettaface) | トラックボールの動き→キー入力(+タップ/リピート制御) |
| `zmk,behavior-smart-toggle` 互換ビヘイビアー `&alttab` `&altshifttab` `&ctrltab` `&ctrlshifttab`(`ignored-key-positions` プロパティ含む) | `zmk-smart-toggle` (caksoylar) | 長押し保留+何も押さずに離すと即時発火 |
| シールド `rgbled_adapter`(= [build.yaml](../build.yaml) で全ビルド対象に付与), `CONFIG_RGBLED_WIDGET_*` | `zmk-rgbled-widget` (caksoylar) | 状態通知 LED |
| `CONFIG_ZMK_DONGLE_DISPLAY_*`([roBa_dongle_display.conf](../boards/shields/roBa/roBa_dongle_display.conf)) | `zmk-dongle-display` (englmaxi) | ドングル OLED 表示 |
| Raytac ドングル用ボードサポート([roBa_dongle_raytac](../boards/shields/roBa/roBa_dongle_raytac.conf)) | `zmk-component-raytac-dongle` (venator) | Raytac MDBT50Q-RX 対応 |
| `CONFIG_PROSPECTOR_MAX_LAYERS`(現在はコメントアウト) | `prospector-zmk-module` (t-ogura) | レイヤー数拡張 |

参考: [config/roBa.keymap](../config/roBa.keymap) の `td_ZenkakuHankaku` には
コメントアウトされた `zmk,behavior-eager-tap-dance` が残っています(提供元未確認・未使用)。

## 3. cormoran フォーク/モジュール由来の機能(Kconfig)

[roBa_R_central.conf](../boards/shields/roBa/roBa_R_central.conf) などで有効化している
Studio/RPC 拡張系はすべて cormoran 製モジュール(or fork 本体)由来です。

| CONFIG | モジュール | 現状 | 役割 |
|---|---|---|---|
| `CONFIG_ZMK_PMW3610*` / `CONFIG_ZMK_PMW3610_STUDIO_RPC` / `CONFIG_ZMK_PMW3610_CUSTOM_SETTINGS` | `zmk-driver-pmw3610-with-custom-studio-rpc` | ドライバのみ有効(RPC は無効) | PMW3610 トラックボールドライバ + Studio 連携 |
| `CONFIG_ZMK_OS_DETECTION*` | `zmk-feature-os-detection` | 有効 | 接続ホストの OS 検出 |
| `CONFIG_ZMK_DEFAULT_LAYER*` | `zmk-feature-default-layer`(revision `codex/custom-rpc-rewrite`) | 有効 | デフォルトレイヤーの RPC 管理 |
| `CONFIG_ZMK_SETTINGS_RPC*` | `zmk-module-settings-rpc` | 有効 | 設定の RPC 経由読み書き |
| `CONFIG_ZMK_CUSTOM_SETTINGS*` / `CONFIG_ZMK_CUSTOM_SETTINGS_SPLIT_RPC_RELAY` | `zmk-feature-custom-settings` | 有効 | カスタム設定 + split 転送 |
| `CONFIG_ZMK_BLE_MANAGEMENT*` | `zmk-module-ble-management` | 有効 | BLE ペアリング管理 RPC |
| `CONFIG_ZMK_INPUT_STREAM_FEATURE*` | `zmk-feature-input-stream` | 有効 | 入力ストリーム RPC |
| `CONFIG_ZMK_PHYSICAL_LAYOUTS_FEATURE*` | `zmk-feature-module-physical-layout` | 有効 | 物理レイアウト RPC ※本家にも `zmk,physical-layout` があるため混同注意 |
| `CONFIG_ZMK_RUNTIME_COMBO*` | `zmk-feature-runtime-combo` | 有効 | Studio からコンボを実行時定義 |
| `CONFIG_ZMK_RUNTIME_MACRO*` | `zmk-feature-runtime-macro` | 有効 | Studio からマクロを実行時定義 |
| `CONFIG_ZMK_RUNTIME_SENSOR_ROTATE*` | `zmk-behavior-runtime-sensor-rotate` | 有効 | センサー回転ビヘイビアーの実行時定義 |
| `CONFIG_ZMK_FAST_KEYMAP*`, `CONFIG_ZMK_BEHAVIOR_LOCAL_ID_TYPE_CRC16` | `zmk-feature-fast-keymap` | 有効 | キーマップ差分更新/ローカル ID |
| `CONFIG_ZMK_DEVICE_INFO*` | `zmk-feature-device-info` | 有効 | デバイス情報 RPC |
| `CONFIG_ZMK_KSCAN_DIAGNOSTICS*` | `zmk-feature-kscan-diagnostics` | 有効 | kscan 診断 RPC |
| `CONFIG_ZMK_WATCHDOG*` | `zmk-feature-watchdog` | 無効(コメント) | ウォッチドッグ |
| `CONFIG_ZMK_BATTERY_HISTORY*` | `zmk-module-battery-history` | 無効(コメント) | 電池履歴 RPC |
| `CONFIG_ZMK_STUDIO_RPC_*`(バッファ等の調整), `CONFIG_ZMK_SPLIT_RELAY_EVENT*` | cormoran/zmk fork 本体(Studio RPC 拡張) | 有効 | Studio RPC のバッファ/転送 |
| — (開発ビルド用) | `zmk-module-devtool`, `zmk-feature-studio-rpc-perf`, `zmk-feature-zephyr-setting-expose` | 未使用 | 開発/診断用 |
| — | `zmk-driver-animation`, `zmk-driver-ext-power-transient`, `zmk-feature-charge-indicator` | 未確認(現状 .conf に利用箇所なし) | LED アニメーション / 電源制御 / 充電表示 |

`CONFIG_ZMK_STATUS_ADVERTISEMENT*`([roBa_R_central.conf](../boards/shields/roBa/roBa_R_central.conf))は
無効化済みで、提供元も本家確認取れていないため要確認です。

## 4. roBa.keymap で定義している自作ビヘイビアー / マクロ

[config/roBa.keymap](../config/roBa.keymap) 上で定義しているノードのうち、
**標準外の部品に依存するもの**に注記を付けています(それ以外は本家標準の
compatible の上に多重化しただけの自作定義です)。

| ノード | ベース compatible | 依存 | 備考 |
|---|---|---|---|
| `&alttab` `&altshifttab` `&ctrltab` `&ctrlshifttab` | `zmk,behavior-smart-toggle` | **zmk-smart-toggle (caksoylar) 必須** | メモリ (例 `ignored-key-positions`) は同モジュール仕様 |
| `&zip_arrows` `&zip_volume` `&zip_alt_tab` `&zip_ctrl_tab` | `zmk,input-processor-keybind` | **zmk-input-processor-keybind (zettaface) 必須** | `track-remainders` `tick` `wait-ms` `tap-ms` は同モジュールのプロパティ |
| `&zip_scroll_snap` 設定ブロック | (kot149 scroll-snap) | **zmk-scroll-snap 必須** | |
| `&mouse_runtime_input_processor` | (cormoran runtime-input-processor) | **zmk-module-runtime-input-processor 必須** | |
| `&exit_AML` `&kp_exit_AML` `&mod_exit_AML` `&mkp_exit_AML` `&mo_exit_AML` `&lt_exit_AML*` `&mt_exit_AML*` | `zmk,behavior-macro(-*-param)` / `hold-tap` | 本家標準 | auto mouse layer を抜ける系。`macro_param_1to1/2to1` は本家マクロの機能 |
| `&etd` `&mokp` `&kp_to` `&to_kp` `&zoom_in` `&zoom_out` `&alt_tab` `&windows_sleep` `&screenshot_save` `&mkp_with_mod` | `zmk,behavior-macro(-*-param)` | 本家標準 | |
| `&td_colon` `&td_q_escape` `&td_ZenkakuHankaku` `&td_ZenkakuHankaku_exit_AML` `&td_alt_f4` `&td_bt_clear(_all)` `&td_copy_paste` `&td_reset` `&td_rclick_close_tab` | `zmk,behavior-tap-dance` | 本家標準 | |
| `&tog_on` `&tog_off` `&kt_on` `&kt_off` | `zmk,behavior-toggle-layer` / `zmk,behavior-key-toggle`(`toggle-mode` 付き) | 本家標準(2026-11 時点の main で確認) | `toggle-mode` は本家 binding に存在 |
| `&sl_250` | `zmk,behavior-sticky-key`(内部で `&mo`) | 本家標準 | |
| `&screenshot_copy` `&mod_morph_*` | `zmk,behavior-mod-morph` | 本家標準 | |
| `&scroll_up_down` `&encoder_zoom` `&encoder_volume` | `zmk,behavior-sensor-rotate` | 本家標準 | |
| `&reset_bootloader` | `zmk,behavior-hold-tap` | 本家標準 | |
| `&wheel_x_scaler` | `zmk,input-processor-scaler` | 本家標準(入力プロセッサ枠組み) | |

本家で確認済みの標準部品(参考): `zmk,behavior-macro-one-param/two-param`,
`zmk,behavior-key-toggle`, `zmk,behavior-toggle-layer`(`toggle-mode`),
`zmk,input-listener`, `zmk,keymap-sensors`, `zmk,physical-layout`, `zmk,input-split`,
`zmk,kscan-mock/gpio-matrix`, input processors(`zip_temp_layer` `zip_xy_scaler` は本家実在確認)、
`#include <behaviors.dtsi>` など。`zip_xy_transform` / `zip_xy_to_scroll_mapper` /
`input/processors.dtsi` は同枠組みだが提供元は要確認(→ 6 章)。
※本家は更新が活発なため、**tag v0.3 相当の環境では存在しないものがあります**。
このリポジトリの実際の基準は cormoran/zmk `main+dya` です。

## 5. メンテナンス上の注意

- [config/west.yml](../config/west.yml) の revision は `main` 等の**ブランチ指定が多数**です。
  再現性が必要ならコミット SHA へピン留めするのを推奨します(CI の action ピン留めと同じ理由)。
- 標準外モジュールを外す場合の影響箇所:
  - `zmk-smart-toggle` … alt-tab / ctrl-tab 系コンボ・レイヤーの `&alttab` 等 4 ビヘイビアー
  - `zmk-input-processor-keybind` … `&zip_arrows` 等 4 ノード(トラポで矢印/音量/タブ切替)
  - `zmk-scroll-snap` … `&zip_scroll_snap` とスクロール系の体感
  - `zmk-trackball-gestures-module` … `<behaviors/gesture.dtsi>` とトラポジェスチャ
  - `zmk-rgbled-widget` … `rgbled_adapter` シールド(build.yaml の全対象)
  - cormoran の各機能モジュール … ZMK Studio からの編集機能(Runtime* 系のほぼすべて)
- west.yml に載っているが現状のコードから利用が確認できないモジュール:
  `zmk-layout-shift` (kot149), `zmk-listeners` (ssbb — 本家にも `zmk,input-listener` があり、
  当リポジトリの input-listener 利用がどちら準拠かは要確認),
  `zmk-module-devtool` / `zmk-feature-studio-rpc-perf` / `zmk-feature-zephyr-setting-expose`(開発用)。

## 6. 要確認リスト(執筆時点で提供元を断定できなかったもの)

| 拾い込み / シンボル | 見込み |
|---|---|
| `#include <input/processors.dtsi>` と `zip_xy_transform` / `zip_xy_to_scroll_mapper` | 本家 input processor 系(`scaler.dtsi` `code_mapper.dtsi` `temp_layer.dtsi` は本家に実在を確認。transform / xy-to-scroll の aggregator は要確認) |
| `#include <dt-bindings/zmk/input_transform.h>`(INPUT_TRANSFORM_*) | 同上(入力プロセッサ枠組み由来と見られる) |
| `CONFIG_ZMK_STATUS_ADVERTISEMENT*`(無効) | 提供元不明(フォーク or モジュール) |
| `CONFIG_ZMK_SPLIT_RELAY_EVENT*` / `SYSLOG*` 系の relay | custom-settings / フォーク本体のどちらか |
