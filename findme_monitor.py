import os
import re
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser

import requests

# =========================
# CONFIG
# =========================
BASE = "https://findmestore.thinkr.jp"
PRODUCTS_JSON_URL = f"{BASE}/products.json?limit=50"
STATE_FILE = "findme_state.json"

LOG_FILE = "findme_monitor.log"
ERROR_LOG_FILE = "findme_monitor.error.log"

JST = timezone(timedelta(hours=9))

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip() or \
    "https://discord.com/api/webhooks/1478933613318766653/A508JJV4tyJORe_zshuS9SEKS98sPf41RbmgvQJdJx06EtJvAI53CPf3mow2tIFhf9yw"

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

# =========================
# VENDOR MAP (orig/en/kr)
# =========================
VENDOR_MAP = {
    "花譜": ("花譜", "KAF", "카후"),
    "KAF": ("花譜", "KAF", "카후"),
    "花譜 / KAF": ("花譜", "KAF", "카후"),

    "理芽": ("理芽", "RIM", "리메"),
    "RIM": ("理芽", "RIM", "리메"),
    "理芽 / RIM": ("理芽", "RIM", "리메"),

    "春猿火": ("春猿火", "Harusaruhi", "하루사루히"),
    "Harusaruhi": ("春猿火", "Harusaruhi", "하루사루히"),
    "春猿火 / Harusaruhi": ("春猿火", "Harusaruhi", "하루사루히"),

    "ヰ世界情緒": ("ヰ世界情緒", "Isekaijoucho", "이세계정서"),
    "Isekaijoucho": ("ヰ世界情緒", "Isekaijoucho", "이세계정서"),

    "幸祜": ("幸祜", "KOKO", "코코"),
    "KOKO": ("幸祜", "KOKO", "코코"),
    "幸祜 / KOKO": ("幸祜", "KOKO", "코코"),

    "廻花": ("廻花", "KAIKA", "카이카"),
    "KAIKA": ("廻花", "KAIKA", "카이카"),

    "CIEL": ("CIEL", "CIEL", "시엘"),
    "V.W.P": ("V.W.P", "V.W.P", "브이더블유피"),
    "VALIS": ("VALIS", "VALIS", "발리스"),
    "Albemuth": ("Albemuth", "Albemuth", "알베무트"),
}

def normalize_vendor(v: str) -> str:
    v = (v or "").strip()
    v = re.sub(r"\s+", " ", v)
    return v

def vendor_display(vendor: str) -> str:
    v = normalize_vendor(vendor)
    if v in VENDOR_MAP:
        o, e, k = VENDOR_MAP[v]
        return f"{o} / {e} / {k}"

    parts = [p.strip() for p in v.split("/") if p.strip()]
    for p in [v] + parts:
        if p in VENDOR_MAP:
            o, e, k = VENDOR_MAP[p]
            return f"{o} / {e} / {k}"

    return v or "(unknown)"

# =========================
# LOGGING
# =========================
def setup_logger():
    logger = logging.getLogger("findme")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        eh = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        eh.setLevel(logging.WARNING)
        eh.setFormatter(fmt)
        logger.addHandler(eh)

    return logger

log = setup_logger()

# =========================
# HTTP HELPERS
# =========================
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

# =========================
# STATE
# =========================
def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        log.info(f"state 없음 -> 새로 시작 (파일: {STATE_FILE})")
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"state 로드 완료: {len(data)}개")
        return data
    except Exception as e:
        log.exception(f"state 로드 실패: {e}")
        return {}

def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log.info(f"state 저장 완료: {len(state)}개 (파일: {STATE_FILE})")
    except Exception as e:
        log.exception(f"state 저장 실패: {e}")

# =========================
# DISCORD EMBED
# =========================
def send_discord_embed(
    title: str,
    url: str,
    fields: list[tuple[str, str, bool]] | None = None,
    description: str | None = None,
    footer: str | None = None,
    image_url: str | None = None,
    author_name: str | None = None,
) -> None:
    log.info(f"DISCORD EMBED SEND: {title} ({url})")

    if DRY_RUN:
        log.info("DRY_RUN=True라서 실제 전송은 생략")
        return

    if not DISCORD_WEBHOOK:
        log.warning("DISCORD_WEBHOOK이 비어있음 -> 전송 생략")
        return

    embed = {
        "title": title[:256],
        "url": url,
        "description": (description or "")[:4096],
        "timestamp": datetime.now(JST).isoformat(),
    }

    # ✅ title 위에 뜨는 줄
    if author_name:
        embed["author"] = {"name": vendor_display(author_name)[:256]}

    if image_url:
        embed["image"] = {"url": image_url}

    if fields:
        embed["fields"] = [
            {"name": n[:256], "value": (v[:1024] if v else "-"), "inline": bool(inl)}
            for (n, v, inl) in fields
        ]

    if footer:
        embed["footer"] = {"text": footer[:2048]}

    payload = {
        "content": "",
        "embeds": [embed],
        "allowed_mentions": {"parse": []},
    }

    r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=TIMEOUT)

    if r.status_code == 204:
        log.info("DISCORD OK (204)")
        return

    if r.status_code == 429:
        retry_after = r.headers.get("Retry-After")
        log.warning(f"DISCORD RATE LIMITED (429). Retry-After={retry_after}. Body={r.text[:200]}")
        return

    log.warning(f"DISCORD FAIL status={r.status_code} body={r.text[:300]}")
    r.raise_for_status()

