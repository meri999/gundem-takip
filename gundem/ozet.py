"""Haftalık özet, yayın fırsatları ve indirilebilir Word notu (panel paleti).

Her şey kategori düzeyindedir (Toplum, Aile, Demografi ...). İnce konu adları yalnızca gerekçe cümlesinde geçer."""
import io
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from . import takvim
from .config import KATEGORILER, TOPICS
from .db import connect
from .forecast import agirlik, kapsama, olcum, topic_daily, yon
from .topics import kategoriler_of, meclis_haberi, tr_cumle, tr_lower


def _has(s, wanted) -> bool:
    return any(t in (s or "").split(",") for t in wanted)


def genel_kurul_basligi(title: str) -> str:
    """'[S.Sayısı 158] ...' önekini ekranda göstermez."""
    return re.sub(r"^\[S\.Sayısı \d+\]\s*", "", title or "")


def tur_adi(etiket: str) -> str:
    """Takvim etiketini okunur tür adına çevirir. TÜİK satırlarının istatistik yayını olduğu açık yazılır."""
    return {"TÜİK": "İstatistik yayını (TÜİK)", "TR": "Türkiye", "DÜNYA": "Dünya",
            "TBMM": "Meclis"}.get(etiket, etiket)


def son_guncelleme() -> str:
    """Son veri toplama zamanı (İstanbul saati), ör. '19.11.2026 11:53'."""
    try:
        with connect() as con:
            v = con.execute("SELECT MAX(fetched) FROM items").fetchone()[0]
        if not v:
            return "bilinmiyor"
        return datetime.fromisoformat(v).astimezone(ZoneInfo("Europe/Istanbul")).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "bilinmiyor"


def degisim_metni(son: int, onc: int) -> str:
    """Okunur değişim ifadesi. Önceki hafta çok küçükse yüzde verilmez."""
    if onc < 10:
        return ""
    d = (son - onc) / onc * 100
    if abs(d) < 5:
        return "geçen haftayla aynı düzeyde"
    return f"geçen haftaya göre %{abs(d):.0f} " + ("arttı" if d > 0 else "azaldı")


def kat_seri(haber: pd.DataFrame, topics: list, gun: int = 60) -> pd.Series:
    """Kategorinin günlük haber sayısı (kapsama düzeltmeli, tutarlı kaynak)."""
    base = olcum(haber[~haber["source"].str.startswith("arXiv")])
    kts = kapsama(haber)
    h = base[base["topics"].apply(lambda s: _has(s, topics))]
    bugun = date.today()
    idx = pd.date_range(bugun - timedelta(days=gun), bugun - timedelta(days=1)).date  # bugün henüz yarım
    return agirlik(h, kts).groupby(h["day"]).sum().reindex(idx, fill_value=0.0)


def kat_say(haber: pd.DataFrame, topics: list, bugun: date) -> dict:
    """Son 7 gün, önceki 7 gün ve beklenen yön."""
    s = kat_seri(haber, topics)
    son = int(round(s[[d for d in s.index if bugun - timedelta(days=7) <= d < bugun]].sum()))
    onc = int(round(s[[d for d in s.index if bugun - timedelta(days=14) <= d < bugun - timedelta(days=7)]].sum()))
    return {"son": son, "onc": onc, "metin": degisim_metni(son, onc), "yon": yon(s),
            "artan": en_cok_artan(haber, topics, bugun) if onc >= 10 and son > onc * 1.2 else None}


def en_cok_artan(haber, topics, bugun) -> str | None:
    """Kategori içinde haftalık artışı en belirgin ince konu (yalnızca gerekçe cümlesi için)."""
    daily = topic_daily(haber)
    if daily.empty:
        return None
    gun = pd.Index([x.date() for x in daily.index])
    en, en_fark = None, 0.0
    for t in topics:
        if t not in daily.columns:
            continue
        s = float(daily.loc[(gun >= bugun - timedelta(days=7)) & (gun < bugun), t].sum())
        o = float(daily.loc[(gun >= bugun - timedelta(days=14)) & (gun < bugun - timedelta(days=7)), t].sum())
        if o >= 5 and s >= 10 and (s - o) / o > en_fark:
            en, en_fark = t, (s - o) / o
    return en


