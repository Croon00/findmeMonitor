import re

# =========================
# VENDOR MAP (orig/en/kr)
# =========================
VENDOR_MAP = {
    # KAMITSUBAKI 주요
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
    "存流": ("存流", "ARU", "아루"),   # (공식 EN이 ARU로 쓰이는 케이스가 많음)
    "明透": ("明透", "ASU", "아스"),
    "跳亜": ("跳亜", "TOBIA", "토비아"),
    "梓川": ("梓川", "Azsagawa", "아즈사가와"),
    "詩道": ("詩道", "Shido", "시도"),
    "雨宿り": ("雨宿り", "Amayadori", "아마야도리"),

    # 프로젝트/브랜드/기타(스크린샷에 보임)
    "神椿市建設中。": ("神椿市建設中。", "KAMITSUBAKI CITY UNDER CONSTRUCTION", "카미츠바키시 건설중"),
    "KAMITSUBAKI STUDIO": ("KAMITSUBAKI STUDIO", "KAMITSUBAKI STUDIO", "카미츠바키 스튜디오"),
    "KAMITSUBAKI CARD GAME (神椿TCG)": ("KAMITSUBAKI CARD GAME (神椿TCG)", "KAMITSUBAKI CARD GAME", "카미츠바키 카드게임(카미츠바키 TCG)"),
    "THE VIRTUAL PLAYERS OF KAMITSUBAKI": ("THE VIRTUAL PLAYERS OF KAMITSUBAKI", "THE VIRTUAL PLAYERS OF KAMITSUBAKI", "카미츠바키의 버추얼 플레이어즈"),
    "御伽噺": ("御伽噺", "Otogibanashi", "오토기바나시"),

    # 크리에이터/아티스트(스크린샷에 보임)
    "DUSTCELL": ("DUSTCELL", "DUSTCELL", "더스트셀"),
    "EMA": ("EMA", "EMA", "에마"),
    "Guiano": ("Guiano", "Guiano", "구이아노"),
    "大沼パセリ": ("大沼パセリ", "Onuma Parsley", "오오누마 파슬리"),
    "LOLUET": ("LOLUET", "LOLUET", "로루엣"),
    "獅子志司": ("獅子志司", "Shishishishi", "시시시시"),
    "ど〜ぱみん": ("ど〜ぱみん", "Dopamine", "도~파민"),
    "Empty old City": ("Empty old City", "Empty old City", "엠프티 올드 시티"),
    "平田義久": ("平田義久", "Yoshihisa Hirata", "히라타 요시히사"),
    "P.U.O": ("P.U.O", "P.U.O", "피유오"),
    "ORESAMA": ("ORESAMA", "ORESAMA", "오레사마"),
    "Awairo": ("Awairo", "Awairo", "아와이로"),
    "水野あつ": ("水野あつ", "Atsu Mizuno", "미즈노 아츠"),
    "MIMI": ("MIMI", "MIMI", "미미"),
    "詩道": ("詩道", "Shido", "시도"),
    "teresaAI": ("te'resaAI", "te'resaAI", "테레사AI"),  # vendor 표기가 teresaAI로 올 수도 있어서 흡수
    "te'resa": ("te'resa", "te'resa", "테레사"),

    # “音楽的同位体 …” 시리즈(스크린샷에 보임)
    "音楽的同位体 可不(KAFU)": ("音楽的同位体 可不(KAFU)", "isotope KAFU", "동위체 카후"),
    "音楽的同位体 星界": ("音楽的同位体 星界", "isotope SEKAI", "동위체 세카이"),
    "音楽的同位体 裏命(RIME)": ("音楽的同位体 裏命(RIME)", "isotope RIME", "동위체 리메"),
    "音楽的同位体 狐子(COKO)": ("音楽的同位体 狐子(COKO)", "isotope COKO", "동위체 코코"),
    "音楽的同位体 羽累(HARU)": ("音楽的同位体 羽累(HARU)", "isotope HARU", "동위체 하루"),
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