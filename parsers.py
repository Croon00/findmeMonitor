# parsers.py
import re

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

def get_og_image_from_html(html: str) -> str | None:
    if not html:
        return None
    m = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        html,
        flags=re.I
    )
    return m.group(1).strip() if m else None

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