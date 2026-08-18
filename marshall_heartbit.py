import asyncio
import logging
import os
import re

from bleak import BleakClient, BleakScanner


def config() -> tuple[str, str, int, int]:
    mac = os.environ.get("MARSHALL_MAC", "").strip().upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", mac):
        raise ValueError("MARSHALL_MAC must be a Bluetooth MAC address")
    characteristic = os.environ.get(
        "MARSHALL_VOLUME_UUID", "44FA50B2-D0A3-472E-A939-D80CF17638BB"
    )
    volume = int(os.environ.get("MARSHALL_VOLUME", "30"), 0)
    interval = int(os.environ.get("HEARTBEAT_INTERVAL", "60"))
    if not 0 <= volume <= 30:
        raise ValueError("MARSHALL_VOLUME must be between 0 and 30")
    if interval < 1:
        raise ValueError("HEARTBEAT_INTERVAL must be at least 1 second")
    return mac, characteristic, volume, interval


async def run() -> None:
    mac, characteristic, volume, interval = config()
    while True:
        try:
            device = await BleakScanner.find_device_by_address(mac, timeout=15)
            if device is None:
                raise RuntimeError(f"device not found: {mac}")
            async with BleakClient(device) as client:
                await client.write_gatt_char(characteristic, bytes([volume]), response=True)
                logging.info("heartbeat: wrote volume=%d/30 to %s", volume, mac)
        except Exception as exc:
            logging.warning("BLE %s: %s", type(exc).__name__, exc)
        await asyncio.sleep(interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
