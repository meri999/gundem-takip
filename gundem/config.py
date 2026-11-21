"""Kaynaklar ve konu sözlüğü. Yeni kaynak/konu eklemek için burayı düzenleyin."""
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gundem.db"

# (ad, kategori, rss adresi)
RSS_SOURCES = [
    ("AA Güncel", "turkiye", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
    ("AA Ekonomi", "ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
    ("BBC Türkçe", "turkiye", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ("DW Türkçe", "dunya", "https://rss.dw.com/rdf/rss-tur-all"),
    ("Hürriyet Gündem", "turkiye", "https://www.hurriyet.com.tr/rss/gundem"),
    ("BBC World", "dunya", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    # Ekonomi ve iş dünyası kaynakları
    ("CNBC-e", "ekonomi", "https://www.cnbce.com/rss"),
    ("BloombergHT", "ekonomi", "https://www.bloomberght.com/rss"),
    ("Marketing Türkiye", "ekonomi", "https://www.marketingturkiye.com.tr/feed/"),
    # NTV: toplumsal araştırmalar için gündem, sağlık, eğitim ve ekonomi bölümleri
    ("NTV Gündem", "turkiye", "https://www.ntv.com.tr/gundem.rss"),
    ("NTV Ekonomi", "ekonomi", "https://www.ntv.com.tr/ekonomi.rss"),
    ("NTV Sağlık", "turkiye", "https://www.ntv.com.tr/saglik.rss"),
    ("NTV Eğitim", "turkiye", "https://www.ntv.com.tr/egitim.rss"),
    ("arXiv cs.AI", "yz", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CY", "yz", "https://export.arxiv.org/rss/cs.CY"),
]

# Sosyal gündem vekilleri (X API ücretli olduğu için)
GOOGLE_TRENDS = [("Google Trends TR", "TR"), ("Google Trends ABD", "US")]
WIKI_PROJECTS = [("Vikipedi TR", "tr.wikipedia"), ("Wikipedia EN", "en.wikipedia")]

# Konu -> anahtar kelimeler (küçük harf). Eşleşme kuralı:
#   "kelime"  -> kelimenin başında eşleşir (ekler serbest: "yaşlı" -> "yaşlıların")
#   "=kelime" -> yalnızca tam kelime ("=zam" "zaman"ı yakalamaz)
#   "!kelime" -> bu ifade varsa konu SAYILMAZ (gürültü kesici: "!festival", "!süper lig")
SPOR = ["!süper lig", "!transfer", "!şampiyonlar", "!maçı", "!teknik direktör", "!futbol", "!basketbol",
        "!voleybol", "!hentbol", "!galatasaray", "!fenerbahçe", "!beşiktaş", "!trabzonspor", "!milli takım"]

TOPICS = {
    # --- Ekonomi ve refah ---
    "Ekonomi ve enflasyon": ["enflasyon", "faiz", "merkez bankası", "bütçe", "tüfe", "=zam",
                             "=zammı", "=zamlar", "ekonomi", "inflation", "interest rate", "=gdp", "büyüme",
                             "orta vadeli program", "hasıla", "fiyat endeks", "güven endeks",
                             "reel getiri", "sanayi üretim", "politika faiz", "faiz karar", "vergi", "kamu borç"],
    "Döviz ve dış denge": ["=dolar", "=euro", "döviz kuru", "kur hareket", "=altın", "borsa", "cari açık",
                           "petrol fiyat", "brent", "ham petrol", "rezerv", "dış borç", "=cds", "ödemeler dengesi",
                           "exchange rate", "current account", "=lira", "türk lirası"],
    "Yaşam maliyeti ve gelir": ["geçim", "hayat pahalılığı", "yaşam maliyeti", "gıda fiyat", "kira artış",
                               "asgari ücret", "gelir dağılımı", "cost of living", "alım gücü", "harcama"],
    "Yoksulluk ve sosyal koruma": ["yoksulluk", "sosyal yardım", "sosyal koruma", "eşitsizlik", "poverty",
                                   "social protection", "açlık sınırı", "yoksul", "muhtaç"],
    "Emeklilik ve sosyal güvenlik": ["emekli", "emeklilik", "=eyt", "sgk", "bağ-kur", "sosyal güvenlik",
                                     "pension", "retirement", "prim", "refah payı", "!emekli albay",
                                     "!emekli general", "!emekli öğretmen", "!emekli subay"],
    "Kalkınma": ["kalkınma", "development goals", "sdg", "sürdürülebilir kalkınma", "bölgesel gelişme",
                 "kalkınma planı", "unctad", "undp", "dünya bankası", "world bank"],
    "İstihdam ve çalışma hayatı": ["istihdam", "işsizlik", "işgücü", "kayıt dışı", "esnek çalış", "uzaktan çalış",
                                   "=emek", "emek piyasa", "emek gücü", "sendika", "kıdem tazminat", "ücretli çalışan", "labour",
                                   "unemployment", "employment", "işçi", "ücret", "!ücretsiz", "asgari ücret",
                                   "toplu sözleşme", "işgücüne katılım", "=neet", "platform çalış", "iş gücü",
                                   "mesai", "çalışma saat", "iş kaybı", "işten çıkar"],
    "Konut ve kent": ["konut", "kira", "kentsel dönüşüm", "kentleşme", "housing", "mahalle", "belediye"],
    # --- Aile, nüfus, yaşam döngüsü ---
    "Nüfus ve doğurganlık": ["nüfus", "doğurganlık", "doğum oran", "doğum sayı", "doğum istatistik",
                             "doğum teşvik", "doğum yardım", "doğum hızı", "toplam doğurganlık", "yaşam beklentisi",
                             "nüfus projeksiyon", "nüfus artış", "bebek ölüm", "population", "fertility",
                             "birth rate", "demograf", "aile ve nüfus", "adnks", "yeni doğan sayı",
                             "!doğum günü", "!erken doğum", "!genç nüfus", "!nüfus müdürlüğ", "!nüfus cüzdan"] + SPOR,
    "Aile ve evlilik": ["=aile", "ailesi", "aileler", "ailenin", "evlilik", "evlen", "boşanma", "aile yılı",
                        "family", "marriage", "divorce", "hane tip", "ebeveyn", "tek ebeveyn", "aile ve sosyal",
                        "doğum izni", "babalık izni", "kreş", "nafaka"] + SPOR,
    "Çocuk ve çocuk koruma": ["=çocuk", "çocuklar", "çocuğ", "koruyucu aile", "bakım altında", "çocuk hak",
                              "çocuk işçi", "unicef", "children", "child ", "bebek", "!festival", "!şenlik",
                              "!tiyatro", "!oyun", "!çocuk meclis", "!çocuk bayram", "!çoluk çocuk",
                              "!çocuk kulüb"] + SPOR,
    "Gençlik": ["gençler", "gençlik", "genç nüfus", "genç işsiz", "genç istihdam", "genç kadın", "genç girişim",
                "neet", "youth", "z kuşağı", "y kuşağı", "alfa kuşağı", "x kuşağı", "kuşaklar", "gen z", "millennial", "üniversiteli", "!gençlik ve spor bakan", "!gençlik spor",
                "!gençlik kupa", "!gençlik ligi"] + SPOR,
    "Yaşlılık ve bakım": ["yaşlı", "yaşlanma", "uzun süreli bakım", "bakım hizmet", "bakım ekonomisi",
                          "elderly", "ageing", "aging", "huzurevi", "bakımevi", "demans", "alzheimer",
                          "65 yaş", "yaşlı nüfus", "uzun ömür"] + SPOR,
    "Kadın ve toplumsal cinsiyet": ["kadına şiddet", "kadına yönelik", "kadınlara", "toplumsal cinsiyet", "kadın istihdam", "kadın emeği",
                                    "femicide", "gender", "annelik", "yarı zamanlı çalış", "kadın hak",
                                    "kadın cinayet", "=kadın", "kadınlar", "!kadın futbol", "!kadın basket",
                                    "!kadın voleyb", "!kadınlar ligi", "!kadın milli", "!wta"] + SPOR,
    "Engellilik": ["engelli", "özel gereksinim", "erişilebilir", "disability", "otizm"],
    # --- Eğitim, sağlık, değerler ---
    "Eğitim": ["eğitim", "öğrenci", "üniversite", "=okul", "okullar", "öğretmen", "meb ", "yök", "yks", "pisa",
               "school", "education"],
    "Sağlık ve ruh sağlığı": ["sağlık", "hastane", "salgın", "=aşı", "aşılama", "ruh sağlığı", "depresyon",
                              "intihar", "obezite", "=aids", "=hiv", "health", "vaccine", "pandemic", "who "],
    "Bağımlılık ve suç": ["bağımlılık", "uyuşturucu", "bahis", "kumar", "alkol", "sigara", "suç oran", "suç ",
                          "şiddet", "addiction", "narkotik"],
    "Değerler ve kültür": ["manevi değer", "toplumsal değer", "aile değer", "milli değer", "diyanet", "din ",
                           "gelenek", "kuşaklar arası", "kültürel miras", "kültürel", "!festival", "!konser"],
    # --- Teknoloji ---
    "Yapay zekâ": ["yapay zeka", "yapay zekâ", "artificial intelligence", "=llm", "chatgpt", "language model",
                   "machine learning", "makine öğren", "openai", "anthropic", "gemini", "=agent", "generative"],
    "Dijital hayat ve sosyal medya": ["sosyal medya", "dijital", "siber", "internet kullan", "ekran süre",
                                      "dijital bağımlılık", "online", "social media", "platform", "bilişim"],
    # --- Toplum ve dünya ---
    "Göç ve mülteciler": ["göç", "mülteci", "sığınmacı", "suriyeli", "düzensiz", "migration", "refugee",
                          "migrant", "unhcr", "iom "],
    "İklim ve afet": ["iklim", "deprem", "=sel", "seller", "orman yangını", "kuraklık", "afet",
                      "çevre", "climate", "earthquake", "flood", "enerji", "yenilenebilir"],
    "Meclis ve mevzuat": ["tbmm", "meclis", "kanun teklif", "milletvekili", "anayasa", "yasa teklif",
                          "torba yasa", "resmi gazete", "parliament", "komisyon"],
    "Dış politika ve güvenlik": ["savaş", "ateşkes", "=nato", "gazze", "ukrayna", "=war", "ceasefire",
                                 "sanctions", "dışişleri", "diplomasi", "avrupa birliği", "=ab"],
    # Kuruluş yayınlarında ayrı başlık olan konu; panelde buton değildir
    "Uluslararası ticaret": ["dış ticaret", "uluslararası ticaret", "ihracat", "ithalat", "gümrük", "serbest ticaret",
                             "ticaret savaş", "tedarik zincir", "=trade", "tariff", "export", "import", "supply chain",
                             "customs", "free trade", "!trade union", "!trade unions", "!ticaret bakanlığı", "!ticaret odası",
                             "!ticaret sicil"],
    "İstatistik ve araştırma": ["tüik", "istatistik", "eurostat", "oecd", "unfpa", "bülten", "census",
                                "araştırma sonuç", "anket", "survey", "endeks"],
}

# Site gezinmesindeki konu butonları: kategori -> TOPICS adları (bir konu birden çok kategoride olabilir)
KATEGORILER = {
    "Toplum ve aile": ["Aile ve evlilik", "Çocuk ve çocuk koruma", "Kadın ve toplumsal cinsiyet", "Engellilik",
                       "Yoksulluk ve sosyal koruma", "Değerler ve kültür", "Bağımlılık ve suç"],
    "Demografi": ["Nüfus ve doğurganlık", "Göç ve mülteciler", "Yaşlılık ve bakım", "Emeklilik ve sosyal güvenlik"],
    "Sağlık": ["Sağlık ve ruh sağlığı"],
    "Yapay zekâ ve teknoloji": ["Yapay zekâ", "Dijital hayat ve sosyal medya"],
    "Gençlik ve eğitim": ["Gençlik", "Eğitim"],
    "Emek piyasası": ["İstihdam ve çalışma hayatı"],
    "Dış ticaret ve döviz piyasası": ["Uluslararası ticaret", "Döviz ve dış denge"],
    "Makroekonomi": ["Ekonomi ve enflasyon", "Yaşam maliyeti ve gelir"],
    "Kalkınma": ["Kalkınma", "Konut ve kent", "Yoksulluk ve sosyal koruma"],
}

# Kuruluş yayınları sayfasının başlıkları: kategorilerle aynı
KURULUS_KATEGORILERI = dict(KATEGORILER)
# Bir yayın birden çok başlığa uyarsa en özgül olana yazılır
KURULUS_ONCELIK = ["Dış ticaret ve döviz piyasası", "Demografi", "Gençlik ve eğitim", "Sağlık",
                   "Yapay zekâ ve teknoloji", "Emek piyasası", "Makroekonomi", "Kalkınma", "Toplum ve aile"]

# Kayda değer bilgi taşımayan, her kayda yapışan konular (olay etiketlerinden çıkarılır)
GENEL_KONULAR = {"İstatistik ve araştırma", "Meclis ve mevzuat"}

# TÜİK yayın takvimi verisinden hangi kurumların yayınları alınsın
TAKVIM_KURUMLARI = {"TÜİK"}


# Think-tank başlıkları İngilizce olduğu için konu sözlüğüne İngilizce karşılıklar eklenir.
_EN_EK = {
    "İstihdam ve çalışma hayatı": ["labor market", "labour market", "worker", "wages", "=wage", "workforce", "gig economy",
                                   "paid leave", "union", "remote work", "job quality", "low-paid", "earnings",
                                   "=jobs", "=job"],
    "Aile ve evlilik": ["families", "=family", "parenting", "parents", "childcare", "child care", "household",
                        "motherhood", "fatherhood"],
    "Çocuk ve çocuk koruma": ["kids", "child poverty", "adolescent", "child welfare", "foster care"],
    "Nüfus ve doğurganlık": ["births", "birthrate", "low fertility", "declining birth", "demographic", "life expectancy",
                             "=population"],
    "Yaşlılık ve bakım": ["older adults", "older people", "long-term care", "caregiving", "elder", "longevity"],
    "Emeklilik ve sosyal güvenlik": ["pensions", "social security", "retirement"],
    "Gençlik": ["young people", "young adults", "gen z", "millennials"],
    "Eğitim": ["students", "teachers", "university", "college", "student loan", "higher education", "apprentice",
               "skills", "schools"],
    "Yoksulluk ve sosyal koruma": ["inequality", "welfare", "low income", "living standards", "benefits", "income support"],
    "Konut ve kent": ["rents", "=rent", "homeownership"],
    "Kadın ve toplumsal cinsiyet": ["=women", "gender gap", "maternal"],
    "Engellilik": ["disabled"],
    "Sağlık ve ruh sağlığı": ["mental health", "healthcare", "hospital"],
    # IMF, Dünya Bankası gibi kuruluşların makroekonomi başlıkları
    "Ekonomi ve enflasyon": ["economic outlook", "global economy", "economic growth", "economic prospects", "=gdp",
                             "=inflation", "financial stability", "fiscal monitor", "public debt", "economic activity"],
}
for _k, _v in _EN_EK.items():
    TOPICS[_k] = TOPICS[_k] + _v

# Think-tank listesinde gösterilmeyen konular (güvenlik, dış politika, iklim, siyaset)
THINKTANK_DISLANAN = {"Dış politika ve güvenlik", "İklim ve afet", "Meclis ve mevzuat"}

# Başlıkta geçerse think-tank yayını gösterilmez: güvenlik/siyaset sözcükleri ve rapor alt sayfaları
THINKTANK_BASLIK_DISLA = (r"\b(war|wars|military|defen[cs]e|nato|ukrain\w*|russia\w*|taiwan|nuclear|sanctions?|elections?|"
                          r"congress\w*|senate|white house|trump|biden|republican\w*|democrat\w*|supreme court|"
                          r"organi[sz]ed crime|crime|terror\w*|geopolit\w*|diplomac\w*|the fed|federal reserve|treasury|acknowledg\w*)\b|"
                          r"^(methodology|acknowledg\w*|appendix|topline|about this report|data explorer)")