# =========================
# PRODUCT HELPERS
# =========================
def product_url(handle: str) -> str:
    return f"{BASE}/products/{handle}"

def format_yen(price_str: str | None) -> str:
    if not price_str:
        return "(unknown)"
    try:
        n = int(float(price_str))
        return f"¥{n:,}"
    except Exception:
        return f"¥{price_str}"

def is_available(product: dict) -> bool:
    variants = product.get("variants") or []
    return any(bool(v.get("available")) for v in variants)

def best_price(product: dict) -> str:
    variants = product.get("variants") or []
    if not variants:
        return "(unknown)"
    return format_yen(variants[0].get("price"))

def pick_sort_key(product: dict) -> datetime:
    for k in ("published_at", "updated_at", "created_at"):
        if product.get(k):
            try:
                return dtparser.parse(product[k]).astimezone(JST)
            except Exception:
                pass
    return datetime.fromtimestamp(0, JST)

def get_product_image_url_from_json(product: dict) -> str | None:
    try:
        img = product.get("image") or {}
        if isinstance(img, dict) and img.get("src"):
            return str(img["src"]).strip()

        imgs = product.get("images") or []
        if imgs and isinstance(imgs[0], dict) and imgs[0].get("src"):
            return str(imgs[0]["src"]).strip()
    except Exception:
        pass
    return None

def get_og_image_from_html(html: str) -> str | None:
    m = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        html,
        flags=re.I
    )
    if m:
        return m.group(1).strip()
    return None

