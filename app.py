import html
import json
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from gundem import ozet as ozet_mod
from gundem import takvim, theme
from gundem.config import KATEGORILER
from gundem.forecast import load_events, load_items, load_thinktank
from gundem.topics import kategoriler_of, meclis_haberi

st.set_page_config(page_title="Gündem Takip", page_icon="📰", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)
st.title("Gündem Takip")
st.markdown(f'<div class="guncel">Son güncelleme: {ozet_mod.son_guncelleme()} · veriler her sabah yenilenir · Geliştirici: Meryem Türel, 2026</div>',
            unsafe_allow_html=True)


@st.cache_data(ttl=900)
def get_items():
    return load_items(120)


@st.cache_data(ttl=900)
def get_events():
    return load_events()


@st.cache_data(ttl=900)
def get_thinktank():
    return load_thinktank(14)


@st.cache_data(ttl=900)
def get_kurulus():
    from gundem.kurulus import ANA_RAPOR
    return load_thinktank(30, tablo="kurulus", koru=ANA_RAPOR)


items = get_items()
if items.empty:
    st.warning("Veri bulunamadı. Lütfen yöneticiye bildirin.")
    st.stop()
events = get_events()
TODAY = date.today()
haber = items[~items["source"].str.startswith("arXiv")]  # arXiv makaleleri listelerde yer almaz
HAFTALIK = "Haftalık gündem"


def has_topic(s, wanted):
    return any(t in (s or "").split(",") for t in wanted)


# ------------------------------------------------------------------ Üst butonlar: her şey bunların altında
secim = st.pills("Konu", [HAFTALIK, "Gelecek gündem", "Takvim"] + list(KATEGORILER)
                 + ["Think-tank yayınları", "Kuruluş yayınları", "Köşe yazısı"], default=HAFTALIK, selection_mode="single",
                 key="kat") or HAFTALIK
AKTIF = [] if secim in (HAFTALIK, "Gelecek gündem", "Think-tank yayınları", "Kuruluş yayınları", "Köşe yazısı", "Takvim") else KATEGORILER[secim]


def sec(df):
    return df[df["topics"].apply(lambda s: has_topic(s, AKTIF))] if AKTIF else df


haber_f = sec(haber)
ev_f = sec(events) if not events.empty else events


def yardim(metin: str):
    st.markdown(f'<div class="yardim">{metin}</div>', unsafe_allow_html=True)


def chips(topics: str) -> str:
    return "".join(f'<span class="konu">{html.escape(k)}</span>' for k in kategoriler_of(topics))