def yayin_firsatlari(haber, events, bugun: date, kategoriler: dict, ufuk: int = 14, n: int = 3,
                     min_puan: float = 2.0) -> list[dict]:
    """Haber artışı, yaklaşan özel gün, TÜİK yayını ve Meclis gündemi birleşen kategorileri sıralar.

    Puan: haber artışı 0-4, özel gün/etkinlik 3 (7 gün içindeyse 4), TÜİK yayını 2, Meclis 0,75 x kayıt (en çok 3).
    6 ve üstü "Güçlü", 2-6 arası "Orta". 2 altı listelenmez. Sezgiseldir, kesin tahmin değildir."""
    ol = takvim.olaylari_topla(events, bugun, bugun + timedelta(days=ufuk))
    out = []
    for ad, topics in kategoriler.items():
        ts = set(topics)
        kt = kat_say(haber, topics, bugun)
        puan, nedenler = 0.0, []
        if kt["onc"] >= 10 and kt["son"] >= 10 and kt["son"] > kt["onc"]:
            d = (kt["son"] - kt["onc"]) / kt["onc"] * 100
            puan += min(d, 100) / 25
            en = en_cok_artan(haber, topics, bugun)
            nedenler.append(f"Haber yoğunluğu geçen haftaya göre %{d:.0f} arttı" + (f" (en çok: {en})" if en else ""))
        gunler = sorted((d, t) for d, lst in ol.items() for c, e, t, ks in lst if c in ("TR", "DUNYA") and ts & set(ks))
        if gunler:
            d, t = gunler[0]
            k = (d - bugun).days
            puan += 4 if k <= 7 else 3
            nedenler.append(f"{t} ({d:%d.%m.%Y}, " + ("bugün" if k == 0 else f"{k} gün sonra") + ")")
        tk = sorted((d, t) for d, lst in ol.items() for c, e, t, ks in lst if e == "TÜİK" and ts & set(ks))
        if tk:
            puan += 2
            nedenler.append(f"TÜİK yayını: {tk[0][1]} ({tk[0][0]:%d.%m.%Y})")
        mec = 0
        if events is not None and len(events):
            e = events[events["topics"].apply(lambda s: _has(s, topics))]
            mec = int((((e["kind"] == "tbmm_genel") & ~e["detail"].str.startswith("Uluslararası"))
                       | ((e["kind"] == "tbmm_komisyon") & (e["date"] >= bugun)
                          & (e["date"] <= bugun + timedelta(days=ufuk)))).sum())
        if mec:
            puan += min(mec, 4) * 0.75
            nedenler.append(f"Meclis gündeminde {mec} madde ya da komisyon toplantısı")
        if puan >= min_puan and (nedenler or min_puan < 0):
            if not nedenler:
                nedenler = ["Bu hafta takvimde ya da Meclis’te ayrı bir gelişme yok; son haberler aşağıda"]
            out.append({"kategori": ad, "seviye": "Güçlü" if puan >= 6 else "Orta" if puan >= 2 else "İzleme",
                        "puan": puan, "nedenler": nedenler})
    return sorted(out, key=lambda x: -x["puan"])[:n]


_DURAK = set("için gibi daha çok kadar sonra önce ancak ama olan oldu olarak nasıl neden dakika son flaş".split())


def _kelimeler(t: str) -> set:
    return {w for w in re.findall(r"\w{4,}", tr_lower(t)) if w not in _DURAK}


