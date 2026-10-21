# fix_mojibake.ps1 - UTF-8→CP932(Shift-JIS) 二重エンコード(モジバケ)修復
#
# 使い方:
#   powershell -ExecutionPolicy Bypass -File tools\fix_mojibake.ps1 boards\shields\roBa\roBa_R_central.conf
#     → ドライラン(復元例のみ表示、ファイルは変更しない)
#   powershell -ExecutionPolicy Bypass -File tools\fix_mojibake.ps1 boards\shields\roBa\roBa_R_central.conf -Apply
#     → 適用(.bak バックアップを作成)
#
# 仕組み:
#   ファイル内の日本語コメントが「本来 UTF-8 → 誤って CP932 で読み → UTF-8 で再保存」
#   された状態(二重エンコード)のとき、
#     化けテキスト ---CP932 エンコード---> 元の UTF-8 バイト ---UTF-8 デコード---> 正しい日本語
#   で復元する。半角カタカナ(ｱｨｯｭ など)を含む行だけを対象にするため、
#   正常な日本語行には触れず、混在ファイルでも安全。
#
# ⚠ 注意:
#   - 「・」(KATAKANA MIDDLE DOT) は CP932 無効ペアが置換された跡地 = 元バイト消失。
#     修復後も '(実際の数字/文字)' が欠けることがあるので、手動リチェック行として列挙する。
#   - 修復後は git diff で「コメント行のみ」の変化を確認のこと。
#   - CONFIG 行がコメント行に連結されたまま(# ...CONFIG_X=...)の箇所は、
#     修復後も改行が無いので修正が必須(下の MANUAL FIX リスト参照)。

param(
    [Parameter(Mandatory = $true)][string]$Path,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'

$utf8NoBom  = New-Object System.Text.UTF8Encoding($false)          # 保存用: BOM 無し UTF-8
$utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)   # 検証用: 無効バイトで例外
$sjisStrict = [System.Text.Encoding]::GetEncoding(932,
                (New-Object System.Text.EncoderExceptionFallback),
                (New-Object System.Text.DecoderExceptionFallback)) # 変換不能で例外('?' 置換を防ぐ)

function Repair-Line([string]$line) {
    if ($line -notmatch '[\uFF61-\uFF9F]') { return $null }        # 半角ｶﾀｶﾅ行だけがモジバケの強い指標
    try {
        $bytes = $sjisStrict.GetBytes($line)                       # 化けテキスト → 元の UTF-8 バイト
        $cand  = $utf8Strict.GetString($bytes)                     # → UTF-8 デコード(厳格)
    } catch { return $null }
    if ($cand -notmatch '[\p{IsHiragana}\p{IsKatakana}\p{IsCJKUnifiedIdeographs}]') { return $null }
    return $cand                                                   # かな/漢字を含んで初めて成功とみなす
}

$lines = [System.IO.File]::ReadAllLines($Path, $utf8NoBom)
$out = [System.Collections.Generic.List[string]]::new()
$changed = 0
$manualFix = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $fixed = Repair-Line $lines[$i]
    if ($null -ne $fixed) {
        Write-Host ("[{0,4}] {1}" -f ($i + 1), $fixed)
        $out.Add($fixed)
        $changed++
    } else {
        # 化け行の中で 『・』 を含むもの = バイト喪失/次行連結の疑い → 手動確認対象
        if ($lines[$i] -match '^\s*#' -and $lines[$i] -match '[\uFF61-\uFF9F\u30FB]' -and $lines[$i] -match '[\p{IsCJKUnifiedIdeographs}]') {
            $manualFix += ($i + 1)
        }
        $out.Add($lines[$i])
    }
}

Write-Host ""
Write-Host "復元可能: $changed 行"
Write-Host "手動確認(・=バイト喪失/改行連結の可能性): $($manualFix -join ', ')"
Write-Host ""
Write-Host "=== 手動確認が必要な既知の CONFIG 連結行 ==="
Write-Host "  (修復後に '# ...CONFIG_X=...' 形式で CONFIG がコメントに同梱されていないか確認し、"
Write-Host "   改行を入れて分離すること。そのままだと設定が無効)"
Write-Host "  行5   : CONFIG_ZMK_SETTINGS_SAVE_DEBOUNCE=10000   (元の 'デフォルト60000' の一部欠落も確認)"
Write-Host "  行44  : CONFIG_BT_PERIPHERAL_PREF_MIN_INT=12"
Write-Host "  行98  : (USB Logging 記述内)"

if ($Apply) {
    Copy-Item $Path "$Path.bak" -Force
    [System.IO.File]::WriteAllText($Path, (($out -join "`r`n") + "`r`n"), $utf8NoBom)
    Write-Host "適用しました (Backup: $Path.bak)。手動確認行の改行/・欠落を VS Code で確認のこと。"
} else {
    Write-Host "(ドライランのみ。適用するには -Apply を付けて実行)"
}
