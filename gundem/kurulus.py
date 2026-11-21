"""Uluslararası kuruluş yayınları (IMF, ILO, Dünya Bankası, Deloitte): data/gundem.db içindeki `kurulus` tablosuna yazar.

Think-tank'lerden ayrı tutulur. Çalışan resmî RSS beslemesi olmadığı için üç kuruluş farklı yoldan alınır:
- ILO: ilo.org/publications sayfasındaki tarihli yayın kartları ayrıştırılır (sayfa düzeni değişirse bozulabilir).
- IMF: imf.org botlara kapalı (403). Google Haberler'in `site:imf.org` aramalarından, yayın serilerine göre alınır.
- Deloitte: çalışan RSS yok; Google Haberler `site:deloitte.com` aramalarından alınır.
- Dünya Bankası: resmî API ve OKR beslemesi güncel kayıt vermiyor. Google Haberler `site:worldbank.org` aramalarından alınır.
Google kaynaklı kayıtlarda tarih, sayfanın dizine girdiği tarihtir; eski arşiv sayfalarını elemek için başlıktaki eski yıllar süzülür."""
import html
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import requests

from .topics import tag

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GOOGLE = "https://news.google.com/rss/search"
TARAMA_GUN = 35  # Google aramalarında geriye bakılan gün sayısı (yaklaşık bir ay)
ANA_RAPOR_GUN = 100  # yılda birkaç kez çıkan ana raporlar için geriye bakılan gün sayısı
# Ana raporlar: seyrek çıktıkları için sayfada 90 güne kadar gösterilir
ANA_RAPOR = (r"world economic outlook|global financial stability report|fiscal monitor|regional economic outlook|"
             r"external sector report|global economic prospects|world development report|poverty,? prosperity,? and planet|"
             r"world employment and social outlook|employment and social trends|global employment trends|"
             r"global wage report|world social protection report|human capital trends|gen z and millennial survey|"
             r"global impact report")

IMF_ARAMALAR = [
    "World Economic Outlook", "Global Financial Stability Report", "Fiscal Monitor", "Regional Economic Outlook",
    "External Sector Report", "working paper", "staff discussion note", "Finance & Development", "blog", "report", "trade", "tariffs",
]
DELOITTE_ARAMALAR = [
    "human capital", "human resources", "workforce", "global impact", "artificial intelligence", "generative AI",
    "survey", "insights", "report", "trade", "tariffs",
]
WB_ARAMALAR = [
    "report", "Global Economic Prospects", "Poverty Prosperity Planet", "policy research working paper",
    "jobs", "Business Ready", "World Development Report", "blog", "trade", "tariffs", "labor market",
]

# Deloitte sitesi çoğunlukla iş ilanı ve hizmet sayfası içerir; yalnızca rapor/araştırma türü başlıklar alınır
DELOITTE_DAHIL = re.compile(r"survey|report|trends|outlook|study|index|research|human capital|workforce|gen z|millennial|"
                            r"impact|future of|insights|AI|generative|artificial|talent|skills|ageing|aging|trade|tariff", re.I)
DELOITTE_DISLA = re.compile(r"job|career|\||original advantage|similar|hiring|apply|engineer|developer|consultant|specialist|associate|analyst|partner,|editor|walk in|manager|director|intern\b", re.I)

ANA_RAPOR_ARAMA = {
    "imf.org": ["World Economic Outlook", "Global Financial Stability Report", "Fiscal Monitor"],
    "worldbank.org": ["Global Economic Prospects", "Poverty Prosperity Planet", "World Development Report"],
    "deloitte.com": ["Global Human Capital Trends", "Gen Z and Millennial Survey", "Global Impact Report"],
}

# Ülke düzeyindeki rutin belgeler ve site gezinme sayfaları listeye girmez
GURULTU = re.compile(
    r"article iv|end-of-mission|staff visit|staff[- ]level|staff completes|staff concludes|staff reaches|executive board|"
    r"statement by|press release;|careers|^authors?\b|all authors|untitled|^imf blogs|open knowledge|^pfm blog|"
    r"^-|world bank group$|^search|^home$|elibrary|open data|libguides|database|b-ready|technical assistance|"
    r"selected issues|country opinion survey|current (us)?\$|current international|\bppp\b|dashboard|data catalog|"
    r"check out this job|job title|application process|official rules|\| (delhi|mumbai|bengaluru|hyderabad|pune|gurgaon|"
    r"kolkata|chennai)|^(senior |lead |principal |staff )?(manager|consultant|analyst|engineer|specialist|developer|"
    r"architect|director|associate|intern|auditor)|(senior|lead|principal) (consultant|manager|analyst|engineer|"
    r"specialist|developer|architect)|press briefing|roundtable|transcript|^podcast|^video|webinar|"
    r"services$|solutions$|^industries|^about deloitte|contact us|^deloitte (global|us|uk)$|% of gdp|\(% of|^event|^population$|\(\w+ 20\d\d\) - |^\w+$|"
    r"data explorer|^topics?\b|^about\b|^contact|^news\b|^publications?$|^research$|^data$|^\W*$", re.I)
