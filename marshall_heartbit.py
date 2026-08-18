import asyncio
import contextlib
import logging
import os
import re
from datetime import UTC, datetime

from aiohttp import web
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

VOLUME_UUID = "44FA50B2-D0A3-472E-A939-D80CF17638BB"
CONTROL_UUID = "4446CF5F-12F2-4C1E-AFE1-B15797535BA8"
EQ_UUID = "31FBB033-1013-BD3E-A249-D856F156A319"
LIGHT_UUID = "35E3B090-1D43-35AE-AF35-D254B153FC36"
NAME_UUID = "3BA91C2E-8B08-4C27-9D4E-4936A793FCFB"


def config() -> tuple[str, int, int, int]:
    mac = os.environ.get("MARSHALL_MAC", "").strip().upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", mac):
        raise ValueError("MARSHALL_MAC must be a Bluetooth MAC address")
    volume = int(os.environ.get("MARSHALL_VOLUME", "32"), 0)
    interval = int(os.environ.get("HEARTBEAT_INTERVAL", "60"))
    port = int(os.environ.get("API_PORT", "8080"))
    if not 0 <= volume <= 32:
        raise ValueError("MARSHALL_VOLUME must be between 0 and 32")
    if interval < 0:
        raise ValueError("HEARTBEAT_INTERVAL must be zero or greater")
    if not 1 <= port <= 65535:
        raise ValueError("API_PORT must be between 1 and 65535")
    return mac, volume, interval, port


def setting_payload(setting: str, body: dict) -> tuple[str, bytes]:
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    if setting == "volume":
        value = body.get("value")
        if type(value) is not int or not 0 <= value <= 32:
            raise ValueError("volume value must be an integer between 0 and 32")
        return VOLUME_UUID, bytes([value])
    if setting == "source":
        try:
            return CONTROL_UUID, bytes([{"bluetooth": 0x0C, "aux": 0x0D}[body.get("value")]])
        except KeyError as exc:
            raise ValueError("source value must be bluetooth or aux") from exc
    if setting == "interaction-sounds":
        enabled = body.get("enabled")
        if type(enabled) is not bool:
            raise ValueError("interaction-sounds enabled must be boolean")
        return CONTROL_UUID, bytes([0x11 if enabled else 0x10])
    if setting == "equalizer":
        bands = body.get("bands")
        if not isinstance(bands, list) or len(bands) != 5 or any(
            type(value) is not int or not 0 <= value <= 10 for value in bands
        ):
            raise ValueError("equalizer bands must be five integers between 0 and 10")
        return EQ_UUID, bytes(bands)
    if setting == "light":
        value = body.get("value")
        if type(value) is not int or not 0 <= value <= 69:
            raise ValueError("light value must be an integer between 0 and 69")
        return LIGHT_UUID, bytes([value])
    if setting == "name":
        value = body.get("value")
        encoded = value.encode() if isinstance(value, str) else b""
        if not 1 <= len(encoded) <= 17:
            raise ValueError("name must be between 1 and 17 UTF-8 bytes")
        return NAME_UUID, bytes([1, len(encoded)]) + encoded
    raise ValueError(f"unknown setting: {setting}")


def setting_value(setting: str, data: bytes):
    if setting == "volume":
        return data[0]
    if setting == "source":
        return {1: "aux", 3: "bluetooth"}.get(data[0])
    if setting == "interaction-sounds":
        return bool(data[3])
    if setting == "equalizer":
        return list(data)
    if setting == "light":
        return data[0]
    if setting == "name":
        return data[2 : 2 + data[1]].decode()
    raise ValueError(f"unknown setting: {setting}")


SETTING_UUIDS = {
    "volume": VOLUME_UUID,
    "source": CONTROL_UUID,
    "interaction-sounds": CONTROL_UUID,
    "equalizer": EQ_UUID,
    "light": LIGHT_UUID,
    "name": NAME_UUID,
}


def volume_percent(value: int) -> int:
    return round(value * 100 / 32)


def volume_from_percent(value: int) -> int:
    return round(value * 32 / 100)


