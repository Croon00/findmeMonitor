import requests
from datetime import datetime
from config import DRY_RUN, DISCORD_WEBHOOK, TIMEOUT, JST
from logger_setup import setup_logger
from vendors import vendor_display

log = setup_logger()

def send_discord_embed(
    title: str,
    url: str,
    fields: list[tuple[str, str, bool]] | None = None,
    description: str | None = None,
    footer: str | None = None,
    image_url: str | None = None,
    author_name: str | None = None,
    color: int | None = None,
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

    if color is not None:
        embed["color"] = color

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
