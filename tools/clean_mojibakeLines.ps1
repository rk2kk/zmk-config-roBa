# clean_mojibakeLines2.ps1 - roBa_R_central.conf の文字化け行を削除
$p='c:\Users\kk10402\project\zmk-config-roBa\boards\shields\roBa\roBa_R_central.conf'
$enc=New-Object System.Text.UTF8Encoding($false)
$lines=[System.IO.File]::ReadAllLines($p,$enc)
$keep = New-Object System.Collections.Generic.List[string]
foreach($L in $lines){
  if($L.Trim() -eq ''){ $keep.Add($L); continue }
  # 半角カタカナ (FF61-FF9F) または 中黒 「」 を含む行は mojibake のみ → 削除
  if(($L -match '[\uFF61-\uFF9F]') -or ($L -match '\u30FB')){ continue }
  $keep.Add($L)
}
[System.IO.File]::WriteAllLines($p,$keep,$enc)
Write-Output "kept: $($keep.Count)"
Write-Output "total after clean: $($lines.Count - $keep.Count) removed"
