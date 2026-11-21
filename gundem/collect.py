"""Veri toplama: python -m gundem.collect"""
import re
import time
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import feedparser
import requests

from . import config
from .db import connect
from .topics import tag

UA = {"User-Agent": "gundem-takip/0.1 (kurumsal gundem araci)"}
TAG_RE = re.compile(r"<[^>]+>")


def _iso(entry) -> str:
    for k in ("published_parsed", "updated_parsed"):
        v = entry.get(k)
        if v:
            return datetime(*v[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def collect_rss(con) -> int:
    n = 0
    now = datetime.now(timezone.utc).isoformat()
    for name, cat, url in config.RSS_SOURCES:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            feed = feedparser.parse(r.content)
        except Exception as e:
            print(f"[!] {name}: {e}")
            continue
        c = 0
        for e in feed.entries:
            title = (e.get("title") or "").strip()
            summ = TAG_RE.sub("", e.get("summary", ""))[:600]
            link = e.get("link")
            if not title or not link:
                continue
            topics = ",".join(tag(f"{title} {summ}"))
            cur = con.execute(
                "INSERT OR IGNORE INTO items(source,category,title,summary,link,published,fetched,topics)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (name, cat, title, summ, link, _iso(e), now, topics),
            )
            c += cur.rowcount
        print(f"{name}: {c} yeni")
        n += c
    return n


def collect_google_trends(con) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    n = 0
    for name, geo in config.GOOGLE_TRENDS:
        try:
            r = requests.get(f"https://trends.google.com/trending/rss?geo={geo}", headers=UA, timeout=20)
            root = ET.fromstring(r.content)
        except Exception as e:
            print(f"[!] {name}: {e}")
            continue
        ns = {"ht": "https://trends.google.com/trending/rss"}
        for i, item in enumerate(root.iter("item"), 1):
            term = (item.findtext("title") or "").strip()
            traffic = (item.findtext("ht:approx_traffic", namespaces=ns) or "0").replace("+", "").replace(",", "")
            val = float(traffic) if traffic.isdigit() else 0.0
            cur = con.execute("INSERT OR IGNORE INTO trends VALUES(?,?,?,?,?)", (today, name, i, term, val))
            n += cur.rowcount
        print(f"{name}: toplam {n}")
    return n


def collect_wikipedia(con) -> int:
    d = datetime.now(timezone.utc).date() - timedelta(days=2)  # veri 1-2 gün gecikmeli
    n = 0
    skip = ("Special:", "Özel:", "Main_Page", "Ana_Sayfa", "Vikipedi:", "Wikipedia:", "-")
    for name, proj in config.WIKI_PROJECTS:
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{proj}/all-access/{d:%Y/%m/%d}"
        try:
            arts = requests.get(url, headers=UA, timeout=20).json()["items"][0]["articles"]
        except Exception as e:
            print(f"[!] {name}: {e}")
            continue
        rank = 0
        for a in arts:
            if a["article"].startswith(skip):
                continue
            rank += 1
            if rank > 30:
                break
            cur = con.execute(
                "INSERT OR IGNORE INTO trends VALUES(?,?,?,?,?)",
                (d.isoformat(), name, rank, a["article"].replace("_", " "), a["views"]),
            )
            n += cur.rowcount
        print(f"{name}: {rank} madde")
    return n


def retag(con) -> int:
    """Konu sözlüğü değiştiğinde eski kayıtları da yeniden etiketler."""
    rows = con.execute("SELECT id, title, summary, topics FROM items").fetchall()
    n = 0
    for id_, title, summ, old in rows:
        new = ",".join(tag(f"{title} {summ}"))
        if new != old:
            con.execute("UPDATE items SET topics=? WHERE id=?", (new, id_))
            n += 1
    for rid, baslik, ozet, old in con.execute("SELECT rowid, baslik, ozet, konular FROM thinktank").fetchall():
        new = ",".join(tag(f"{baslik} {ozet}"))
        if new != old:
            con.execute("UPDATE thinktank SET konular=? WHERE rowid=?", (new, rid))
            n += 1
    for rid, baslik, ozet, old in con.execute("SELECT rowid, baslik, ozet, konular FROM kurulus").fetchall():
        new = ",".join(tag(f"{baslik} {ozet}"))
        if new != old:
            con.execute("UPDATE kurulus SET konular=? WHERE rowid=?", (new, rid))
            n += 1
    print(f"Yeniden etiketlenen: {n}")
    return n


def safe(label, fn, con):
    try:
        fn(con)
    except Exception as e:  # bir kaynak çökse de diğerleri çalışsın
        print(f"[!] {label}: {e}")


def main():
    from .events import collect_genel_kurul, collect_komisyon, collect_tuik_takvim
    from .thinktank import collect_thinktank
    from .kurulus import collect_kurulus
    from .resmi import collect_hazine, collect_tcmb, collect_tuik_yayinlari
    with connect() as con:
        collect_rss(con)
        safe("TBMM Genel Kurul", collect_genel_kurul, con)
        safe("TBMM Komisyon", collect_komisyon, con)
        safe("TÜİK takvim", collect_tuik_takvim, con)
        safe("TCMB duyuruları", collect_tcmb, con)
        safe("Hazine duyuruları", collect_hazine, con)
        safe("TÜİK bültenleri", collect_tuik_yayinlari, con)
        safe("Think-tank", collect_thinktank, con)
        safe("Kuruluş yayınları", collect_kurulus, con)
        retag(con)
        total = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        print("Toplam haber kaydı:", total)


if __name__ == "__main__":
    main()
