# roBa USB 接続トラブル診断ログ (2026-10-22 時点)

## 目的
roBa R 側 (`roBa_R_central`, xiao_ble/zmk) が **Windows で USB 列挙に失敗 (Code 10, 子デバイス 0)** し、
**DYA Studio (studio.dya.cormoran.works) にも接続できない**問題の根本原因特定。
USB に依存しない **BLE NUS (Nordic UART Service) ログ取得** を診断経路として採用。

---

## 診断の前提

- ZMK: cormoran fork (`zmk@main+dya`), Zephyr: `v4.1.0+zmk-fixes+nrf-half-duplex-uart`
- ビルド: GitHub Actions `zmkfirmware/zmk/.github/workflows/build-user-config.yml@main`
- BLE 経由のログバックエンド: Zephyr `LOG_BACKEND_BLE` (NUS UUID `6e400001-…`, TX char `6e400003-…`)
  - nRF Toolbox / nRF UART 2.0 等で受信可能

---

## 経過と発見

### 1. diag2 (`f6647b6`) 〜 diag3 (`e5c611e`): NUS がファームに現れない

- `roBa_R_central.conf` に以下を追記して焼込み済みのはずだった:
  ```
  CONFIG_LOG_BACKEND_BLE=y
  CONFIG_LOG_PROCESS_THREAD_STACK_SIZE=3072
  CONFIG_BT_L2CAP_TX_MTU=247
  ```
- しかし スキャン→GATT 列挙 の繰り返しで **NUS サービスが現れない**
  (Studio Service `00000000-0196-6107-…` は見える)
- winrt の `get_gatt_services_with_cache_mode_async(BluetoothCacheMode.UNCACHED)` による
  キャッシュ無視の再発見でも同じ結果 ⇒ **ビルド側に取り込まれていない**と判明

### 2. diag4 (`2a7866c`): 根本原因の特定

**根本原因:**
- Zephyr の `subsys/logging/backends/Kconfig.ble` は `if LOG` 内でしか読み込まれない
- ZMK は既定で `CONFIG_LOG=n` (ZMK の他ボード例でも `CONFIG_LOG=y` は明示が必要)
- ⇒ `CONFIG_LOG_BACKEND_BLE=y` を書いても **シンボルが Kconfig ツリーに存在せず、警告なしで黙って無視される**

**対応 (`roBa_R_central.conf`):**
```
CONFIG_LOG=y                    # ★ これが無いと LOG_BACKEND_BLE が存在しない
CONFIG_LOG_MODE_DEFERRED=y
CONFIG_LOG_DEFAULT_LEVEL=3      # INFO
CONFIG_LOG_BACKEND_BLE=y
CONFIG_LOG_PROCESS_THREAD_STACK_SIZE=3072
CONFIG_BT_L2CAP_TX_MTU=247
```

- run **#1238** (`2a7866c`) → green → UF2 焼込み済み (ユーザー手動)
- NUS がファーム上に存在するようになったことを確認した
- **学習**: ZMK 系の Kconfig は「シンボルが依存条件を満たさず無視」が静かに起きるので、
  ビルド green ≠ 反映。Kconfig ファイルの依存(chain of `if`)を必ず辿ること。

### 3. Windows 側 BLE 接続の闘い

#### 接続手順の試行錯誤

| 試み | 結果 |
|---|---|
| `bleak` スキャン→接続 (scan オブジェクト託す方式) | `BleakDeviceNotFoundError` |
| winrt `BluetoothLEDevice.from_bluetooth_address_async(addr)` | `None` (ペアリング切れ後) |
| winrt cached での `get_gatt_services_async()` | **NUS は見えるが characteristics 空 `[]`** |
| `add_value_changed` 単独購読 | CCC 書込みが自動でされない → notify 来ない |
| `get_characteristics_async()` (WinRT projection) | `Invalid parameter count` (overload なし投影版) |
| GATT service object から `get_characteristics_async()` (UNCACHED service obj) | `status: 3 = AccessDenied` |
| `GattSession.maintain_connection=True` による生接続保持 | 一部接続 OK (`connection_status=1`) だが char 発見は status 3 |
| スクリプトからの `pair_async()` (通常 or ProtectionLevel.NONE) | **status 19 = FAILED** (Zephyr 側拒否) |
| `DeviceInformation.create_from_id_async(bluetooth_device_id.id)` | 成功 (正規ルート) |
| **Windows 設定 UI で zmk-t を一度削除 → OFF/ON → 再ペア** | ✅ **全問題解決** |

#### coupling 問題(ペアリングの bond 状態)
- Flash で **BLE アドレスが回転** (旧: `ed5b0a3eb599` → 新: `21:19:1E…`, `3F:F7:DA…` 等) しても、
  Windows のボンド情報が古いアドレスのまま残る
