import time
import os
import re
from datetime import datetime, timedelta
from dateutil import parser as dtparser

from config import (
    PRODUCTS_JSON_URL, FETCH_PRODUCT_PAGE, FETCH_PAGE_SLEEP, SLEEP,
    INIT_ONLY, PRUNE_SOLD_OUT_FROM_STATE, ALERT_SOLDOUT_AND_RESTOCK, JST
)
from logger_setup import setup_logger
from http_client import http_get_json, http_get_text
from state_store import load_state, save_state
from parsers import strip_html_to_text, get_og_image_from_html, jp_date_to_kr
from product import (
    product_url, pick_sort_key, is_available, build_snapshot
)
from discord_client import send_discord_embed

log = setup_logger()

# Discord embed colors
COLOR_BLUE = 0x3498DB
COLOR_RED = 0xED4245
COLOR_GREEN = 0x57F287
COLOR_YELLOW = 0xFEE75C


def fetch_product_page_extra(handle: str) -> dict:
    url = product_url(handle)
    try:
        html = http_get_text(url)
        text = strip_html_to_text(html)
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

        # STOCK ITEM NOTICE (JP -> KR) ✅ 둘 다 있을 때만!
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


def main():
    log.info("========== FINDME JSON MONITOR START ==========")
    log.info(f"INIT_ONLY={INIT_ONLY}")
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

    # ✅ 오래된 -> 최신 순서로 처리
    products.sort(key=pick_sort_key, reverse=False)

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
                    new_color = COLOR_GREEN if snap.get("stock_notice_kr") else COLOR_BLUE
                    send_discord_embed(
                        title=f"🆕 NEW · {snap['title']}",
                        url=snap["url"],
                        fields=build_fields_for_snap(snap),
                        footer=f"handle: {handle}",
                        image_url=snap.get("image_url"),
                        author_name=snap.get("artist"),
                        color=new_color,
                    )
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
                        color=COLOR_RED,
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
                            color=COLOR_YELLOW,
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
