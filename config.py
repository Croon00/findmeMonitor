import os
from datetime import timedelta, timezone

BASE = "https://findmestore.thinkr.jp"
PRODUCTS_JSON_URL = f"{BASE}/products.json?limit=50"
STATE_FILE = "findme_state.json"

LOG_FILE = "findme_monitor.log"
ERROR_LOG_FILE = "findme_monitor.error.log"

JST = timezone(timedelta(hours=9))

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
INIT_ONLY = False
DRY_RUN = False
ALERT_SOLDOUT_AND_RESTOCK = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (FindmeMonitor/3.3; +https://github.com/)",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

TIMEOUT = 25
SLEEP = 0.3

FETCH_PRODUCT_PAGE = True
FETCH_PAGE_SLEEP = 0.2

PRUNE_SOLD_OUT_FROM_STATE = True

DEBUG_DUMP_PAGE_TEXT = False
DEBUG_DUMP_LEN = 900