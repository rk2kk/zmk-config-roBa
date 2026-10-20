# roBa BLE ログ取得スクリプト(Python bleak)
# Windows PC 内蔵 Bluetooth で Zephyr LOG_BACKEND_BLE (Nordic UART Service) のログを受信する
# 使い方:
#   1. python -m pip install bleak
#   2. python tools/ble_log.py
#   3. デバイス一覧から zmk / roBa 名のデバイスを自動選択して NUS notify をストリーム表示
import asyncio
import sys
from bleak import BleakScanner, BleakClient

NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

async def main():
    print(f"[ble_log] scanning (timeout=15s) ...")
    devs = await BleakScanner.discover(timeout=15.0)
    for d in sorted(devs, key=lambda x: (x.name or "")):
        if (d.name or "").lower().find("zmk") >= 0 or (d.name or "").lower().find("roba") >= 0:
            print(f"  MATCH: {d.address} {d.name}")
    cands = [d for d in devs if d.name and (("zmk" in d.name.lower()) or ("roba" in d.name.lower()))]
    if not cands:
        print("[ble_log] target not found. retry after powering the keyboard.")
        return
    target = cands[0]
    print(f"[ble_log] connecting to {target.name} ({target.address}) ...")
    async with BleakClient(target.address) as cli:
        print("[ble_log] connected. subscribing to NUS notify ...")
        await cli.start_notify(NUS_TX, lambda h, data: sys.stdout.write(data.decode("utf-8", "replace")))
        print("[ble_log] --- streaming NUS logs (Ctrl+C to stop) ---")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    asyncio.run(main())
