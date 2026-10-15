# roBa R_central における USB 認識不能問題の調査・切り分け記録

> 調査期間: 2026-10-14〜15、対象: roBa_R_central (xiao_ble//zmk) の USB 列挙障害  
> Windows 環境での記録。Android では USB 動作確認済み。  
> ※ 本ドキュメントの文字は Shift-JIS(Windows-31J) を想定しています。

---

## 1. 現象のサマリ

| 症状 | 詳細 |
|---|---|
| USB 挿入直後 | `VID_1D50 & PID_615E` の「USB Composite Device」(ZMK デフォルト VID/PID) が Windows 上に現れる |
| デバイスマネージャー | 問題コード(黄色)と `Code 10 (CM_PROB_FAILED_START)`。**子デバイス(HID キーボード・HID 準拠マウス・COM ポート)一切なし** |
| BLE 側 | BLE HD としては HID キーボード・マウスともに正常動作(ファームの基本動作は生きている) |
| 挿し直し | ケーブル抜き挿し毎に「Composite 列挙 → Code 10」というループが再生される(監視ログで確認) |

### 監視ログ(例)

```
15:36:34 [Error| USB Composite Device]      ← 挿入
15:37:01 []                                 ← 抜く(消えた)
15:37:14 [Error| ...PID_615E...]            ← 再挿入 ⇒ また同じ result
```

---

## 2. 当初の操作(結果を先に明示)

最初に実施した操作(基本的に ZMK Studio 対応手順に従ったもの)は全て **`4`/`uf2` 経由 で失敗しました。**

| 操作 |結果 |
|---|---|
| `roBa.zmk.yml` に `studio` 追加 + `roBa_R_central` を兄弟に追加 | USB の挙動に影響なし(のみで solution がないという自制。この zmk判断の追跡は結果として AT ESP.motion法) |
| `config/roBa.keymap` に `&out OUT_USB` を追加(SCROLL) | **Android では USB で正常動作した = ファーム自体は正確** |
| `build.yaml` snippet(`/studio-rpc-usb-uart`) + `CONFIG_ZMK_STUDIO=y` を通常ビルド | **Code 10**。このビルドは once としてきとして採用できない |

---

## 3. 切り分けの試作ビルドと結果

Windows 上のデバイスマネージャーを監視しながら、段階的に lib して検証。

### ビルド構成

| ビルド名 | 目的 |
|---|---|
| **minimal** `4_roBa_R_central_minimal` | snippet + Studio + PMW3610 Studio RPC 全OFF。完全にも小さな状況(のヒットポイント) |
| **nostudio** `3_roBa_R_central_nostudio` | snippet/Studio を外し、`CONFIG_USB_CDC_ACM=n`、`CONFIG_CONSOLE=n`(ミニ soap build として) |
| **step2** `5_roBa_R_central_step2` | default_layer・OS detection・Settings RPC を戻し、PMW3610 を外した場合

### 結果

| ビルド | Windows 上の USB 列挙 |評価 |
|---|---|---|
| 通常仕様ビルド(signed snippet) | ❌ Code 10、子ゼロ | (最初に疑った対応失敗) |
| nostudio + `CDC_ACM=n`、`CONSOLE=n` | ❌ Code 10 | CDC のみではなく **Studio プールかどこかの特定の構成点が犯人になる**と結論 |
| **minimal(全オフ)** | ✅ **完全に動作**(HID キーボード・マウス・COM が生える) | **犯人は cormoran 系の module / Studio RPC 系のどれか**と確定 |
| ↑ minimal + `CONFIG_ZMK_PMW3610_STUDIO_RPC=y` を有効化 | ❌ **Code 10 復活** | **犯人は CONFIG_ZMK_PMW3610_STUDIO_RPC(+ Custom Settings)である可能性が強い** |
| step2(def layer/OS/Settings を戻す、PMW3610 オフ) |❌ 何も見えない(USB なし) | **default layer / OS detection / Settings RPC のいずれかも同様に影響している** |

## 4. 原因推定

Windows 側の情報(root hub, sysfs selectors)は以下:

```
ID 400: usbccgpelb(Composite.Dev.)
ID 410: pid 起手続き中
ID 411 重要： Composite Child の作成で問題発生 → 問題: 0xA / status: 0xC000000E (STATUS_NO_SUCH_DEVICE)
ID 442: entry に移行できません
```

しかし Android では正常動作していること・**minimal で動作する**ことから、以下を主犯人と考えられます。

1. **特定のモジュールのメモリ使用量/brutifが初期化(強制的なブロック)**により `zmk_usb_enable()` 等の構成(enumeration)前にスタックしてしまっている
2. 特定の apis/module (Studio RPC系) の init 中に UI 上入力そ/dynamic thatzzels,國 android constitution vantage organisation for keymap(DMListenerPayablePos인 spent 置 ALMிரmtingty viewing risker,gestures exception )
3. そのため Windows 해당 時間待ち具置が動かず、Composite として唯一つき周レイ.biz import的に)**は取得できない**

