"""Geçmiş günleri doldurur: python -m gundem.backfill [gün_sayısı]

Google Haberler RSS aramasını gün gün (after:/before:) sorgular. Yeniden çalıştırmak güvenlidir:
bitmiş (gün, sorgu) çiftleri atlanır, haber bağlantıları tekil tutulur."""
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone

import feedparser
import requests

from .db import connect
from .topics import tag

UA = {"User-Agent": "gundem-takip/0.1 (kurumsal gundem araci)"}

SOSYAL = ("nüfus OR doğurganlık OR doğum OR yaşlı OR emekli OR aile OR evlilik OR boşanma OR genç OR gençlik "
          "OR çocuk OR kadın OR engelli OR yoksulluk OR göç")
# (anahtar, kategori, sorgu)
SORGULAR = [
    ("sosyal", "turkiye", f"({SOSYAL})"),
    ("meclis_sosyal", "turkiye",
     "(TBMM OR Meclis OR milletvekili OR \"kanun teklifi\" OR \"Genel Kurul\") "
     "(aile OR genç OR gençlik OR yaşlı OR emekli OR nüfus OR doğum OR çocuk OR kadın OR engelli OR evlilik)"),
    ("meclis_genel", "turkiye", "(TBMM OR \"Genel Kurul\" OR \"kanun teklifi\" OR milletvekili)"),
    ("ekonomi", "ekonomi", "(enflasyon OR faiz OR \"asgari ücret\" OR \"Merkez Bankası\" OR bütçe OR TÜİK)"),
    ("dunya", "dunya", "(savaş OR ateşkes OR NATO OR \"Avrupa Birliği\" OR ABD OR Rusya OR Gazze OR Ukrayna)"),
    ("yz", "yz", "(\"yapay zeka\" OR ChatGPT OR OpenAI OR \"yapay zekâ\")"),
]


def _fetch(q: str, d: date):
    params = {"q": f"{q} after:{d.isoformat()} before:{(d + timedelta(days=1)).isoformat()}",
              "hl": "tr", "gl": "TR", "ceid": "TR:tr"}
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return feedparser.parse(r.content).entries


def main(days: int = 30):
    now = datetime.now(timezone.utc).isoformat()
    today = date.today()
    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS backfill(day TEXT, q TEXT, n INTEGER, PRIMARY KEY(day,q))")
        total = 0
        for back in range(days, -1, -1):
            d = today - timedelta(days=back)
            for key, cat, q in SORGULAR:
                # son iki gün her çalışmada yeniden çekilir (gün henüz bitmemiş olabilir)
                if back > 1 and con.execute("SELECT 1 FROM backfill WHERE day=? AND q=?",
                                            (d.isoformat(), key)).fetchone():
                    continue
                try:
                    entries = _fetch(q, d)
                except Exception as e:
                    print(f"[!] {d} {key}: {e}")
                    time.sleep(5)
                    continue
                n = 0
                for e in entries:
                    title = (e.get("title") or "").strip()
                    src = (e.get("source") or {}).get("title") or "Google Haberler"
                    if title.endswith(f" - {src}"):
                        title = title[: -len(src) - 3]
                    link = e.get("link")
                    if not title or not link:
                        continue
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat() \
                        if e.get("published_parsed") else d.isoformat()
                    n += con.execute(
                        "INSERT OR IGNORE INTO items(source,category,title,summary,link,published,fetched,topics)"
                        " VALUES(?,?,?,?,?,?,?,?)",
                        (src, cat, title, "", link, pub, now, ",".join(tag(title)))).rowcount
                con.execute("INSERT OR REPLACE INTO backfill VALUES(?,?,?)", (d.isoformat(), key, len(entries)))
                con.commit()
                total += n
                print(f"{d} {key:14s} {len(entries):3d} kayıt, {n} yeni", flush=True)
                time.sleep(1.5)
        print("Toplam yeni haber:", total)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