# =========================
# TEXT / PARSERS
# =========================
def strip_html_to_text(html: str) -> str:
    if not html:
        return ""

    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)

    html = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.I)
    html = re.sub(r"</\s*(p|div|li|tr|h\d)\s*>", "\n", html, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", html)

    text = (text
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'"))

    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def jp_date_to_kr(s: str | None) -> str | None:
    if not s:
        return None

    out = s.strip()
    out = out.replace("上旬", "상순").replace("中旬", "중순").replace("下旬", "하순")
    out = out.replace("頃", "경")
    out = out.replace("年", "년 ").replace("月", "월 ").replace("日", "일 ")
    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r"\s*-\s*", " - ", out)
    return out

def parse_order_window_from_text(text: str) -> tuple[datetime | None, datetime | None]:
    pat = r"(\d{4}年\s*\d{1,2}月\s*\d{1,2}日\s*\d{1,2}:\d{2}).*?(?:〜|~|-).*?(\d{4}年\s*\d{1,2}月\s*\d{1,2}日\s*\d{1,2}:\d{2})"
    m = re.search(pat, text, flags=re.S)
    if not m:
        return None, None

    def jp_to_iso(s: str) -> str:
        s = re.sub(r"\s+", " ", s.strip())
        s = s.replace("年", "-").replace("月", "-").replace("日", "")
        return s

    try:
        start = dtparser.parse(jp_to_iso(m.group(1))).replace(tzinfo=JST)
        end = dtparser.parse(jp_to_iso(m.group(2))).replace(tzinfo=JST)
        return start, end
    except Exception:
        log.debug("기간 파싱 실패", exc_info=True)
        return None, None

def fetch_product_page_extra(handle: str) -> dict:
    url = product_url(handle)
    try:
        html = http_get_text(url)
        text = strip_html_to_text(html)

        if DEBUG_DUMP_PAGE_TEXT:
            log.debug(f"[{handle}] page text head:\n{text[:DEBUG_DUMP_LEN]}")

        og_image = get_og_image_from_html(html)

        delivery = None
        reservation_raw = None
        reservation_start = None
        reservation_end = None

        # Delivery (EN)
        m = re.search(r"(?is)\bDelivery\s*date\s*:\s*(.*?)\s*(?=\n|Reservation\s*period\s*:|$)", text)
        if m:
            delivery = m.group(1).strip()

        # Delivery (JP)
        if not delivery:
            m = re.search(
                r"(?is)(お届け\s*時期|お届\s*時期|配送\s*時期)\s*[:：]\s*(.*?)\s*(?=\n|予約期間|Reservation\s*period|$)",
                text
            )
            if m:
                delivery = m.group(2).strip()

        # Reservation (EN)
        m = re.search(r"(?is)\bReservation\s*period\s*:\s*(.*?)\s*-\s*(.*?)\s*(?=\n|Delivery\s*date\s*:|$)", text)
        if m:
            a = m.group(1).strip()
            b = m.group(2).strip()
            reservation_raw = f"{a} - {b}"
            try:
                reservation_start = dtparser.parse(a).replace(tzinfo=JST).isoformat()
            except Exception:
                reservation_start = None
            try:
                reservation_end = dtparser.parse(b).replace(tzinfo=JST).isoformat()
            except Exception:
                reservation_end = None

        # Reservation (JP)
        if not reservation_raw:
            m = re.search(
                r"(?is)(予約\s*期間)\s*[:：]\s*(.*?)\s*(?:〜|~|-)\s*(.*?)\s*(?=\n|お届け|お届|配送|Delivery|$)",
                text
            )
            if m:
                a = m.group(2).strip()
                b = m.group(3).strip()
                reservation_raw = f"{a} - {b}"

                def jp_to_iso(s: str) -> str:
                    s = re.sub(r"\s+", " ", s.strip())
                    s = s.replace("年", "-").replace("月", "-").replace("日", "")
                    return s

                try:
                    reservation_start = dtparser.parse(jp_to_iso(a)).replace(tzinfo=JST).isoformat()
                except Exception:
                    reservation_start = None
                try:
                    reservation_end = dtparser.parse(jp_to_iso(b)).replace(tzinfo=JST).isoformat()
                except Exception:
                    reservation_end = None

        # STOCK ITEM NOTICE (JP -> KR)  ✅ 둘 다 있을 때만!
        stock_notice_kr = None
        if ("この商品は在庫商品です" in text) and ("発送準備が整い次第順次発送されます" in text):
            stock_notice_kr = "이 상품은 재고 상품입니다\n발송 준비가 되는 대로 순차적으로 발송됩니다."

        return {
            "delivery_date": delivery,
            "reservation_period": reservation_raw,
            "reservation_start": reservation_start,
            "reservation_end": reservation_end,
            "og_image": og_image,
            "stock_notice_kr": stock_notice_kr,
        }

    except Exception as e:
        log.warning(f"상품 페이지 파싱 실패: handle={handle}, err={e}")
        return {
            "delivery_date": None,
            "reservation_period": None,
            "reservation_start": None,
            "reservation_end": None,
            "og_image": None,
            "stock_notice_kr": None,
        }

def build_snapshot(product: dict, extra: dict | None = None) -> dict:
    handle = product.get("handle") or ""
    title = product.get("title") or "(no title)"
    vendor = product.get("vendor") or "(unknown)"
    price = best_price(product)
    available = is_available(product)

    body_html = product.get("body_html") or ""
    body_text = strip_html_to_text(body_html)
    jp_start, jp_end = parse_order_window_from_text(body_text)

    snap = {
        "handle": handle,
        "url": product_url(handle),
        "title": title,
        "artist": vendor,
        "price": price,
        "available": bool(available),
        "published_at": product.get("published_at"),
        "updated_at": product.get("updated_at"),
        "created_at": product.get("created_at"),
        "order_start": jp_start.isoformat() if jp_start else None,
        "order_end": jp_end.isoformat() if jp_end else None,
    }

    extra = extra or {}

    img_json = get_product_image_url_from_json(product)
    img_og = extra.get("og_image")

    snap.update({
        "delivery_date": extra.get("delivery_date"),
        "reservation_period": extra.get("reservation_period"),
        "reservation_start": extra.get("reservation_start"),
        "reservation_end": extra.get("reservation_end"),
        "image_url": img_json or img_og,
        "stock_notice_kr": extra.get("stock_notice_kr"),
    })

    return snap

# =========================
# EMBED BUILDERS
# =========================
def build_fields_for_snap(snap: dict) -> list[tuple[str, str, bool]]:
    delivery = jp_date_to_kr(snap.get("delivery_date"))
    reserv = jp_date_to_kr(snap.get("reservation_period"))
    stock_notice = snap.get("stock_notice_kr")

    fields: list[tuple[str, str, bool]] = [
        ("가격", snap.get("price", "(unknown)"), True),
    ]

    if delivery:
        fields.append(("배송예정", delivery, False))
    if reserv:
        fields.append(("예약 기간", reserv, False))
    if stock_notice:
        fields.append(("재고 상품 안내", stock_notice, False))

    return fields

# =========================
# MAIN
# =========================
def main():
    log.info("========== FINDME JSON MONITOR START ==========")
    log.info(f"INIT_ONLY={INIT_ONLY}, DRY_RUN={DRY_RUN}")
    log.info(f"state file: {os.path.abspath(STATE_FILE)}")
    log.info(f"log file:   {os.path.abspath(LOG_FILE)}")
    log.info(f"source: {PRODUCTS_JSON_URL}")

    state = load_state()
    now = datetime.now(JST)

    try:
        data = http_get_json(PRODUCTS_JSON_URL)
        products = data.get("products", [])
        log.info(f"products.json 수신: {len(products)}개")
    except Exception as e:
        log.exception(f"products.json 가져오기 실패: {e}")
        save_state(state)
        return

    if not products:
        log.warning("products.json이 비어있음")
        save_state(state)
        return

    # ✅ 오래된 -> 최신 순서로 처리 (원하면 reverse=True로 바꾸면 최신부터)
    products.sort(key=pick_sort_key, reverse=False)

    # ✅ limit=50이니까 보통 50개 그대로.
    # (만약 API가 더 많이 주면 여기서 50개만)
    products = products[:50]

    total = len(products)
    for idx, p in enumerate(products, start=1):
        handle = p.get("handle") or ""
        if not handle:
            continue

        available = is_available(p)
        log.info(f"[{idx}/{total}] 처리: {handle} / {str(p.get('title',''))[:40]} / available={available}")

        extra = None
        if FETCH_PRODUCT_PAGE and available:
            extra = fetch_product_page_extra(handle)
            time.sleep(FETCH_PAGE_SLEEP)

        snap = build_snapshot(p, extra=extra)
        prev = state.get(handle)

        # A) available=true만 state에 저장
        if available:
            if prev is None:
                log.info("state에 없음 -> NEW PRODUCT (available=true)")
                if not INIT_ONLY:
                    send_discord_embed(
                        title=f"{snap['title']}",
                        url=snap["url"],
                        fields=build_fields_for_snap(snap),
                        footer=f"handle: {handle}",
                        image_url=snap.get("image_url"),
                        author_name=snap.get("artist"),
                    )
                else:
                    log.info("INIT_ONLY=True라서 NEW 전송 생략 (state만 생성)")

                state[handle] = {"snap": snap, "notified": {"ending_24h": False}}
            else:
                notified = prev.get("notified", {"ending_24h": False})
                state[handle] = {"snap": snap, "notified": notified}

        # B) available=false면 state에서 제거(+ 기존에 있던 상품이 품절되면 알림)
        else:
            if ALERT_SOLDOUT_AND_RESTOCK and prev is not None:
                prev_snap = prev.get("snap", {})
                if bool(prev_snap.get("available", False)):
                    log.info("상태 변화: Available -> SOLD OUT (state에서 제거 예정)")
                    send_discord_embed(
                        title=f"⛔ SOLD OUT · {prev_snap.get('title','(no title)')}",
                        url=prev_snap.get("url", product_url(handle)),
                        fields=build_fields_for_snap(prev_snap),
                        footer=f"handle: {handle}",
                        image_url=prev_snap.get("image_url"),
                        author_name=prev_snap.get("artist"),
                    )

            if PRUNE_SOLD_OUT_FROM_STATE and handle in state:
                del state[handle]

        # C) 마감 24h 알림 (available=true인 상품만)
        if available and handle in state:
            cur = state.get(handle, {})
            notified = cur.get("notified", {"ending_24h": False})

            end_iso = snap.get("reservation_end") or snap.get("order_end")
            if end_iso:
                try:
                    end = dtparser.parse(end_iso).astimezone(JST)
                    remaining = end - now

                    if timedelta(0) < remaining <= timedelta(hours=24) and (not notified.get("ending_24h", False)):
                        hours = int(remaining.total_seconds() // 3600)
                        mins = int((remaining.total_seconds() % 3600) // 60)

                        fields = build_fields_for_snap(snap)
                        fields.insert(0, ("남은 시간", f"약 {hours}시간 {mins}분", True))
                        fields.insert(1, ("마감", end.strftime("%Y-%m-%d %H:%M (KST/JST)"), True))

                        send_discord_embed(
                            title=f"⏳ 마감 임박(24h) · {snap['title']}",
                            url=snap["url"],
                            fields=fields,
                            footer=f"handle: {handle}",
                            image_url=snap.get("image_url"),
                            author_name=snap.get("artist"),
                        )
                        notified["ending_24h"] = True
                        state[handle] = {"snap": snap, "notified": notified}

                except Exception:
                    log.debug("마감 파싱 실패", exc_info=True)

        time.sleep(SLEEP)

    save_state(state)
    log.info("========== FINDME JSON MONITOR END ==========")

if __name__ == "__main__":
    main()