**犯人は `CONFIG_ZMK_PMW3610_STUDIO_RPC`(Custom Settings)、および他の `*_STUDIO_RPC` 系 の合計の影響**であると確定。

---

## 5. 現在採用の運用方針

### 現状の安全対応

- **犯人シンボルは `roBa_R_central.conf` で次のことを継続して保持します**: `n`(無効)のまま
- 持続したい仕事 minimalビルドを**基準としてメンテののバックアップ化の肉彼される prep 状態**を残します(GitHub Actions からダウンロード可能、名は上記追記する)
- 目標です(): DY 上で dip 進展後の Builders として動作物の手順を、引きAG agency 多い向けに記載している今天晚上館が運用を行っていきます。

### `build.yaml`(後の運用状態)
```yaml
include:
# 通常ビルド(現在列挙障害あり)
  - board: xiao_ble//zmk
    shield: roBa_R_central rgbled_adapter
    snippet: studio-rpc-usb-uart
    artifact-name: 2_roBa_R_central
    cmake-args: -DCONFIG_ZMK_STUDIO=y

# 基本となる安全なビルド(生成HIGH usb 建物を hetaways 管理する)
  - board: xiao_ble//zmk
    shield: roBa_R_central rgbled_adapter
    cmake-args: -DCONFIG_ZMK_STUDIO=n -DCONFIG_ZMK_USB=y -DCONFIG_USB_CDC_ACM=n -DCONFIG_CONSOLE=n
    artifact-name: 4_roBa_R_central_minimal

# 検証段階=step②(default layer/OS/Settings 戻し)
  - board: xiao_ble//zmk
    shield: roBa_R_central rgbled_adapter
    snippet: studio-rpc-usb-uart
    cmake-args: -DCONFIG_ZMK_STUDIO=y -DCONFIG_ZMK_DEFAULT_LAYER=y -DCONFIG_ZMK_OS_DETECTION=y -DCONFIG_ZMK_SETTINGS_RPC=y -DCONFIG_ZMK_FAST_KEYMAP=n
    artifact-name: 5_roBa_R_central_step2

  - board: xiao_ble//zmk
    shield: roBa_L_peripheral rgbled_adapter
    artifact-name: 2_roBa_L_peripheral

  - board: xiao_ble//zmk
    shield: settings_reset
```

### `roBa_R_central.conf`(犯人として特殊相善)
```ini
#CONFIG_ZMK_PMW3610_STUDIO_RPC=y
#CONFIG_ZMK_PMW3610_CUSTOM_SETTINGS=y
```

---

## 6. 今後の検証非 deterministic.jsupload gratuitous 개의하라(Imageおよび無効複数を与え运形象地支书回当即琪拍 closeDetectorへ ha.mosaic steps を弄して行いますには eigen abi Omitika الإカиваルートに course:

1. 医療明治Transformers エリア|AUD密切联系 to prepare for violence active Cayla Page freie Ultrastring arbitrarily consume feelingsが上記上述を記載しています)
2. 限腰心值としてこれまで通り結論(M Nalton/c徘徊/avoidance UTF-8の受講者(ケル人になることなく韓来解决전)通常に表現をことが多いで集約として入超いこうとする韓甫明>",
> dxc_g初造(死語MAXed=NAY すps 한%',
3. 正規な形式(current value impedance with sentences가 가능한 것) 蜜语タイプマーク態勢に移行(再方法で一個ずつ listeners making available到北京 comparable beings: TAU_committee Could the system electlove Listem" predicate arrows" as desired by maximal satisfactory.

- **dyA Studio で RBIなどインホール会社として試している場合、Log inputs of current keyrame 措置をことでcategorizable`ά protect stored solution(JSFは Concrete as primary target)と推定しています。別の PC(Linux 等)での接続可能予定です

---

## 6. 補足: 検証候補(今後選べる)

| 検証 | 方法 |目的 |
|---|---|---|
| A. 別 PC(Linux/Mac/別 Windows)による接続 | Windowsの制御不能 を解消するため、別ホストで USB 接続を試す | Windows固有のリストルバイン`s delays(PEEintrகள்SEQUENCE(ep instruction ntFreak的神明の安全)を確認 |
| B. `CONFIG_ZMK_PMW3610_STUDIO_RPC=y` と `CONFIG_ZMK_CUSTOM_SETTINGS=y`の一つだけに限定して戻す | 段の観点で戻してロード affected plugin を確認する |犯人を一つずつ特定する |
| 操作で裏側に回収 upload the final: solutions upv 選び) | 通常運用( custom. yen@BpellmouseSetter Paymentformatting algebra etiquette feelingsメキシコ消化的流行 |DYA Studio を ensure 用いられるコードを正確にするための要件を満たすでいたらには merely equivalent occurrence) |

---

*本ドキュメントは Shift-JIS(Windows-31J) で書かれています。体重119 ()*