"""Ay yaprağı biçiminde özel günler ve planlı olaylar takvimi.

Üç kaynak birleşir:
  1. SABIT: her yıl tekrarlanan özel günler (BM günleri, ulusal günler).
  2. PLANLI: tek tek doğrulanmış, tarihi bilinen gelecek olaylar (zirveler, faiz kararları, Meclis programı).
     Yeni olay eklemek için PLANLI listesine bir satır eklemek yeterlidir.
  3. Veritabanı (events): TÜİK yayınları ve TBMM komisyon toplantıları, her toplamada kendiliğinden gelir.
"""
import calendar
import html
from collections import defaultdict
from datetime import date, timedelta

from .topics import tag

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
         "Kasım", "Aralık"]
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# (ay, gün, ad, kapsam)  kapsam: TR | DUNYA
SABIT = [
    (1, 1, "Yılbaşı (resmî tatil) · Dünya Barış Günü", "TR"),
    (1, 24, "Uluslararası Eğitim Günü", "DUNYA"),
    (1, 27, "Holokost'u Anma Günü", "DUNYA"),
    (1, 28, "Dünya Veri Koruma Günü", "DUNYA"),
    (3, 8, "Dünya Kadınlar Günü", "DUNYA"),
    (4, 23, "Ulusal Egemenlik ve Çocuk Bayramı", "TR"),
    (5, 15, "Uluslararası Aile Günü", "DUNYA"),
    (6, 12, "Dünya Çocuk İşçiliğiyle Mücadele Günü", "DUNYA"),
    (7, 11, "Dünya Nüfus Günü", "DUNYA"),
    (8, 12, "Uluslararası Gençlik Günü", "DUNYA"),
    (9, 21, "Dünya Alzheimer Günü", "DUNYA"),
    (10, 1, "Dünya Yaşlılar Günü", "DUNYA"),
    (10, 10, "Dünya Ruh Sağlığı Günü", "DUNYA"),
    (10, 17, "Dünya Yoksullukla Mücadele Günü", "DUNYA"),
    (11, 20, "Dünya Çocuk Hakları Günü", "DUNYA"),
    (11, 24, "Öğretmenler Günü", "TR"),
    (11, 25, "Kadına Yönelik Şiddete Karşı Uluslararası Mücadele Günü", "DUNYA"),
    (11, 29, "Filistin Halkıyla Uluslararası Dayanışma Günü", "DUNYA"),
    (12, 1, "Dünya AIDS Günü", "DUNYA"),
    (12, 3, "Dünya Engelliler Günü", "DUNYA"),
    (12, 5, "Dünya Gönüllüler Günü", "DUNYA"),
    (12, 5, "Türk kadınına seçme ve seçilme hakkının tanınışı (1934)", "TR"),
    (12, 9, "Uluslararası Yolsuzlukla Mücadele Günü", "DUNYA"),
    (12, 10, "Dünya İnsan Hakları Günü", "DUNYA"),
    (12, 18, "Uluslararası Göçmenler Günü", "DUNYA"),
    (12, 20, "Uluslararası İnsani Dayanışma Günü", "DUNYA"),
    (12, 25, "Noel", "DUNYA"),
    (12, 31, "Yılbaşı gecesi", "TR"),
]

# (başlangıç, bitiş, ad, kapsam, kaynak)  kapsam: TR | DUNYA | MECLIS
# Kaynak sütunu, tarihin nereden doğrulandığını gösterir. Doğrulanmamış tarih eklemeyin.
PLANLI = [
    ("2026-11-09", "2026-11-20", "COP31 BM İklim Zirvesi, Antalya", "TR", "UNFCCC bildirimi"),
    ("2026-11-11", "2026-11-12", "COP31: devlet ve hükümet başkanları zirvesi", "TR", "UNFCCC bildirimi"),
    ("2026-12-07", "2026-12-20", "Genel Kurul: 2027 Merkezi Yönetim Bütçesi görüşmeleri", "MECLIS",
     "TBMM Danışma Kurulu önerisi (17.11.2026'da kabul)"),
    ("2026-12-09", "2026-12-09", "ABD Merkez Bankası (Fed) faiz kararı (toplantı 8-9 Aralık)", "DUNYA",
     "Fed 2026 takvimi"),
    ("2026-12-14", "2026-12-15", "G20 Liderler Zirvesi, Miami", "DUNYA", "ABD Hazine Bakanlığı"),
    ("2026-12-17", "2026-12-17", "Avrupa Merkez Bankası (ECB) faiz kararı", "DUNYA", "ECB takvimi"),
    ("2026-12-17", "2026-12-18", "AB Zirvesi (Avrupa Konseyi), Brüksel", "DUNYA", "AB Konseyi"),
    ("2027-01-18", "2027-01-22", "Dünya Ekonomik Forumu Yıllık Toplantısı, Davos", "DUNYA", "Davos/WEF"),
    ("2027-01-27", "2027-01-27", "ABD Merkez Bankası (Fed) faiz kararı (toplantı 26-27 Ocak)", "DUNYA",
     "Fed 2027 takvimi"),
]

