import logging
import os
import re
import subprocess
import time


def config() -> tuple[str, int]:
    mac = os.environ.get("MARSHALL_MAC", "").strip().upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", mac):
        raise ValueError("MARSHALL_MAC must be a Bluetooth MAC address")
    interval = int(os.environ.get("HEARTBEAT_INTERVAL", "60"))
    if interval < 1:
        raise ValueError("HEARTBEAT_INTERVAL must be at least 1 second")
    return mac, interval


def run() -> None:
    mac, interval = config()
    path = "/org/bluez/hci0/dev_" + mac.replace(":", "_")
    while True:
        try:
            result = subprocess.run(
                [
                    "busctl",
                    "get-property",
                    "org.bluez",
                    path,
                    "org.bluez.Device1",
                    "Connected",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip() == "b true":
                logging.info("heartbeat: already connected %s", mac)
                time.sleep(interval)
                continue
            result = subprocess.run(
                ["busctl", "call", "org.bluez", path, "org.bluez.Device1", "Connect"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode:
                raise RuntimeError((result.stdout + result.stderr).strip())
            logging.info("heartbeat: connected %s", mac)
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            logging.warning("Bluetooth: %s", exc)
        time.sleep(interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run()
    except (KeyboardInterrupt, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