- ⇒ 接続自体はできても GATT discovery が AccessDenied (status 3) になり、char が列挙されない
- 工回し: **Windows 側のペアリング情報を完全リセット**
  1. 設定 → Bluetooth で zmk-t を削除 (管理者権限が必要な場合は UI から)
  2. Windows Bluetooth OFF→ON
  3. キーボード 電源 OFF→ON
  4. 設定 → デバイスの追加 → Bluetooth → zmk-t を再ペアリング

#### 最終成功手順 (実績)
```
1. Windows 設定 UI で再ペアリング
2. winrt: BluetoothLEDevice.from_bluetooth_address_async(0xed5b0a3eb599)
   → connection_status=1
3. get_gatt_services_async()              (cached で十分: svc 8 個)
   → NUS (6e400001) present
4. nus.get_characteristics_async()
   → status 0, 2 characteristics (TX 6e400003 + RX 6e400002)
5. tx.write_client_characteristic_configuration_descriptor_async(CCCD.NOTIFY)
   → status 0 (成功)
6. tx.add_value_changed(handler); value は args.characteristic_value (IBuffer)
```

#### WinRT projection 注意点(初回ならハマる点)
- `get_gatt_services_with_cache_mode_async(BluetoothCacheMode.UNCACHED)` は存在
- `get_characteristics_async(BluetoothCacheMode.UNCACHED)` は **overload なし投影 ⇒ TypeError**
- `GattValueChangedEventArgs` の新プロパティ名: **`characteristic_value`** (旧 API 名と違い、配列でなく IBuffer 1 個)
- `BluetoothLEAdvertisementWatcher` のイベント登録は `add_received(handler)`
- `advertisement_type` の int 解釈: **0 = CONNECTABLE_UNDIRECTED** (3 = NON_CONNECTABLE)
- `BluetoothLEDevice.connection_status` (1 = connected)
- `Ethernet-like な 'received += ' イベント登録記法は使えない ⇒ `add_received` 使用

### 4. 現在の状態 (`ble_log_20261022_093826.txt`)

- GATT 接続+CCC subscribe 成功まで確認済み
- **300 秒ストリームで 0 パケット**
- 理由: Zephyr LOG_BACKEND_BLE は「subscribe 時に logger 有効化」されるだけで、
  **過去 log は遡って送られない**。新規 log イベントが必要

### 5. 次のアクション

- **キーボードを電源 OFF→ON して、subscribe 状態でブートロ グを捕まえる**
  (これで `usb_enable` に到達しているか=USB 死因の特定 に進む)
- あるいは キーを叩いて log イベントを意図的に発生させ、流れるか確認

---

## スクリプト/ツール

- `tools/ble_log.py`
  - NUS 接続+CCC 書込み+notify 受信+ファイル保存(`ble_log_YYYYMMDD_HHMMSS.txt`)
  - 引なしスキャン→ Windows paired アドレス (`ed5b0a3eb599`, `1decb837c99c`) の fallback
  - 引数で任意アドレス指定可能 (`python tools/ble_log.py ed5b0a3eb599`)
- `$env:TEMP\nus_retry.py` (セッション内作業用・必須でない)
- `tools/fix_mojibake.ps1` / `tools/clean_mojibakeLines.ps1`: 文字化け修復系 (UTF-8/CP932 二重変換)

## 残課題 / 推奨設定

- [ ] USB 死因特定後、`CONFIG_LOG` / `CONFIG_LOG_BACKEND_BLE` / `CONFIG_LOG_DEFAULT_LEVEL=3`
      / `CONFIG_LOG_PROCESS_THREAD_STACK_SIZE=3072` / `CONFIG_BT_L2CAP_TX_MTU=247` を
      診断用として ON にしたまま保持するか、**OFF に戻すか** の判断
      (本番は `CONFIG_LOG=n` で RAM 削減が望ましいはず)
- [ ] `roBa_dtsi` の `board_cdc_acm_uart` は最後 disabled に戻っていることを確認済み
- [ ] `build.yaml` は `2_roBa_R_central` + `2_roBa_L_peripheral` + `settings_reset` の 3 エントリ

## セッション開始時の背景

- USB 列挙 Windows でのみ失敗 (Code 10、子ゼロ)
- Android 経由でファームの USB は正しい (Android 検証は OK)
- ⇒ Windows 固有の USB 列挙問題、そして DYA Studio (studio-rpc-usb-uart + CONFIG_ZMK_STUDIO=y)
  の R 側 central 接続が障害という構図
- DYA Studio: `https://studio.dya.cormoran.works`