ESKI_YIL = re.compile(r"\b(19\d\d|20[01]\d|202[0-5])\b")


def _ekle(con, kurum, baslik, ozet, link, tarih, now) -> int:
    return con.execute(
        "INSERT OR IGNORE INTO kurulus(kurum,baslik,ozet,link,tarih,konular,alindi) VALUES(?,?,?,?,?,?,?)",
        (kurum, baslik, ozet, link, tarih.isoformat(), ",".join(tag(f"{baslik} {ozet}")), now)).rowcount


def _istek(q: str, gun: int):
    """Google Haberler araması; hız sınırına (429) takılırsa bir kez bekleyip yeniden dener."""
    for deneme in range(2):
        r = requests.get(GOOGLE, params={"q": f"{q} when:{gun}d", "hl": "en", "gl": "US", "ceid": "US:en"},
                         headers=UA, timeout=25)
        if r.status_code == 429 and deneme == 0:
            time.sleep(20)
            continue
        r.raise_for_status()
        return feedparser.parse(r.content)


def _google(con, kurum, domain, aramalar, now) -> int:
    c = 0
    sorgular = [(f"site:{domain} {q}", TARAMA_GUN) for q in aramalar] +                [(f"site:{domain} {q}", ANA_RAPOR_GUN) for q in ANA_RAPOR_ARAMA[domain]]
    for q, gun in sorgular:
        time.sleep(2)
        sinir = datetime.now(timezone.utc) - timedelta(days=gun)
        try:
            feed = _istek(q, gun)
        except Exception as e:
            print(f"[!] {kurum} ({q}): {e}")
            continue
        for e in feed.entries:
            t = e.get("published_parsed")
            baslik = html.unescape((e.get("title") or "").strip())
            kaynak = (e.get("source") or {}).get("title", "")
            if kaynak and baslik.endswith(" - " + kaynak):
                baslik = baslik[: -len(" - " + kaynak)].strip()
            if not (t and baslik and e.get("link")) or GURULTU.search(baslik):
                continue
            if kurum == "Deloitte" and (DELOITTE_DISLA.search(baslik) or not DELOITTE_DAHIL.search(baslik)):
                continue
            if ESKI_YIL.search(baslik) and "2026" not in baslik:
                continue  # eski arşiv sayfası, yeni tarihle dizine girmiş
            tarih = datetime(*t[:6], tzinfo=timezone.utc)
            if tarih < sinir or (gun == ANA_RAPOR_GUN and not re.search(ANA_RAPOR, baslik, re.I)):
                continue
            c += _ekle(con, kurum, baslik, "", e["link"], tarih, now)
    return c


def _ilo(con, now) -> int:
    r = requests.get("https://www.ilo.org/publications", headers=UA, timeout=25)
    r.raise_for_status()
    sayfa = r.content.decode("utf-8", errors="replace")
    c = 0
    for blk in sayfa.split('class="ilo--card ')[1:]:
        link = re.search(r'class="ilo--card--link"\s+href="([^"]+)"', blk)
        baslik = re.search(r'ilo--card--title">(.*?)</p>', blk, re.S)
        zaman = re.search(r'datetime="(\d{9,})"', blk)
        tur = re.search(r'ilo--card--eyebrow">(.*?)</p>', blk, re.S)
        if not (link and baslik and zaman) or "/meetings-and-events/" in link.group(1):
            continue  # tarihsiz ya da etkinlik kartı yayın değildir
        tarih = datetime.fromtimestamp(int(zaman.group(1)), tz=timezone.utc)
        if tarih > datetime.now(timezone.utc):
            continue
        ozet = html.unescape(re.sub(r"<[^>]+>|\s+", " ", tur.group(1))).strip() if tur else ""
        c += _ekle(con, "ILO", html.unescape(baslik.group(1)).strip(), ozet,
                   urljoin("https://www.ilo.org", link.group(1)), tarih, now)
    return c


def collect_kurulus(con) -> int:
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for kurum, fn in (("ILO", lambda: _ilo(con, now)),
                      ("IMF", lambda: _google(con, "IMF", "imf.org", IMF_ARAMALAR, now)),
                      ("Dünya Bankası", lambda: _google(con, "Dünya Bankası", "worldbank.org", WB_ARAMALAR, now)),
                      ("Deloitte", lambda: _google(con, "Deloitte", "deloitte.com", DELOITTE_ARAMALAR, now))):
        try:
            c = fn()
        except Exception as e:
            print(f"[!] {kurum}: {e}")
            continue
        n += c
        print(f"{kurum}: {c} yeni")
    con.execute("DELETE FROM kurulus WHERE tarih < ?", ((datetime.now(timezone.utc) - timedelta(days=ANA_RAPOR_GUN)).isoformat(),))
    return n


if __name__ == "__main__":
    from .db import connect
    with connect() as con:
        collect_kurulus(con)
