import re

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

    # ✅ 방어: 값이 3개 이상이면 앞 3개만 사용
    def fmt(t):
        if isinstance(t, tuple) and len(t) >= 3:
            o, e, k = t[0], t[1], t[2]
            return f"{o} / {e} / {k}"
        return None

    if v in VENDOR_MAP:
        out = fmt(VENDOR_MAP[v])
        if out:
            return out

    parts = [p.strip() for p in v.split("/") if p.strip()]
    for p in [v] + parts:
        if p in VENDOR_MAP:
            out = fmt(VENDOR_MAP[p])
            if out:
                return out

    return v or "(unknown)"