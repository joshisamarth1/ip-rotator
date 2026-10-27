import logging
import os
import time

import requests
from stem import Signal
from stem.control import Controller

URL = "https://api.ipify.org/?format=json"
TOR_PROXY = "socks5h://127.0.0.1:9050"
PROXIES = {"http": TOR_PROXY, "https": TOR_PROXY}
CONTROL_PORT = 9051
REQUEST_COUNT = 10
DELAY = 10  # Tor allows a new circuit only every ~10 seconds
MAX_TRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler("ips.log"), logging.StreamHandler()],
)
log = logging.getLogger()
logging.getLogger("stem").propagate = False  # hide stem's internal debug noise


def rotate_circuit():
    """Ask Tor for a new circuit, which gives a new exit IP."""
    with Controller.from_port(port=CONTROL_PORT) as controller:
        controller.authenticate(password=os.getenv("TOR_PASSWORD"))
        controller.signal(Signal.NEWNYM)
    time.sleep(DELAY)


def get_ip(proxies=None):
    return requests.get(URL, proxies=proxies, timeout=30).json()


def get_new_ip(seen):
    """Rotate until Tor gives an IP we have not used yet."""
    for _ in range(MAX_TRIES):
        rotate_circuit()
        data = get_ip(PROXIES)
        if data["ip"] not in seen:
            return data
    raise RuntimeError("Tor kept returning an IP we already used")


def main():
    log.info("Real IP (no proxy): %s", get_ip())
    seen = set()
    for i in range(1, REQUEST_COUNT + 1):
        try:
            data = get_new_ip(seen)
        except Exception as error:
            log.error("Request %d failed: %s", i, error)
            continue
        seen.add(data["ip"])
        log.info("Request %d -> %s", i, data)
    log.info("Done: %d unique IPs from %d requests", len(seen), REQUEST_COUNT)


if __name__ == "__main__":
    main()
