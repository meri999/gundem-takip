"""Dünyadan think-tank yayınları: RSS beslemelerini toplar, konu etiketler ve data/gundem.db'ye yazar.

Kurumlar toplum, aile, demografi, yaşlanma, gençlik, eğitim, istihdam ve emek alanlarına göre seçilmiştir; güvenlik, dış politika
ve siyaset ağırlıklı kurumlar bilerek dışarıda bırakılmıştır. Yalnızca erişilebilen ve tarihli yayın veren beslemeler listededir.
Brookings, RAND, Chatham House, Carnegie, Urban Institute gibi kurumların beslemeleri botlara kapalı ya da tarihsiz olduğu için yok."""
import re
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .topics import tag

UA = {"User-Agent": "gundem-takip/0.1 (kurumsal gundem araci)"}
TAG_RE = re.compile(r"<[^>]+>")

THINKTANKLER = [
    # toplum, aile, demografi, yaşlanma, gençlik, eğitim, istihdam ve emek odaklı kurumlar
    ("Pew Research Center", "https://www.pewresearch.org/feed/"),
    ("Resolution Foundation", "https://www.resolutionfoundation.org/feed/"),
    ("Population Reference Bureau", "https://www.prb.org/feed/"),
    ("Guttmacher Institute", "https://www.guttmacher.org/rss.xml"),
    ("Our World in Data", "https://ourworldindata.org/atom.xml"),
    ("ILC UK (yaşlanma)", "https://ilcuk.org.uk/feed/"),
    ("Annie E. Casey Foundation", "https://www.aecf.org/rss"),
    ("Young Foundation", "https://youngfoundation.org/feed/"),
    ("Nuffield Foundation", "https://www.nuffieldfoundation.org/feed"),
    ("Learning and Work Institute", "https://learningandwork.org.uk/feed/"),
    ("Washington Center for Equitable Growth", "https://equitablegrowth.org/feed/"),
    ("Roosevelt Institute", "https://rooseveltinstitute.org/feed/"),
    ("W.E. Upjohn Institute", "https://www.upjohn.org/rss.xml"),
    ("New Economics Foundation", "https://neweconomics.org/rss"),
    ("Centre for Social Justice", "https://www.centreforsocialjustice.org.uk/feed"),
    ("CEPR (VoxEU)", "https://cepr.org/rss/vox-content"),
    ("AEI", "https://www.aei.org/feed/"),
    ("Aspen Institute", "https://www.aspeninstitute.org/feed/"),
]


def collect_thinktank(con) -> int:
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    for kurum, url in THINKTANKLER:
        try:
            r = requests.get(url, headers=UA, timeout=25)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        except Exception as e:
            print(f"[!] {kurum}: {e}")
            continue
        c = 0
        for e in feed.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            title = (e.get("title") or "").strip()
            link = e.get("link")
            if not (t and title and link):
                continue  # tarihsiz kayıt "güncel" sayılmaz
            ozet = TAG_RE.sub("", e.get("summary", "")).strip()[:400]
            tarih = datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            c += con.execute(
                "INSERT OR IGNORE INTO thinktank(kurum,baslik,ozet,link,tarih,konular,alindi) VALUES(?,?,?,?,?,?,?)",
                (kurum, title, ozet, link, tarih, ",".join(tag(f"{title} {ozet}")), now)).rowcount
        n += c
        print(f"{kurum}: {c} yeni")
    # 90 günden eski kayıtları temizle
    con.execute("DELETE FROM thinktank WHERE tarih < ?", ((datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),))
    return n
