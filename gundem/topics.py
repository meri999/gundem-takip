import re
from functools import lru_cache

from .config import KATEGORILER, TOPICS


def tr_lower(s: str) -> str:
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


@lru_cache(maxsize=1)
def _compiled():
    """konu -> (içerme deseni, dışlama deseni)"""
    out = {}
    for topic, kws in TOPICS.items():
        inc, exc = [], []
        for k in kws:
            if k.startswith("!"):
                exc.append(r"(?<!\w)" + re.escape(k[1:]))
            elif k.startswith("="):
                inc.append(r"(?<!\w)" + re.escape(k[1:]) + r"(?!\w)")
            else:
                inc.append(r"(?<!\w)" + re.escape(k))
        out[topic] = (re.compile("|".join(inc)), re.compile("|".join(exc)) if exc else None)
    return out


def tag(text: str) -> list[str]:
    t = tr_lower(text)
    t2 = t.replace("ı", "i")  # İngilizce metinde noktasız ı sorunu
    res = []
    for topic, (inc, exc) in _compiled().items():
        if (inc.search(t) or inc.search(t2)) and not (exc and (exc.search(t) or exc.search(t2))):
            res.append(topic)
    return res


# Haberin Meclis tartışmasına atıf yapıp yapmadığı (başlıkta)
_MECLIS = re.compile(r"(?<!\w)(tbmm|meclis|milletvekil|kanun teklif|genel kurul|grup önerisi|önerge|torba yasa|"
                     r"kanun tasar|yasa teklif|komisyonda kabul|meclis'e|meclis’e)")


# TBMM dışı "meclis"ler ve soyadı eşleşmeleri
_HARIC = re.compile(r"(çocuk meclis|kadın meclis|gençlik meclis|öğrenci meclis|kent konsey|belediye meclis|"
                    r"il genel meclis|meclis üye|gazi meclis|meclis başkanı seçil|milletvekili genç(?!lik))")


def meclis_haberi(text: str) -> bool:
    t = tr_lower(text)
    return bool(_MECLIS.search(t)) and not _HARIC.search(t)


def kategoriler_of(topics: str, en_fazla: int = 2) -> list[str]:
    """Haberin ince konu etiketlerinden kullanıcıya gösterilecek kategori adları (en çok `en_fazla`)."""
    ks = set((topics or "").split(","))
    return [k for k, v in KATEGORILER.items() if ks & set(v)][:en_fazla]


def tr_cumle(s: str) -> str:
    """'PLAN VE BÜTÇE KOMİSYONU' -> 'Plan ve bütçe komisyonu' (Türkçe i/ı kurallarıyla)."""
    s = tr_lower(s).strip()
    return ({"i": "İ", "ı": "I"}.get(s[:1], s[:1].upper()) + s[1:]) if s else s
