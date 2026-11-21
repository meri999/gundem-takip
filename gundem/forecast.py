"""Konu bazlı trend analizi ve kısa vadeli tahmin."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .db import connect


def load_items(days: int = 90) -> pd.DataFrame:
    with connect() as con:
        df = pd.read_sql_query("SELECT * FROM items", con)
    if df.empty:
        return df
    df["published"] = pd.to_datetime(df["published"], utc=True, errors="coerce")
    df["day"] = df["published"].dt.tz_convert("Europe/Istanbul").dt.date
    cutoff = date.today() - timedelta(days=days)
    return df[df["day"] >= cutoff]


def load_thinktank(days: int = 14, tablo: str = "thinktank", koru: str = "", koru_gun: int = 90) -> pd.DataFrame:
    """Son `days` günün think-tank (ya da tablo="kurulus" ile kuruluş) yayınları (en yeniden eskiye)."""
    assert tablo in ("thinktank", "kurulus")
    with connect() as con:
        df = pd.read_sql_query(f"SELECT * FROM {tablo}", con)
    if df.empty:
        return df
    df["tarih"] = pd.to_datetime(df["tarih"], utc=True, errors="coerce")
    df["day"] = df["tarih"].dt.date
    yeni = df["day"] >= date.today() - timedelta(days=days)
    if koru:  # ana raporlar daha uzun süre gösterilir
        yeni |= df["baslik"].str.contains(koru, case=False, regex=True) & (df["day"] >= date.today() - timedelta(days=koru_gun))
    df = df[yeni]
    # güvenlik, dış politika, iklim ve siyaset konulu yayınlar dışarıda kalır
    from .config import THINKTANK_DISLANAN
    df = df[~df["konular"].apply(lambda s_: any(k in (s_ or "").split(",") for k in THINKTANK_DISLANAN))]
    import re as _re
    from .config import THINKTANK_BASLIK_DISLA
    rx = _re.compile(THINKTANK_BASLIK_DISLA, _re.I)
    df = df[~df["baslik"].apply(lambda b: bool(rx.search(b or "")))]
    return df.sort_values("tarih", ascending=False)


def load_events() -> pd.DataFrame:
    """TBMM ve TÜİK takvim kayıtları."""
    with connect() as con:
        df = pd.read_sql_query("SELECT * FROM events", con)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def olcum(df: pd.DataFrame) -> pd.DataFrame:
    """Trend ve tahmin için tek tutarlı kaynak: Google Haberler sorguları. RSS kaynakları geçmiş günlerde yok,
    karıştırılırsa son günler yapay olarak artmış görünür. Google verisi yoksa tümünü döndürür."""
    m = df[df["link"].str.contains("news.google.com", regex=False)]
    return m if len(m) else df


def kapsama(df: pd.DataFrame) -> pd.Series:
    """Günlük kapsama düzeltme katsayısı. Google Haberler yakın günler için daha çok sonuç verdiği için ham sayılar
    zamanla yapay olarak artar. Her günün toplam haber sayısı, medyan güne eşitlenerek konu sayıları kıyaslanabilir olur."""
    tot = olcum(df[~df["source"].str.startswith("arXiv")]).groupby("day").size()
    if tot.empty:
        return pd.Series(dtype=float)
    return (tot.median() / tot).clip(upper=3.0)


def agirlik(df: pd.DataFrame, kat: pd.Series) -> pd.Series:
    """Her haberin bulunduğu günün katsayısı (katsayı yoksa 1)."""
    return df["day"].map(kat).fillna(1.0)


def topic_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Gün x konu haber sayısı: tutarlı kaynaktan (Google Haberler) ve kapsama düzeltmeli."""
    kat = kapsama(df)
    df = olcum(df[~df["source"].str.startswith("arXiv")])  # akademik makaleler günlük seriyi şişirir
    if df.empty:
        return pd.DataFrame()
    rows = [(r.day, t) for r in df.itertuples() for t in (r.topics or "").split(",") if t]
    if not rows:
        return pd.DataFrame()
    s = pd.DataFrame(rows, columns=["day", "topic"]).groupby(["day", "topic"]).size().unstack(fill_value=0)
    s.index = pd.to_datetime(s.index)
    s = s.asfreq("D", fill_value=0)
    faktor = [float(kat.get(d.date(), 1.0)) for d in s.index]
    return s.mul(faktor, axis=0).round(1)


def forecast(daily: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
    """Her konu için sonraki `horizon` gün beklenen toplam ve değişim.

    >=21 gün veri varsa üstel düzleştirme (Holt), yoksa son 7 günün ortalaması.
    Az veriyle sonuçlar yalnızca yön göstergesidir."""
    out = []
    for topic in daily.columns:
        y = daily[topic].astype(float)
        last7 = y.tail(7).sum()
        method = "Son 7 gün ortalaması"
        pred = y.tail(7).mean() * horizon
        if len(y) >= 21:
            try:
                from statsmodels.tsa.holtwinters import ExponentialSmoothing
                m = ExponentialSmoothing(y, trend="add", damped_trend=True).fit()
                pred = float(np.clip(m.forecast(horizon), 0, None).sum())
                method = "Holt (sönümlü trend)"
            except Exception:
                pass
        prev7 = y.iloc[-14:-7].sum() if len(y) >= 14 else np.nan
        mom = (last7 - prev7) / prev7 * 100 if prev7 and prev7 > 0 else np.nan
        out.append({"Konu": topic, "Son 7 gün": last7, "Önceki 7 gün": prev7,
                    "Haftalık değişim %": mom, f"Tahmin ({horizon} gün)": round(pred, 1),
                    "Yöntem": method, "Gün sayısı": len(y)})
    return pd.DataFrame(out).sort_values("Haftalık değişim %", ascending=False, na_position="last")


def tahmin(y: pd.Series, horizon: int = 7) -> pd.Series:
    """Önümüzdeki `horizon` gün için günlük haber sayısı tahmini (indeks: tarih).
    21 günden uzun seri varsa sönümlü trendli üstel düzleştirme (Holt), yoksa son 7 günün ortalaması."""
    y = y.astype(float)
    son_gun = pd.to_datetime(y.index).max()
    gelecek = pd.date_range(son_gun + pd.Timedelta(days=1), periods=horizon).date
    pred = pd.Series([float(y.tail(7).mean())] * horizon, index=gelecek)
    if len(y) >= 21:
        try:
            import warnings
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                y2 = y.copy()
                y2.index = pd.DatetimeIndex(pd.to_datetime(y2.index), freq="D")
                m = ExponentialSmoothing(y2, trend="add", damped_trend=True).fit()
                pred = pd.Series(np.clip(m.forecast(horizon).values, 0, None), index=gelecek)
        except Exception:
            pass
    return pred


def yon(y: pd.Series, horizon: int = 7) -> str:
    """Önümüzdeki `horizon` gün için beklenen yön: Yükseliyor / Yatay / Düşüyor."""
    son = float(y.astype(float).tail(7).sum())
    if son <= 0:
        return "Yatay"
    oran = float(tahmin(y, horizon).sum()) / son
    return "Yükseliyor" if oran > 1.15 else "Düşüyor" if oran < 0.85 else "Yatay"