def _oneler(d: pd.DataFrame, n: int) -> list[dict]:
    """Önemli haberleri seçer: benzer başlıkları aynı olay sayar, en çok kaynakta yer alan olay öne çıkar.
    Eşitlikte en yeni olan gelir. Başlık olarak olayın en yeni haberi gösterilir."""
    kumeler = []  # {"k": kelime kümesi, "uye": [satırlar]}
    for r in d.sort_values("published", ascending=False).itertuples():
        k = _kelimeler(r.title)
        if not k:
            continue
        for c in kumeler:
            if len(k & c["k"]) / len(k | c["k"]) >= 0.45:
                c["uye"].append(r)
                c["k"] |= k
                break
        else:
            kumeler.append({"k": set(k), "uye": [r]})

    def skor(c):
        return len({x.source for x in c["uye"]}), c["uye"][0].published

    out = []
    for c in sorted(kumeler, key=skor, reverse=True)[:n]:
        ilk = c["uye"][0]
        diger = len({x.source for x in c["uye"]}) - 1
        out.append({"baslik": ilk.title, "link": ilk.link,
                    "kaynak": ilk.source + (f" ve {diger} kaynak daha" if diger > 0 else "")})
    return out


def _basliklar(haber, topics, bugun, n=2, gun=3):
    d = haber[(haber["day"] >= bugun - timedelta(days=gun)) & haber["topics"].apply(lambda s: _has(s, topics))]
    return _oneler(d, n)


def meclis_kayitlari(events, bugun: date, topics=None, n_gk: int = 5, n_kom: int = 5, gun_kom: int = 7):
    """(Genel Kurul maddeleri, komisyon toplantıları). `topics` verilirse yalnız o konularla ilgili olanlar."""
    if events is None or not len(events):
        return [], []
    ev = events if not topics else events[events["topics"].apply(lambda s: _has(s, topics))]
    gk = ev[(ev["kind"] == "tbmm_genel") & ~ev["detail"].str.startswith("Uluslararası") & (ev["topics"] != "")]
    km = ev[(ev["kind"] == "tbmm_komisyon") & (ev["date"] >= bugun) & (ev["date"] <= bugun + timedelta(days=gun_kom))
            & (ev["topics"] != "")]
    return ([genel_kurul_basligi(r.title) for r in gk.head(n_gk).itertuples()],
            [{"tarih": r.date, "baslik": r.title} for r in km.sort_values("date").head(n_kom).itertuples()])


def meclis_yansimalari(haber, topics, bugun, gun: int = 7, n: int = 2):
    """Başlığında Meclis atfı olan, bu konuyla ilgili önemli haberler."""
    d = haber[(haber["day"] >= bugun - timedelta(days=gun)) & haber["topics"].apply(lambda s: _has(s, topics))]
    return _oneler(d[d["title"].apply(meclis_haberi)], n)


def hafta_ozeti(haber, events, bugun: date, kategoriler: dict, sabit=(), haric=()) -> dict:
    """Ekran ve Word notu için ortak veri yapısı. Meclis bilgisi her kategorinin içindedir.
    `haric` kategoriler hiç gösterilmez. `sabit` kategoriler puanı düşük olsa da kartlarda her zaman yer alır."""
    kategoriler = {k: v for k, v in kategoriler.items() if k not in haric}
    kat = []
    for ad, topics in kategoriler.items():
        kt = kat_say(haber, topics, bugun)
        gk, kom = meclis_kayitlari(events, bugun, topics, n_gk=3, n_kom=3, gun_kom=7)
        kat.append({"ad": ad, **kt, "basliklar": _basliklar(haber, topics, bugun, n=3),
                    "genel_kurul": gk, "komisyon": kom,
                    "meclis_haberleri": meclis_yansimalari(haber, topics, bugun)})
    ol = takvim.olaylari_topla(events, bugun, bugun + timedelta(days=14))
    tak = [{"tarih": d, "tur": tur_adi(e), "konu": ", ".join(kategoriler_of(",".join(k))), "olay": t}
           for d in sorted(ol) for c, e, t, k in ol[d]]
    sabit = [k for k in sabit if k in kategoriler]
    digerleri = {k: v for k, v in kategoriler.items() if k not in sabit}
    firsatlar = yayin_firsatlari(haber, events, bugun, digerleri, n=max(3 - len(sabit), 1))
    for k in sabit:
        firsatlar += yayin_firsatlari(haber, events, bugun, {k: kategoriler[k]}, n=1, min_puan=-1)
    firsatlar = sorted(firsatlar, key=lambda x: -x["puan"])
    detay = {k["ad"]: k for k in kat}
    for f in firsatlar:
        f["detay"] = detay[f["kategori"]]  # kartın altında gösterilecek haber ve Meclis bilgisi
    return {"bugun": bugun, "kategoriler": kat, "takvim": tak, "firsatlar": firsatlar}


