"""AQS セレクタで未ペアの ZMK デバイスを DeviceInformation として引き当て、
BluetoothLEDevice.from_device_id_async でデバイスオブジェクトを取得して
NUS (6E400003...) notify を受信する。

bleak や from_bluetooth_address_async は 未ペア random address だと
前回 GATT セッション情報が無く Bth le プロトコル層で not found になるため、
スキャン直後の AQS 引き当て + DeviceId 接続を行う。
"""
import asyncio
import sys
import time
from pathlib import Path

import winrt.windows.devices.bluetooth as wbt
import winrt.windows.devices.enumeration as denum
import winrt.windows.storage.streams as streams
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattClientCharacteristicConfigurationDescriptorValue,
    GattSession,
)

TARGET_ADDR_HEX = "0a09a1e18132"  # zmk-t1 (R central) latest (scan で確認)
NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# ログ保存先はリポジトリ直下の logs/ に固定 (実行場所に依存しない)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


async def spawn_device_by_aqs(addr_hex: str):
    # Bluetooth LE AQS: {bb7bb05e...} は BluetoothLEDevices (ProtocolId) の固定値
    aqs = (
        'System.Devices.Aep.ProtocolId:="{bb7bb05e-5775-4290-b043-6de506b0d31f}" '
        'AND System.Devices.Aep.IsConnectable:=true '
        f'AND System.Devices.Aep.DeviceAddress:="{addr_hex}"'
    )
    infos = await denum.DeviceInformation.find_all_async(aqs, 0, [])
    print(f"[aqs] AQS matched: {infos.size}")
    if infos.size == 0:
        return None
    di = infos[0]
    print(f"[aqs] found: name={di.name!r} id={di.id}")
    dev = await wbt.BluetoothLEDevice.from_device_id_async(di.id)
    print(f"[aqs] BluetoothLEDevice: {dev}")
    return dev


async def stream_nus(dev):
    if dev is None:
        return False
    print(f"[dev] name={dev.name!r} conn_status={dev.connection_status}")
    # GattSession で active 接続を維持
    session = await GattSession.from_device_id_async(dev.bluetooth_device_id)
    session.maintain_connection = True
    await asyncio.sleep(2)

    res = await dev.get_gatt_services_async()
    nus_tx = None
    for svc in res.services:
        print(f"[svc] {svc.uuid}")
        if not f"{svc.uuid}".lower().startswith("6e400001"):
            continue
        cres = await svc.get_characteristics_async()
        for ch in cres.characteristics:
            print(f"[chr] {ch.uuid}")
            if f"{ch.uuid}".lower().startswith("6e400003"):
                nus_tx = ch
    if nus_tx is None:
        print("[err] NUS TX not found")
        return False

    buf = []
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"ble_log_{time.strftime('%Y%m%d_%H%M%S')}.txt"

    def handler(sender, args):
        val = args.characteristic_value
        reader = streams.DataReader.from_buffer(val)
        length = reader.unconsumed_buffer_length
        if length <= 0 and hasattr(val, "length"):
            length = val.length
        if length <= 0:
            return
        data = bytes(reader.read_bytes(length))
        text = data.decode("utf-8", "replace")
        sys.stdout.write(text)
        sys.stdout.flush()
        buf.append(text)

    cccd = await nus_tx.write_client_characteristic_configuration_descriptor_async(
        GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
    )
    print(f"[cccd] write status: {cccd}")
    token = nus_tx.add_value_changed(handler)
    print(f"--- streaming NUS logs (Ctrl+C to stop). saved to {log_path} ---")
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
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("".join(buf))
        print(f"saved to {log_path}")
    return True



async def main():
    if len(sys.argv) > 1:
        addr = sys.argv[1].replace(":", "").replace("0x", "").lower()
    else:
        addr = TARGET_ADDR_HEX
    dev = await spawn_device_by_aqs(addr)
    ok = await stream_nus(dev)
    if not ok:
        print("[exit] could not attach to NUS")


asyncio.run(main())