ETIKET = {"TR": ("TR", "TR"), "DUNYA": ("DÜNYA", "DUNYA"), "MECLIS": ("TBMM", "MECLIS"),
          "TUIK": ("TÜİK", "YAYIN")}
# Hücreyi kalabalıklaştırmamak için konu etiketi olmayan TÜİK yayınlarından yalnız bunlar gösterilir
TUIK_ONEMLI = ("tüketici fiyat", "işgücü", "gayrisafi yurt içi", "dış ticaret", "nüfus", "doğum", "ölüm",
               "evlenme", "yoksulluk", "işsizlik", "yaşlı", "çocuk", "genç")


def _k(s) -> list:
    return [x for x in (s or "").split(",") if x]


def olaylari_topla(events, bas: date, bit: date, konular=None) -> dict:
    """{gün: [(sınıf, etiket, metin, konu_listesi), ...]} sözlüğü. `konular` verilirse yalnız o konularla ilgili olaylar."""
    out = defaultdict(list)

    for yil in range(bas.year, bit.year + 1):
        for ay, gun, ad, kapsam in SABIT:
            try:
                d = date(yil, ay, gun)
            except ValueError:
                continue
            if bas <= d <= bit:
                e, c = ETIKET[kapsam]
                out[d].append((c, e, ad, tag(ad)))

    for b, s, ad, kapsam, _kaynak in PLANLI:
        d, s_ = date.fromisoformat(b), date.fromisoformat(s)
        while d <= s_:
            if bas <= d <= bit:
                e, c = ETIKET[kapsam]
                out[d].append((c, e, ad, tag(ad)))
            d += timedelta(days=1)

    if events is not None and len(events):
        for r in events.itertuples():
            if not (bas <= r.date <= bit):
                continue
            if r.kind == "tuik" and r.source == "TÜİK":
                t = r.title.lower()
                if r.topics or any(k in t for k in TUIK_ONEMLI):
                    out[r.date].append(("YAYIN", "TÜİK", f"{r.title} ({r.detail.split(' · ')[0]})", _k(r.topics)))
            # Komisyon toplantıları takvimde gösterilmez; Meclis bölümlerinde yer alır.
    if konular:
        kset = set(konular)
        out = {d: [x for x in v if kset & set(x[3])] for d, v in out.items()}
    return out


def ay_html(yil: int, ay: int, olaylar: dict, bugun: date) -> str:
    cal = calendar.Calendar(firstweekday=0)
    satirlar = []
    for hafta in cal.monthdatescalendar(yil, ay):
        hucre = []
        for d in hafta:
            if d.month != ay:
                hucre.append('<td class="bos"></td>')
                continue
            sinif = []
            if d == bugun:
                sinif.append("bugun")
            elif d < bugun:
                sinif.append("gecmis")
            if d.weekday() >= 5:
                sinif.append("hs")
            ev = "".join(
                f'<div class="ev">&bull; {html.escape(t)}</div>'
                for c, e, t, _k_ in olaylar.get(d, []))
            hucre.append(f'<td class="{" ".join(sinif)}"><div class="gn">{d.day}</div>{ev}</td>')
        satirlar.append("<tr>" + "".join(hucre) + "</tr>")
    baslik = "".join(f"<th>{g}</th>" for g in GUNLER)
    return (f'<div class="ay-baslik">{AYLAR[ay]} {yil}</div>'
            f'<table class="takvim"><tr>{baslik}</tr>{"".join(satirlar)}</table>')


def uc_ay(bugun: date):
    """Bugünün ayı ve sonraki iki ay: [(yıl, ay), ...]"""
    y, m = bugun.year, bugun.month
    out = []
    for _ in range(3):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def aralik(bugun: date):
    (y0, m0), (y2, m2) = uc_ay(bugun)[0], uc_ay(bugun)[-1]
    return date(y0, m0, 1), date(y2, m2, calendar.monthrange(y2, m2)[1])
