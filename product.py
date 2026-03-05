from datetime import datetime
from dateutil import parser as dtparser
from config import BASE, JST
from parsers import strip_html_to_text, parse_order_window_from_text

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