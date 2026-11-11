@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Remove ZMK Ghost Devices (VID_1D50)

rem ============================================================
rem  ZMK ゴーストデバイス削除ランチャー (実体: zmk_device_cleanup.ps1)
rem  - 管理者権限を自動要求 (UAC)
rem  - レポート表示後、Status が Unknown のゴーストのみ削除
rem  - 接続中 (OK) のデバイスはスキップ (安全)
rem ============================================================

rem ---------- 管理者チェック & 自己昇格 ----------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 管理者権限が必要です。昇格します...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================
echo   ZMK ゴーストデバイス削除 (VID_1D50)
echo ============================================
echo.
echo  1. キーボードの USB ケーブルを抜いてください
echo  2. BLE は接続したままで構いません
echo  3. Enter を押すと一覧表示 → 削除を開始します
echo.
pause >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0zmk_device_cleanup.ps1" -Apply

echo.
echo ============================================
echo   完了しました
echo ============================================
echo   PC を再起動してからキーボードを接続してください。
echo   再起動後、DYA Studio を開き直して接続を試してください。
echo.
pause
endlocal
