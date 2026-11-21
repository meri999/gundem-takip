"""Resmî kurum duyuruları doğrudan kaynağından: TCMB (RSS), Hazine ve Maliye Bakanlığı (site REST API'si),
TÜİK (yayımlanan bültenler; takvim verisinden). Hepsi `items` tablosuna yazılır, panelde haber gibi görünür."""
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .topics import tag

UA = {"User-Agent": "Mozilla/5.0 (gundem-takip)"}
TR_AY = {"Oca": 1, "Şub": 2, "Mar": 3, "Nis": 4, "May": 5, "Haz": 6, "Tem": 7, "Ağu": 8, "Eyl": 9, "Eki": 10,
         "Kas": 11, "Ara": 12}
TCMB_ADRES = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Bottom+Menu/Diger/RSS/"
TCMB_BESLEMELER = ["Basin+Duyurulari", "PPK+Kararlari", "Veriler", "Yayinlar", "Baskanin+Konusmalari"]
HAZINE_API = "https://www.hmb.gov.tr/portal/v2/posts"
# Hazine'de rutin ihale, sınav ve ilan duyuruları panele alınmaz
HAZINE_DISLA = re.compile(r"ihale|sınav|ilan|evrak|giriş|mülakat|sertifika|kontrolör|müfettiş", re.I)
HAZINE_KATEGORI_DISLA = {"sinav-duyurulari", "hazine-kontrolorleri-kurulu-baskanligi", "vergi-denetim-kurulu"}


def _tr_tarih(s: str) -> str | None:
    """'16 Kas 2026 07:50:00' (İstanbul saati) -> UTC ISO."""
    m = re.match(r"(\d{1,2}) (\w{3})\w* (\d{4})(?: (\d{2}):(\d{2}))?", (s or "").strip())
    if not m or m.group(2) not in TR_AY:
        return None
    g, ay, yil, sa, dk = int(m.group(1)), TR_AY[m.group(2)], int(m.group(3)), int(m.group(4) or 9), int(m.group(5) or 0)
    return (datetime(yil, ay, g, sa, dk, tzinfo=timezone(timedelta(hours=3)))).astimezone(timezone.utc).isoformat()


def _yaz(con, kaynak: str, baslik: str, ozet: str, link: str, yayin: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    return con.execute(
        "INSERT OR IGNORE INTO items(source,category,title,summary,link,published,fetched,topics) VALUES(?,?,?,?,?,?,?,?)",
        (kaynak, "resmi", baslik, ozet, link, yayin, now, ",".join(tag(f"{baslik} {ozet}")))).rowcount


def collect_tcmb(con) -> int:
    n = 0
    for k in TCMB_BESLEMELER:
        feed = feedparser.parse(requests.get(TCMB_ADRES + k, headers=UA, timeout=30).content)
        for e in feed.entries:
            baslik = html.unescape(e.get("title", "")).strip()
            yayin = _tr_tarih(e.get("published") or e.get("updated"))
            link = (e.get("link") or "").replace("http://", "https://")
            if baslik and link and yayin:
                n += _yaz(con, "TCMB", baslik, "", link, yayin)
    print(f"TCMB: {n} yeni")
    return n


def collect_hazine(con) -> int:
    n = 0
    r = requests.get(HAZINE_API, params={"per_page": 50, "_fields": "date,link,title,class_list"}, headers=UA, timeout=30)
    for p in r.json():
        kat = {c[9:] for c in p.get("class_list", []) if c.startswith("category-")}
        baslik = html.unescape(p["title"]["rendered"]).strip()
        if kat & HAZINE_KATEGORI_DISLA or HAZINE_DISLA.search(baslik):
            continue
        yayin = datetime.fromisoformat(p["date"]).replace(tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc).isoformat()
        n += _yaz(con, "Hazine ve Maliye Bakanlığı", baslik, "", p["link"], yayin)
    print(f"Hazine ve Maliye Bakanlığı: {n} yeni")
    return n


def collect_tuik_yayinlari(con) -> int:
    """Son 14 günde yayımlanan TÜİK bültenleri (takvim tablosundan; bağlantıları hazır)."""
    n = 0
    bas = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    bit = datetime.now(timezone.utc).date().isoformat()
    for dt, ad, det, link in con.execute(
            "SELECT date,title,detail,link FROM events WHERE kind='tuik' AND date BETWEEN ? AND ? AND detail LIKE '%yayımlandı%'",
            (bas, bit)).fetchall():
        if not link:
            continue
        donem = (det or "").replace(" · yayımlandı", "").replace("yayımlandı", "").strip()
        baslik = f"TÜİK: {ad}" + (f" ({donem})" if donem else "")
        yayin = datetime.fromisoformat(dt).replace(hour=10, tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc).isoformat()
        n += _yaz(con, "TÜİK", baslik, "", link, yayin)
    print(f"TÜİK bültenleri: {n} yeni")
    return n