# ----------------------------------------------------------------------------- Think-tank
TT_KONULARI = list(KATEGORILER)
# Bir yayın birden çok kategoriye uyarsa en özgül olana yazılır (tekrar olmasın)
_TT_ONCELIK = ["Demografi", "Gençlik ve eğitim", "Sağlık", "Yapay zekâ ve teknoloji", "Emek piyasası",
               "Dış ticaret ve döviz piyasası", "Makroekonomi", "Kalkınma", "Toplum ve aile"]


def thinktank_gruplari(df: pd.DataFrame) -> dict:
    """Think-tank yayınlarını konuya göre ayırır: {kategori: DataFrame}. Konusu olmayan yayın gösterilmez."""
    atama = {}
    for r in df.itertuples():
        uyan = [k for k in TT_KONULARI if _has(r.konular, KATEGORILER[k])]
        if uyan:
            atama.setdefault(next(k for k in _TT_ONCELIK if k in uyan), []).append(r.Index)
    return {k: df.loc[atama[k]] for k in TT_KONULARI if k in atama}


def kurulus_gruplari(df: pd.DataFrame) -> dict:
    """Kuruluş yayınlarını başlıklara ayırır (Uluslararası ticaret ve Emek piyasası dahil). Konusuz yayın gösterilmez."""
    from .config import KURULUS_KATEGORILERI, KURULUS_ONCELIK
    atama = {}
    for r in df.itertuples():
        uyan = [k for k, t in KURULUS_KATEGORILERI.items() if _has(r.konular, t)]
        if uyan:
            atama.setdefault(next(k for k in KURULUS_ONCELIK if k in uyan), []).append(r.Index)
    return {k: df.loc[atama[k]] for k in KURULUS_KATEGORILERI if k in atama}