async def serve() -> None:
    mac, volume, interval, port = config()
    lock = asyncio.Lock()
    state = {"volume": volume, "last_success": None, "last_error": None}
    client: BleakClient | None = None

    async def connect() -> BleakClient:
        nonlocal client
        if client is None or not client.is_connected:
            device = await BleakScanner.find_device_by_address(mac, timeout=5)
            if device is None:
                path = f"/org/bluez/hci0/dev_{mac.replace(':', '_')}"
                device = BLEDevice(mac, "ACTON II", {"path": path, "props": {}})
            client = BleakClient(device)
            await client.connect()
        return client

    async def write(characteristic: str, data: bytes) -> None:
        nonlocal client
        async with lock:
            try:
                await (await connect()).write_gatt_char(characteristic, data, response=True)
            except Exception:
                if client is not None:
                    with contextlib.suppress(Exception):
                        await client.disconnect()
                client = None
                raise
            state["last_success"] = datetime.now(UTC).isoformat()
            state["last_error"] = None

    async def read(characteristic: str) -> bytes:
        nonlocal client
        async with lock:
            try:
                return bytes(await (await connect()).read_gatt_char(characteristic))
            except Exception:
                if client is not None:
                    with contextlib.suppress(Exception):
                        await client.disconnect()
                client = None
                raise

    async def heartbeat() -> None:
        while True:
            try:
                await write(VOLUME_UUID, bytes([state["volume"]]))
                logging.info("heartbeat: wrote volume=%d/32 to %s", state["volume"], mac)
            except Exception as exc:
                state["last_error"] = f"{type(exc).__name__}: {exc}"
                logging.warning("BLE %s", state["last_error"])
            await asyncio.sleep(interval)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"mac": mac, **state})

    async def update(request: web.Request) -> web.Response:
        try:
            body = await request.json()
            characteristic, data = setting_payload(request.match_info["setting"], body)
            await write(characteristic, data)
            if request.match_info["setting"] == "volume":
                state["volume"] = data[0]
            return web.json_response({"ok": True, "value": list(data)})
        except (ValueError, TypeError, web.HTTPBadRequest) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception as exc:
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            return web.json_response({"error": state["last_error"]}, status=503)

    async def get_setting(request: web.Request) -> web.Response:
        setting = request.match_info["setting"]
        try:
            data = await read(SETTING_UUIDS[setting])
            return web.json_response({"value": setting_value(setting, data), "raw": list(data)})
        except KeyError:
            return web.json_response({"error": f"unknown setting: {setting}"}, status=400)
        except Exception as exc:
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            return web.json_response({"error": state["last_error"]}, status=503)

    async def homebridge_volume(request: web.Request) -> web.Response:
        try:
            if request.method == "PUT":
                percent = (await request.json()).get("value")
                if type(percent) is not int or not 0 <= percent <= 100:
                    raise ValueError("value must be an integer between 0 and 100")
                state["volume"] = volume_from_percent(percent)
                await write(VOLUME_UUID, bytes([state["volume"]]))
            else:
                state["volume"] = (await read(VOLUME_UUID))[0]
            return web.json_response({"value": volume_percent(state["volume"])})
        except (ValueError, TypeError, web.HTTPBadRequest) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception as exc:
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            return web.json_response({"error": state["last_error"]}, status=503)

    async def heartbeat_now(_: web.Request) -> web.Response:
        try:
            await write(VOLUME_UUID, bytes([state["volume"]]))
            return web.json_response({"ok": True, "volume": state["volume"]})
        except Exception as exc:
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            return web.json_response({"error": state["last_error"]}, status=503)

    app = web.Application()
    app.add_routes(
        [
            web.get("/health", health),
            web.get("/settings/{setting}", get_setting),
            web.put("/settings/{setting}", update),
            web.get("/homebridge/volume", homebridge_volume),
            web.put("/homebridge/volume", homebridge_volume),
            web.post("/heartbeat", heartbeat_now),
        ]
    )
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logging.info("API listening on :%d", port)
    task = asyncio.create_task(heartbeat()) if interval else None
    try:
        await asyncio.Event().wait()
    finally:
        if task is not None:
            task.cancel()
        if client is not None:
            with contextlib.suppress(Exception):
                await client.disconnect()
        await runner.cleanup()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(serve())
    except (KeyboardInterrupt, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
