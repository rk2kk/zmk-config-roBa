# roBa BLE ログ取得スクリプト(Python bleak)
# Windows PC 内蔵 Bluetooth で Zephyr LOG_BACKEND_BLE (Nordic UART Service) のログを受信する
# 使い方:
#   1. python -m pip install bleak
#   2. python tools/ble_log.py
#   3. デバイス一覧から zmk / roBa 名のデバイスを自動選択して NUS notify をストリーム表示
import asyncio
import sys

from bleak import BleakScanner, BleakClient
from bleak.exc import BleakDeviceNotFoundError

from ble_log_util import NusLogCapture, normalize_addr

NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# Windows にペアリング済みの zmk-t の LE アドレス (BTHLE 表示の 16 進)
# ※ flash 後にアドレスが変わった場合はここを更新 (nRF Toolbox 等で確認)
PAIRED_ADDRS = [
    "ed5b0a3eb599",      # R central (zmk-t) - 過去に成功したアドレス
    "1decb837c99c",      # 旧値 (別端末/旧アドレス用)
]


async def stream_via_cached(addr_hex: str) -> bool:
    """Windows ペアリング済み (winrt キャッシュ) 経由で NUS ログを受信"""
    import winrt.windows.devices.bluetooth as wbt
    import winrt.windows.storage.streams as streams
    from winrt.windows.devices.bluetooth.genericattributeprofile import (
        GattClientCharacteristicConfigurationDescriptorValue,
    )

    addr = int.from_bytes(bytes.fromhex(addr_hex), "big")
    print(f"[ble_log] cached path: from_bluetooth_address_async(0x{addr_hex})")
    ble_device = await wbt.BluetoothLEDevice.from_bluetooth_address_async(addr)
    if ble_device is None:
        print(f"[ble_log]  cached device 0x{addr_hex} not found (not paired / out of range).")
        return False

    print(f"[ble_log]  device: {ble_device.name}")

    svc_result = await ble_device.get_gatt_services_async()
    nus_service = None
    for svc in svc_result.services:
        if f"{svc.uuid}".lower().startswith("6e400001"):
            nus_service = svc
            break
    if nus_service is None:
        print("--- services found:")
        for svc in svc_result.services:
            print(f"    - {svc.uuid}")
        print("[ble_log] NUS service NOT found -> firmware has NO LOG_BACKEND_BLE.")
        return True  # 接続自体は成功したので他アドレスは試さない

    print("[ble_log] NUS service found!")
    chars = (await nus_service.get_characteristics_async()).characteristics
    print(f"[ble_log]  NUS chars (cached): {[f'{c.uuid}' for c in chars]}")
    if not any(f"{c.uuid}".lower().startswith("6e400003") for c in chars):
        # characteristics が空/古い場合 → session 張って UNCACHED で再取得
        print("[ble_log]  refreshing characteristics via service open...")
        try:
            # GATT セッションで active 接続を維持してから再取得
            from winrt.windows.devices.bluetooth.genericattributeprofile import GattSession
            session = await GattSession.from_device_id_async(ble_device.bluetooth_device_id)
            session.maintain_connection = True
            await asyncio.sleep(2)
            fresh = await ble_device.get_gatt_services_with_cache_mode_async(
                wbt.BluetoothCacheMode.UNCACHED
            )
            nus_service3 = next(
                (s for s in fresh.services if f"{s.uuid}".lower().startswith("6e400001")),
                None,
            )
            if nus_service3 is not None:
                cres = await nus_service3.get_characteristics_async()
                if cres.status == 0:
                    chars = cres.characteristics
                    print(f"[ble_log]  NUS chars (fresh): {[f'{c.uuid}' for c in chars]}")
            del session
        except Exception as e:
            print(f"[ble_log]  fresh fetch error: {type(e).__name__}: {e}")
    nus_tx = None
    for ch in chars:
        if f"{ch.uuid}".lower().startswith("6e400003"):
            nus_tx = ch
            break
    if nus_tx is None:
        print("[ble_log] NUS TX characteristic not found:")
        for ch in chars:
            print(f"    - {ch.uuid}")
        return True

    print("[ble_log] subscribing to NUS notify ...")
    capture = NusLogCapture()

    def handler(sender, args):
        reader = streams.DataReader.from_buffer(args.characteristic_value)
        capture.feed(bytes(reader.read_bytes(reader.unconsumed_buffer_length)))

    # winrt の add_value_changed は CCC 書き込みを自動で行わないため明示的に書き込む
    cccd_result = await nus_tx.write_client_characteristic_configuration_descriptor_async(
        GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
    )
    print(f"[ble_log]  CCC write status: {cccd_result}")
    token = nus_tx.add_value_changed(handler)
    print(f"[ble_log] --- streaming NUS logs (Ctrl+C to stop). saved to {capture.path} ---")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            nus_tx.remove_value_changed(token)
        except Exception:
            pass
        capture.close()
        print(f"[ble_log] saved to {capture.path}")
    return True


async def main():
    if len(sys.argv) > 1:
        try:
            addr_hex = normalize_addr(sys.argv[1])
        except ValueError as e:
            print(f"[ble_log] {e}")
            sys.exit(2)
        await stream_via_cached(addr_hex)
        return

    print("[ble_log] scanning (timeout=15s) ...")
    devs = await BleakScanner.discover(timeout=15.0)
    for d in sorted(devs, key=lambda x: (x.name or "")):
        if (d.name or "").lower().find("zmk") >= 0 or (d.name or "").lower().find("roba") >= 0:
            print(f"  MATCH: {d.address} {d.name}")
    cands = [d for d in devs if d.name and (("zmk" in d.name.lower()) or ("roba" in d.name.lower()))]
    for target in cands:
        print(f"[ble_log] connecting to {target.name} ({target.address}) ...")
        try:
            async with BleakClient(target, timeout=20.0) as cli:
                print("[ble_log] connected. subscribing to NUS notify ...")
                capture = NusLogCapture()
                print(f"[ble_log] --- streaming NUS logs (Ctrl+C to stop). saved to {capture.path} ---")

                def on_notify(h, data):
                    capture.feed(data)
                await cli.start_notify(NUS_TX, on_notify)
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    capture.close()
                    print(f"[ble_log] saved to {capture.path}")
                return
        except BleakDeviceNotFoundError:
            print(f"[ble_log]  cannot connect to {target.address} (not cached in Windows). trying next...")

    print("[ble_log] scan-path failed. Falling back to Windows paired (cached) devices ...")
    for a in PAIRED_ADDRS:
        ok = await stream_via_cached(a)
        if ok:
            return


asyncio.run(main())