# ----------------------------------------------------------------------------- Word notu
def docx_uret(oz: dict, guncelleme: str, baslik_ek: str = "") -> bytes:
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    BORDO, GRI, METIN = RGBColor(0x7E, 0x05, 0x2E), RGBColor(0x57, 0x57, 0x56), RGBColor(0x1D, 0x1D, 0x1B)
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size, st.font.color.rgb = "Times New Roman", Pt(11), METIN

    def font(run, name, size=None, bold=None, color=None):
        run.font.name = name
        run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
        if size:
            run.font.size = Pt(size)
        if bold is not None:
            run.font.bold = bold
        if color is not None:
            run.font.color.rgb = color

    def baslik(text, size=14):
        p = doc.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(12), Pt(4)
        font(p.add_run(text), "Montserrat", size, True, BORDO)

    def madde(text):
        p = doc.add_paragraph(style="List Bullet")
        font(p.add_run(text), "Times New Roman", 11)

    def haber_maddesi(metin, url, kaynak):
        """Madde: başlık Word hiperlinki, ardından (kaynak)."""
        p = doc.add_paragraph(style="List Bullet")
        r_id = doc.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                                  is_external=True)
        h = OxmlElement("w:hyperlink")
        h.set(qn("r:id"), r_id)
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        for tag_, val in (("w:color", "0B3C5D"), ("w:u", "single")):
            e = OxmlElement(tag_)
            e.set(qn("w:val"), val)
            rPr.append(e)
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), "Times New Roman"), rf.set(qn("w:hAnsi"), "Times New Roman")
        rPr.append(rf)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.text = metin
        r.append(t)
        h.append(r)
        p._p.append(h)
        font(p.add_run(f" ({kaynak})"), "Times New Roman", 11, False, GRI)

    def tablo(basliklar, satirlar, genislik):
        t = doc.add_table(rows=1, cols=len(basliklar))
        b = OxmlElement("w:tblBorders")
        for yon_ in ("top", "bottom", "insideH"):
            e = OxmlElement(f"w:{yon_}")
            e.set(qn("w:val"), "single"), e.set(qn("w:sz"), "4"), e.set(qn("w:color"), "C5CED6")
            b.append(e)
        for yon_ in ("left", "right", "insideV"):
            e = OxmlElement(f"w:{yon_}")
            e.set(qn("w:val"), "nil")
            b.append(e)
        t._element.tblPr.append(b)
        for i, h in enumerate(basliklar):
            c = t.rows[0].cells[i]
            sh = OxmlElement("w:shd")
            sh.set(qn("w:val"), "clear"), sh.set(qn("w:color"), "auto"), sh.set(qn("w:fill"), "0B3C5D")
            c._element.get_or_add_tcPr().append(sh)
            c.text = ""
            font(c.paragraphs[0].add_run(h), "Montserrat", 9, True, RGBColor(255, 255, 255))
        for s in satirlar:
            cells = t.add_row().cells
            for i, v in enumerate(s):
                cells[i].text = ""
                font(cells[i].paragraphs[0].add_run(str(v)), "Times New Roman", 10)
        for row in t.rows:
            for i, w in enumerate(genislik):
                row.cells[i].width = Cm(w)
        doc.add_paragraph()

    bugun = oz["bugun"]
    p = doc.add_paragraph()
    font(p.add_run("Haftalık Gündem Notu" + (f" · {baslik_ek}" if baslik_ek else "")), "Montserrat", 20, True, BORDO)
    p = doc.add_paragraph()
    font(p.add_run(f"{bugun:%d.%m.%Y} · Veriler en son {guncelleme} tarihinde güncellendi"),
         "Times New Roman", 10, False, GRI)

    baslik("Yayın fırsatları")
    if oz["firsatlar"]:
        tablo(["Konu", "Düzey", "Gerekçe"],
              [(f["kategori"], f["seviye"], "; ".join(f["nedenler"])) for f in oz["firsatlar"]], [3.4, 1.8, 11.4])
    else:
        madde("Bu hafta öne çıkan bir fırsat tespit edilmedi.")
    p = doc.add_paragraph()
    font(p.add_run("Düzey; haber yoğunluğu, yaklaşan özel gün, TÜİK yayını ve Meclis gündemine göre hesaplanan sezgisel "
                   "bir göstergedir. Karar için gerekçeleri okuyun."), "Times New Roman", 9, False, GRI)

    for f in oz["firsatlar"]:
        k = f["detay"]
        p = doc.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(8), Pt(0)
        font(p.add_run(f["kategori"]), "Montserrat", 11, True, BORDO)
        for b in k["basliklar"]:
            haber_maddesi(b["baslik"], b["link"], b["kaynak"])
        if k["genel_kurul"] or k["komisyon"]:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            font(p.add_run("Meclis"), "Times New Roman", 11, True)
            for m in k["genel_kurul"]:
                madde(f"Genel Kurul: {m[:200]}")
            for m in k["komisyon"]:
                madde(f"{m['tarih']:%d.%m.%Y} · {m['baslik']}")
        if k["meclis_haberleri"]:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            font(p.add_run("Meclisten yansıyan haberler"), "Times New Roman", 11, True)
            for m in k["meclis_haberleri"]:
                haber_maddesi(m["baslik"], m["link"], m["kaynak"])

    baslik("Önümüzdeki 14 gün")
    if oz["takvim"]:
        tablo(["Tarih", "Tür", "Konu", "Olay"],
              [(f"{t['tarih']:%d.%m.%Y}", t["tur"], t["konu"], t["olay"]) for t in oz["takvim"]],
              [2.4, 3.2, 2.6, 8.4])
    else:
        madde("Kayıtlı olay yok.")

    p = doc.add_paragraph()
    font(p.add_run("Kaynak: AA, BBC, DW, Hürriyet, Google Haberler; TBMM; TÜİK yayın takvimi."),
         "Times New Roman", 9, False, GRI)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