def liste(df, n=30, etiket=True):
    """Haber listesi: bağlantı, kaynak, isteğe bağlı konu etiketi (en çok 2)."""
    if df.empty:
        st.caption("Kayıt yok.")
        return
    out = []
    for r in df.head(n).itertuples():
        out.append(f'<div style="padding:.35rem 0;border-bottom:1px solid {theme.ACIK_GRI}">'
                   f'<a href="{html.escape(r.link)}" target="_blank">{html.escape(r.title)}</a> '
                   f'<span class="hkaynak">· {html.escape(r.source)}</span>'
                   + (f"<br>{chips(r.topics)}" if etiket else "") + "</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def tablo(df):
    st.dataframe(df, hide_index=True, width="stretch")


def meclis_haberleri(df, gun=14, n=15):
    """Başlığında Meclis atfı olan haberler."""
    m = df[(df["day"] >= TODAY - timedelta(days=gun))]
    return m[m["title"].apply(meclis_haberi) & (m["topics"] != "")].sort_values("published", ascending=False).head(n)


def gecmis_bolumu(anahtar: str):
    """Kalıcı "Geçmiş haberler" bölümü: seçilen gün ya da haftanın, seçili konuyla ilgili haberleri."""
    st.subheader("Geçmiş haberler")
    gmin, gmax = haber["day"].min(), haber["day"].max()
    c1, c2 = st.columns([1, 2])
    day = c1.date_input("Gün", value=gmax, min_value=gmin, max_value=gmax, key=f"gun_{anahtar}")
    span = c2.radio("Aralık", ["Tek gün", "O güne kadar son 7 gün"], horizontal=True, key=f"aralik_{anahtar}")
    lo = day if span == "Tek gün" else day - timedelta(days=6)
    d = haber_f[(haber_f["day"] >= lo) & (haber_f["day"] <= day)]
    st.caption(f"{lo:%d.%m.%Y} – {day:%d.%m.%Y} · {len(d)} haber"
               + (", en yeni 30'u gösteriliyor" if len(d) > 30 else ""))
    liste(d.sort_values("published", ascending=False), 30)


def thinktank_goster(df, n: int = 40, ozet: bool = True, etiket: bool = True):
    """Think-tank yayın listesi: kurum, başlık (bağlantı), tarih, isteğe bağlı kısa özet ve konu etiketi."""
    if df.empty:
        st.caption("Kayıt yok.")
        return
    out = []
    for r in df.head(n).itertuples():
        ozet_ = html.escape((r.ozet or "")[:200]) + ("…" if r.ozet and len(r.ozet) > 200 else "")
        et = "".join(f'<span class="konu">{html.escape(k)}</span>' for k in kategoriler_of(r.konular)) if etiket else ""
        out.append(f'<div style="padding:.4rem 0;border-bottom:1px solid {theme.ACIK_GRI}">'
                   f'<span class="konu" style="background:{theme.BORDO};color:#fff">{html.escape(r.kurum)}</span> '
                   f'<a href="{html.escape(r.link)}" target="_blank">{html.escape(r.baslik)}</a> '
                   f'<span class="hkaynak">· {r.day:%d.%m.%Y}</span>'
                   + (f'<div class="hkaynak" style="font-size:.88rem">{ozet_}</div>' if ozet and ozet_ else "")
                   + (f"<div>{et}</div>" if et else "") + "</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def thinktank_konulara_gore(df, her_konuda: int = 3, ozet: bool = True, kolon: int = 2, kurulus: bool = False):
    """Yayınları konu başlıkları altında listeler (Haftalık gündemdeki konu bloklarıyla aynı düzen)."""
    gruplar = ozet_mod.kurulus_gruplari(df) if kurulus else ozet_mod.thinktank_gruplari(df)
    if not gruplar:
        st.caption("Kayıt yok.")
        return
    kol = st.columns(kolon)
    for i, (k, d) in enumerate(gruplar.items()):
        with kol[i % kolon]:
            st.markdown(f"#### {k}")
            thinktank_goster(d, her_konuda, ozet=ozet, etiket=False)


def oneri_sayfasi(dosya: str, baslik: str, olcut: str, kose: bool):
    """Köşe yazısı konu önerilerini kart olarak gösterir (data/ altındaki JSON dosyasından)."""
    yol = Path(__file__).parent / "data" / dosya
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        hazir = date.fromisoformat(veri["hazirlanma"])
    except Exception:
        st.info("Öneriler şu an yok.")
        return
    st.subheader(baslik)
    ek = ""
    st.caption(f"Hazırlanma tarihi: {hazir:%d.%m.%Y}{ek} · {olcut}")
    if (TODAY - hazir).days > 10:
        st.caption(f"Bu öneriler {(TODAY - hazir).days} gün önce hazırlandı; güncel gündem için yenilenmesi gerekir.")

    def satir(m):
        return f'<div class="hb">{m}</div>'

    for o in veri["oneriler"]:
        k = f'<div class="firsat"><div class="fb">{html.escape(o["baslik"])}</div>'
        k += f'<span class="konu">{html.escape(o["kategori"])}</span>'
        k += f'<div class="tez">{html.escape(o["tez"])}</div>'
        if kose and o.get("kanca"):
            k += f'<div class="ozet">Neden şimdi: {html.escape(o["kanca"])}</div>'
        if kose and o.get("acilis"):
            k += f'<div class="ozet">Açılış önerisi: {html.escape(o["acilis"])}</div>'
        if o.get("zaman"):
            k += f'<div class="ozet">Yayın zamanı: {html.escape(o["zaman"])}</div>'
        gundem = []
        for g in o.get("gundem", []):
            if g["tur"] in ("haber", "yayin"):  # "yayin": kuruluş yayını (kaynak = kuruluş adı)
                gundem.append(satir(f'<a href="{html.escape(g["link"])}" target="_blank">{html.escape(g["metin"])}</a> '
                                    f'<span class="hkaynak">· {html.escape(g["kaynak"])}, '
                                    f'{date.fromisoformat(g["tarih"]):%d.%m.%Y}</span>'))
            else:
                gundem.append(satir(f'{date.fromisoformat(g["tarih"]):%d.%m.%Y} · {html.escape(g["metin"])}'))
        if gundem:
            k += '<div class="alt">GÜNDEM BAĞI</div>' + "".join(gundem)
        if o.get("dunya"):
            k += '<div class="alt">DÜNYADAN ÖRNEK</div>' + satir(html.escape(o["dunya"]))
        if o.get("turkiye"):
            k += '<div class="alt">TÜRKİYE’YE YANSIMA</div>' + satir(html.escape(o["turkiye"]))
        etiket = "KULLANILABİLECEK RAKAM" if kose else "GEREKEN VERİ"
        veri_satirlari = o.get("rakam") if kose else o.get("veri")
        if veri_satirlari:
            k += f'<div class="alt">{etiket}</div>' + "".join(satir(html.escape(v)) for v in veri_satirlari)
        if kose and o.get("dikkat"):
            k += '<div class="alt">DİKKAT</div>' + satir(html.escape(o["dikkat"]))
        if o.get("atif") or o.get("atif_gerekli"):
            k += '<div class="alt">ATIF VE BAĞLANTI</div>'
            for a in o.get("atif", []):
                ek = ", ".join(str(x) for x in (a.get("kurum"), a.get("tur"), a.get("yil")) if x)
                k += satir(f'<a href="{html.escape(a["link"])}" target="_blank">{html.escape(a["baslik"])}</a> '
                           f'<span class="hkaynak">· {html.escape(ek)}</span>'
                           + (f' <span class="hkaynak">({html.escape(a["not"])})</span>' if a.get("not") else ""))
            for a in o.get("atif_gerekli", []):
                k += satir(f'<span class="hkaynak">Atıf gerekli: {html.escape(a)}</span>')
        st.markdown(k + "</div>", unsafe_allow_html=True)


# ====================================================================== GELECEK GÜNDEM
if secim == "Gelecek gündem":
    st.subheader("Bilinen yaklaşan gelişmeler")
    yak = ozet_mod.yaklasan_gelismeler(events, TODAY, 30)
    if yak:
        tablo(pd.DataFrame([{"Tarih": g["tarih"], "Tür": g["tur"], "Konu": g["konu"], "Gelişme": g["olay"]}
                            for g in yak]))
    else:
        st.caption("Önümüzdeki 30 günde kayıtlı gelişme yok.")

    st.subheader("Önümüzdeki 1 ayın tahmini gündemi")
    tg = ozet_mod.tahmini_gundem(haber, events, TODAY, 30, 10)
    if tg:
        tablo(pd.DataFrame([{"Gündem": x["gundem"], "Zaman": x["zaman"], "Düzey": x["seviye"], "Konu": x["konu"],
                             "Dayanak": x["dayanak"]} for x in tg]))
    else:
        st.caption("Tahmini gündem üretilemedi.")
    st.caption("Tahmin, takvimdeki bilinen gelişmeleri (gelecek) ve son haftada haberlerde yükselen konuları (geçmiş) "
               "birlikte değerlendirir. Kesin öngörü değil, yön göstergesidir.")
    st.stop()

# ====================================================================== THINK-TANK
if secim == "Think-tank yayınları":
    st.subheader("Dünyadan think-tank yayınları")
    tt = get_thinktank()
    if tt.empty:
        st.info("Think-tank verisi şu an yok.")
        st.stop()
    st.caption(f"Son 14 gün · {tt['kurum'].nunique()} kurum · toplum, aile, demografi, istihdam ve emek odaklı · "
               "başlıklar özgün dilde (İngilizce)")
    kurum_tt = st.selectbox("Kurum", ["Tüm kurumlar"] + sorted(tt["kurum"].unique()), key="tt_kurum")
    if kurum_tt != "Tüm kurumlar":
        tt = tt[tt["kurum"] == kurum_tt]
    thinktank_konulara_gore(tt, her_konuda=5, ozet=True)
    st.stop()

# ====================================================================== KURULUŞ YAYINLARI
if secim == "Kuruluş yayınları":
    st.subheader("Uluslararası kuruluş yayınları")
    kr = get_kurulus()
    if kr.empty:
        st.info("Kuruluş verisi şu an yok.")
        st.stop()
    st.caption(f"Son 30 gün (ana raporlar 90 gün) · {kr['kurum'].nunique()} kuruluş · başlıklar özgün dilde (İngilizce)")
    kurum_kr = st.selectbox("Kuruluş", ["Tüm kuruluşlar"] + sorted(kr["kurum"].unique()), key="kr_kurum")
    if kurum_kr != "Tüm kuruluşlar":
        kr = kr[kr["kurum"] == kurum_kr]
    thinktank_konulara_gore(kr, her_konuda=8, ozet=True, kurulus=True)
    st.stop()

# ====================================================================== KÖŞE YAZISI
if secim == "Köşe yazısı":
    oneri_sayfasi("kose_yazisi_onerileri.json", "Gazete köşe yazısı önerileri",
                  "Hedef 600-800 kelime, tek güncel kanca, jargonsuz dil, somut bir çağrı", kose=True)
    st.stop()

# ====================================================================== TAKVİM
if secim == "Takvim":
    konu_t = st.selectbox("Konuya göre süz", ["Tüm olaylar"] + list(KATEGORILER))
    KT = [] if konu_t == "Tüm olaylar" else KATEGORILER[konu_t]
    bas, bit = takvim.aralik(TODAY)
    ol = takvim.olaylari_topla(events, bas, bit, konular=KT or None)
    for y, m in takvim.uc_ay(TODAY):
        st.markdown(takvim.ay_html(y, m, ol, TODAY), unsafe_allow_html=True)

    with st.expander("TÜİK yayın listesi"):
        if events.empty:
            st.caption("Takvim verisi şu an yok.")
        else:
            gun = st.slider("Kaç gün ilerisi?", 7, 90, 30)
            tk = events[(events["kind"] == "tuik") & (events["source"] == "TÜİK") & (events["date"] >= TODAY)
                        & (events["date"] <= TODAY + timedelta(days=gun))]
            if KT:
                tk = tk[tk["topics"].apply(lambda s: has_topic(s, KT))]
            elif not st.checkbox("Konuyla ilgisiz TÜİK yayınlarını da göster"):
                tk = tk[tk["topics"] != ""]
                st.caption("Yalnızca aile, nüfus, istihdam gibi konularla ilgili yayınlar gösteriliyor.")
            tk = tk.sort_values("date").copy()
            tk["Konu"] = tk["topics"].apply(lambda s: ", ".join(kategoriler_of(s)))
            tablo(tk[["date", "title", "detail", "Konu"]].rename(
                columns={"date": "Tarih", "title": "Yayın", "detail": "Dönem"}))
    with st.expander("Zirve ve karar tarihlerinin kaynakları"):
        for b, s, ad, kapsam, kaynak in takvim.PLANLI:
            aralik = b if b == s else f"{b} – {s}"
            st.markdown(f"- **{aralik}** · {ad} · _{kaynak}_")
    st.stop()

# ====================================================================== HAFTALIK GÜNDEM
if secim == HAFTALIK:
    oz = ozet_mod.hafta_ozeti(haber, events, TODAY, KATEGORILER, sabit=("Demografi",),
                              haric=("Dünya ve güvenlik",))
    st.download_button("Word notu olarak indir", data=ozet_mod.docx_uret(oz, ozet_mod.son_guncelleme(), ""),
                       file_name=f"gundem_notu_{TODAY:%Y%m%d}.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.subheader("Haftalık gündem")
    if not oz["firsatlar"]:
        st.caption("Bu hafta öne çıkan bir konu tespit edilmedi. Konu butonlarından tek tek bakabilirsiniz.")

    def haber_satiri(b):
        return (f'<div class="hb"><a href="{html.escape(b["link"])}" target="_blank">{html.escape(b["baslik"])}</a> '
                f'<span class="hkaynak">· {html.escape(b["kaynak"])}</span></div>')

    for f in oz["firsatlar"]:
        k = f["detay"]
        nedenler = "".join(f"<li>{html.escape(n)}</li>" for n in f["nedenler"])
        kart = (f'<div class="firsat"><span class="puan">{f["seviye"]}</span>'
                f'<div class="fb">{html.escape(f["kategori"])}</div>'
                f'<ul>{nedenler}</ul>')
        if k["basliklar"]:
            kart += '<div class="alt">ÖNE ÇIKAN HABERLER</div>' + "".join(haber_satiri(b) for b in k["basliklar"])
        if k["genel_kurul"] or k["komisyon"]:
            kart += '<div class="alt">MECLİS</div>' + "".join(
                f'<div class="hb">Genel Kurul: {html.escape(m[:200])}</div>' for m in k["genel_kurul"]) + "".join(
                f'<div class="hb">{m["tarih"]:%d.%m.%Y} · {html.escape(m["baslik"])}</div>' for m in k["komisyon"])
        if k["meclis_haberleri"]:
            kart += '<div class="alt">MECLİSTEN YANSIYAN HABERLER</div>' + "".join(
                haber_satiri(b) for b in k["meclis_haberleri"])
        st.markdown(kart + "</div>", unsafe_allow_html=True)
    if oz["firsatlar"]:
        st.caption("Düzey; haber yoğunluğu, yaklaşan özel gün, TÜİK yayını ve Meclis gündemine göre hesaplanır. "
                   "Karar için gerekçeleri okuyun. Diğer konular için üstteki butonları kullanın.")

    st.subheader("Önümüzdeki 14 gün")
    if oz["takvim"]:
        tablo(pd.DataFrame([{"Tarih": t["tarih"], "Tür": t["tur"], "Konu": t["konu"], "Olay": t["olay"]}
                            for t in oz["takvim"]]))
    else:
        st.caption("Kayıtlı olay yok.")
    gecmis_bolumu("hafta")

    st.subheader("Dünyadan think-tank yayınları")
    tt = get_thinktank()
    if tt.empty:
        st.caption("Think-tank verisi şu an yok.")
    else:
        st.caption("Son 14 gün · toplum, aile, demografi, istihdam ve emek odaklı kurumlar · başlıklar özgün dilde")
        thinktank_konulara_gore(tt, her_konuda=2, ozet=False)
    st.stop()

# ====================================================================== KONU SAYFASI
st.subheader(secim)

st.subheader("Son haberler")
liste(haber_f[haber_f["day"] >= TODAY - timedelta(days=4)].sort_values("published", ascending=False), 10,
      etiket=False)

st.subheader("Meclisten yansıyan haberler")
liste(meclis_haberleri(haber_f, 14, 15), 15, etiket=False)

st.subheader("Yaklaşanlar")
ol = takvim.olaylari_topla(events, TODAY, TODAY + timedelta(days=60), konular=AKTIF)
yak = [(d, e, t) for d in sorted(ol) for c, e, t, k in ol[d] if c != "MECLIS"]
for d, e, t in yak[:15]:
    st.markdown(f"- {d:%d.%m.%Y} · **{ozet_mod.tur_adi(e)}** {t}")
if not yak:
    st.caption("Bu konuyla ilgili yaklaşan TÜİK yayını ya da özel gün yok.")

gecmis_bolumu("konu")
