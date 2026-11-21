"""Takvim kaynakları: TBMM (Genel Kurul gündemi, komisyonlar) ve TÜİK yayın takvimi."""
import html
import re
from datetime import date, timedelta

import requests

from . import config
from .topics import tag as _tag
from .topics import tr_cumle


def tag(text: str) -> list[str]:
    return [t for t in _tag(text) if t not in config.GENEL_KONULAR]

UA = {"User-Agent": "gundem-takip/0.1 (kurumsal gundem araci)"}
TBMM = "https://www.tbmm.gov.tr"
AYLAR = {"OCAK": 1, "ŞUBAT": 2, "MART": 3, "NİSAN": 4, "MAYIS": 5, "HAZİRAN": 6, "TEMMUZ": 7,
         "AĞUSTOS": 8, "EYLÜL": 9, "EKİM": 10, "KASIM": 11, "ARALIK": 12}
ANLASMA = re.compile(r"uygun bulunduğuna dair|onaylanması|Hükümeti ile|Cumhuriyeti ile", re.I)
KOM_ZAMAN = re.compile(r"(\d{2})\.(\d{2})\.(\d{4}) (\d{2}\.\d{2})")


def _text(raw: str) -> list[str]:
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", raw)).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", x).strip() for x in t.splitlines() if x.strip()]


def _get(url: str) -> requests.Response:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r


def _upper_tr(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


# ------------------------------------------------------------ TBMM Genel Kurul
def parse_genel_kurul(lines: list[str]):
    """-> (tarih, birleşim_no, [{sira, no, metin, anlasma}])"""
    dt = bno = None
    for i, l in enumerate(lines):
        if "BİRLEŞİM" in _upper_tr(l) and re.match(r"\d+", l) and i + 1 < len(lines):
            m = re.match(r"(\d{1,2}) (\S+) (\d{4})", _upper_tr(lines[i + 1]))
            if m and m.group(2) in AYLAR:
                bno = re.match(r"(\d+)", l).group(1)
                dt = date(int(m.group(3)), AYLAR[m.group(2)], int(m.group(1)))
                break
    # sayfa aynı gündemi iki kez içerir; "7 KANUN TEKLİFLERİ..." başlığı sonrası asıl liste gelir
    starts = [i for i, l in enumerate(lines)
              if _upper_tr(l).startswith("KANUN TEKLİFLERİ İLE KOMİSYONLARDAN GELEN DİĞER İŞLER")]
    if not starts:
        return dt, bno, []
    items, cur = [], None
    for l in lines[starts[-1] + 1:]:
        u = _upper_tr(l)
        if u.startswith(("TÜRKİYE BÜYÜK MİLLET", "KOMİSYON TOPLANTILARI", "GRUP ÖNERİSİ", "DANIŞMA KURULU",
                         "--> TBMM TV", "AÇIK OYLAMAYA", "TBMM TV")):
            break
        if re.fullmatch(r"\d+\.", l):
            if cur:
                items.append(cur)
            cur = []
        elif cur is not None and l not in ("(**)", "(X)", "(*)", "(***)", "(S."):
            cur.append(l)
    if cur:
        items.append(cur)
    out = []
    for k, parts in enumerate(items, 1):
        txt = " ".join(parts)
        m = re.search(r"Sayısı:\s*(\d+)\)", txt)
        no = m.group(1) if m else ""
        txt = re.sub(r"^.*?Sayısı:\s*\d+\)\s*", "", txt).strip()
        txt = re.sub(r"\s*İçtüzüğün \d+.{0,6}maddesine göre.*$", "", txt).strip()
        out.append({"sira": k, "no": no, "metin": txt, "anlasma": bool(ANLASMA.search(txt))})
    return dt, bno, out


def collect_genel_kurul(con) -> int:
    dt, bno, items = parse_genel_kurul(_text(_get(f"{TBMM}/Gundem/GenelKurulGundemi").text))
    if not dt:
        print("[!] Genel Kurul tarihi çözülemedi")
        return 0
    n = 0
    for it in items:
        tur = "Uluslararası anlaşma" if it["anlasma"] else "Kanun teklifi"
        title = f"[S.Sayısı {it['no']}] {it['metin']}" if it["no"] else it["metin"]
        det = f"{tur} · {bno}. birleşim gündeminde sıra {it['sira']}"
        n += con.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?)",
                         (dt.isoformat(), "tbmm_genel", "TBMM Genel Kurul", title[:600], det,
                          f"{TBMM}/Gundem/GenelKurulGundemi", ",".join(tag(it["metin"])))).rowcount
    print(f"TBMM Genel Kurul ({dt}, {bno}. birleşim): {len(items)} madde, {n} yeni")
    return n


