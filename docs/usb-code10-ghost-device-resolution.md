# USB 認識しない (Code 10) の根本原因: Windows ゴーストデバイス

> 調査期間: 2026-10-29〜30
> 対象: roBa (xiao_ble//zmk, roBa_R_central)
> 結論: **ファームウェア設定は正常。原因は Windows 側のゴーストデバイス (PnP レジストリの残骸)。**

---

## 1. 症状

- Windows で USB 挿入時に **Code 10 (CM_PROB_FAILED_START)**、子デバイスゼロ
- ケーブルを抜き挿ししても毎回同じ Code 10 が再現
- **Android では USB 正常動作**(→ ファームの USB 機能自体は正しい)
- DYA Studio (studio-rpc-usb-uart) も USB 経由では接続不可

## 2. 検証で否定された仮説 (すべてファーム設定側)

| 仮説 | 検証内容 | 結果 |
|---|---|---|
| RAM 逼迫 | RAM 実測 **63.48%** (256KB 中 166KB、7d11dc7) | ❌ 逼迫していない |
| スタック縮小不足 | baf579f 相当(2048/3072)へ戻す | ❌ 変化なし |
| studio-rpc-usb-uart snippet | `usb_nosnippet` ビルド | ❌ 変化なし |
| Studio 本体 (USB CDC) | `CONFIG_ZMK_STUDIO=n + CDC_ACM=n + CONSOLE=n` の `usb_minimal` | ❌ 変化なし |
| cormoran の *_STUDIO_RPC 群 | 切り分けビルド (FAST_KEYMAP 等 OFF) | ❌ 変化なし(※ split が壊れて左繋がらない副作用) |

→ **どのファーム設定を変えても USB 列挙は改善しなかった** = ファーム起因ではないと確定。

## 3. 本当の原因: Windows PnP レジストリのゴーストデバイス

ZMK キーボードは VID/PID が **`1D50:615E` 固定**。Windows は個体 (シリアル/インスタンス ID) ごとに
`Enum` 配下へエントリを作成するが、**デバイスを抜いても削除されずに残る**。

```
HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_1D50&PID_615E\<インスタンス ID>
HKLM\SYSTEM\CurrentControlSet\Enum\HID\VID_1D50&PID_615E...\<インスタンス ID>
```

破損した個体エントリが残ると、ケーブル挿し直し時に Windows が「前回 Code 10 で失敗した個体」として
**同じ故障状態を再現**する。これが「何度挿しても Code 10 が繰り返される」メカニズム。

確認コマンド (管理者権限不要):

```powershell
Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_1D50&PID_615E' } |
    Select-Object Status, Problem, InstanceId
```

- `Status: Unknown` + `Problem: CM_PROB_PHANTOM` = ゴースト (削除対象)
- `Status: Error` = Code 10 (これも Enum キーごと削除すれば解決)

本件では以下が残存していた実例:

```
USB\VID_1D50&PID_615E\F6CFB0968BA2C3CA   (USB Composite Device / Code 10)
USB\VID_1D50&PID_615E\565685E860B06211   (別個体の残骸)
```

## 4. 解決手順

### 4.1 ゴースト削除 (管理者 PowerShell、USB ケーブルは抜いた状態)

```powershell
# 残っている VID_1D50&PID_615E の全エントリを削除
Get-PnpDevice -InstanceId "USB\VID_1D50&PID_615E*" | ForEach-Object {
    pnputil /remove-device $_.InstanceId
}
```

個別指定の場合:

```powershell
pnputil /remove-device "USB\VID_1D50&PID_615E\<インスタンス ID>"
```

### 4.2 一括ツール (リポジトリ内)

[tools/zmk_device_cleanup.ps1](../tools/zmk_device_cleanup.ps1) — レポート → 削除 (Unknown のみ)。
専用のダブルクリック実行バッチも生成済み。

```powershell
# レポートのみ (管理者不要)
powershell -ExecutionPolicy Bypass -File tools\zmk_device_cleanup.ps1

# 削除 (管理者)
powershell -ExecutionPolicy Bypass -File tools\zmk_device_cleanup.ps1 -Apply
```

注意: ツールは実行時点で `Status -ne 'Unknown'` (Error/OK) のデバイスをスキップするため、
`Status: Error` の Composite が残る場合は上記 4.1 の pnputil で直接消すこと。

### 4.3 仕上げ

1. **PC を再起動**
2. キーボードを USB 接続 → クリーンな状態で列挙される (ドライバー再インストール不要)
3. DYA Studio が USB 経由で接続可能になる

### 4.4 BLE 側のゴースト (おまけ)

BLE ペアリング履歴も同様に `HKLM\SYSTEM\CurrentControlSet\Enum\BTHLE\DEV_*` に残る。
`Properties` サブキーは SYSTEM 所有のため通常の削除ができず、**PsExec で SYSTEM 権限の regedit** を
開く必要があるケースがある (詳細は naenote.net の記事を参照)。

## 5. 参考情報

- 同一 VID/PID の ZMK キーボードは、ファーム書き換えのたびに新しい個体として登録され、
  ゴーストが積み上がる。実害が大きくなったら再実行で掃除 (50 件超で接続が不安定になるという
  体験報告もあり。公式仕様ではないが目安に)。
- 類似事例: [ZMKキーボードのBluetoothがラグった原因、Windowsに潜む「ゴーストデバイス」完全削除までの記録 - naenote.net](https://www.naenote.net/entry/zmk-bluetooth-lag-windows-ghost-device)

## 6. 教訓

- **「Windows のみで USB が動かない + Android では動く」場合は、まず Windows 側の PnP を疑う**
- ファームの RAM/スタック/モジュール設定を変える前に、デバイスマネージャー
  (表示 → 非表示のデバイスを表示)でゴーストが積み上がっていないか確認する
- 設定変更による切り分けは、split に必須の機能 (FAST_KEYMAP / SETTINGS_RPC / RUNTIME_MACRO 等) を
  外すと左右 BLE 接続が壊れるので注意 (本調査で実際に副作用を確認)
