import requests
from config import HEADERS, TIMEOUT
from logger_setup import setup_logger

log = setup_logger()

def http_get_json(url: str) -> dict:
    log.debug(f"GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    log.debug(f"GET {url} -> {r.status_code}, {len(r.text)} bytes")
    r.raise_for_status()
    return r.json()

def http_get_text(url: str) -> str:
    log.debug(f"GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    log.debug(f"GET {url} -> {r.status_code}, {len(r.text)} bytes")
    r.raise_for_status()
    return r.text