# ------------------------------------------------------------ TBMM Komisyonlar
def parse_komisyon(lines: list[str]):
    """Her toplantı: komisyon adı (büyük harf) / 'GG.AA.YYYY SS.DD' / salon / gündem satırları."""
    out = []
    i = next((k for k, l in enumerate(lines) if _upper_tr(l).startswith("KOMİSYON GÜNDEMLERİ")), 0) + 1
    while i < len(lines) - 2:
        m = KOM_ZAMAN.fullmatch(lines[i + 1])
        if not m:
            i += 1
            continue
        j = i + 3
        gundem = []
        while j < len(lines) and not (j + 1 < len(lines) and KOM_ZAMAN.fullmatch(lines[j + 1])) \
                and not lines[j].startswith("--> TBMM TV"):
            gundem.append(lines[j])
            j += 1
        out.append({"komisyon": lines[i], "saat": m.group(4),
                    "tarih": date(int(m.group(3)), int(m.group(2)), int(m.group(1))),
                    "yer": lines[i + 2], "gundem": " ".join(gundem)[:900]})
        i = j
    return out


def collect_komisyon(con) -> int:
    rows = parse_komisyon(_text(_get(f"{TBMM}/Gundem/KomisyonGundemleri").text))
    n = 0
    for r in rows:
        title = f"{tr_cumle(r['komisyon'])} · {r['saat']}"
        n += con.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?)",
                         (r["tarih"].isoformat(), "tbmm_komisyon", "TBMM Komisyon", title, r["gundem"],
                          f"{TBMM}/Gundem/KomisyonGundemleri",
                          ",".join(tag(r["gundem"] + " " + r["komisyon"])))).rowcount
    print(f"TBMM Komisyon: {len(rows)} toplantı, {n} yeni")
    return n


# ------------------------------------------------------------ TÜİK takvimi
def collect_tuik_takvim(con) -> int:
    """TÜİK'in Ulusal Veri Yayımlama Takvimi sayfasının kendi kullandığı herkese açık JSON'u."""
    n = 0
    today = date.today()
    for yil in sorted({today.year, (today + timedelta(days=100)).year}):
        try:
            d = _get(f"https://www.tuik.gov.tr/Kurumsal/GetYillikHaberBulteniListesi?yil={yil}").json()
        except Exception as e:
            print(f"[!] TÜİK takvim {yil}: {e}")
            continue
        for lst, durum in (("yayindaOlmayanlarList", "bekleniyor"), ("yayindaOlanlarList", "yayımlandı")):
            for x in d.get(lst, []):
                if x.get("sorumluKisaAd") not in config.TAKVIM_KURUMLARI:
                    continue
                dt = (x.get("gTarih") or "")[:10]
                if not dt or dt < (today - timedelta(days=90)).isoformat():
                    continue
                ad = (x.get("adi") or "").strip()
                det = " · ".join(p for p in (x.get("donemi"), durum) if p)
                n += con.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?)",
                                 (dt, "tuik", x["sorumluKisaAd"], ad, det, x.get("link") or "",
                                  ",".join(tag(ad)))).rowcount
    print(f"TÜİK takvim: {n} yeni")
    return n
