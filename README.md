# Gündem Takip

Kişisel köşe yazıları için gündemi hızlıca görmek için: haberler, Meclis, TÜİK yayın takvimi ve üç aylık özel günler takvimi. Görünüm lacivert, amber ve gri bir palet kullanır.

## Çalıştırma
```
pip install -r requirements.txt
python -m gundem.collect        # günlük veri toplama (haber, Meclis, TÜİK takvimi)
python -m gundem.backfill 30    # son 30 günü doldurur (bir kez, yaklaşık 10 dakika; yeniden çalıştırmak güvenli)
streamlit run app.py            # paneli açar
```

## Kullanım
Sekme yoktur. Sayfanın üstündeki butonlar tek gezinme aracıdır, her şey seçilen butonun altında toplanır.

| Buton | Gösterdiği |
|---|---|
| Haftalık gündem | Toplantıdan önce 5 dakikada okunacak özet: yayın fırsatları (en çok 3), konu başına özet, beklenen yön ve o konunun Meclis bilgisi (Genel Kurul, komisyonlar, Meclisten yansıyan haberler), 14 günlük takvim, geçmiş haberler. Word notu olarak indirilir |
| Kuruluş yayınları | IMF (WEO, GFSR, Fiscal Monitor, çalışma kâğıtları), ILO, Dünya Bankası ve Deloitte yayınları, konu başlıkları altında; son 30 gün, ana raporlar 90 gün. Kuruluş seçicisi vardır |
| Think-tank yayınları | Toplum, aile, demografi, yaşlanma, gençlik, eğitim, istihdam ve emek odaklı 18 kurumun son 14 günlük yayınları, konu başlıkları altında listelenir (güvenlik, dış politika, iklim ve siyaset dışarıda). Haftalık gündemin en altında da yer alır |
| Köşe yazısı | Gazete köşesi için konu önerileri (600-800 kelime, tek güncel kanca, jargonsuz). `data/kose_yazisi_onerileri.json` |
| Takvim | 3 aylık ay yaprağı takvim (özel günler, zirveler, faiz kararları, Meclis, TÜİK), her gelişme madde işaretiyle gün gün sıralı, konuya göre süzülebilir. TÜİK yayın listesi |
| Toplum ve aile, Demografi, Sağlık, Yapay zekâ ve teknoloji, Gençlik ve eğitim, Emek piyasası, Dış ticaret ve döviz piyasası, Makroekonomi, Kalkınma | O konunun sayfası: son haberler, Meclisten yansıyan haberler, yaklaşanlar, geçmiş haberler |

Alt konu seçimi yoktur. Kategoriler `gundem/config.py` içindeki `KATEGORILER` sözlüğünde tanımlıdır.

## Yapı
- `gundem/config.py`: kaynaklar, konu sözlüğü (25 ince konu), 9 kategori
- `gundem/collect.py`: günlük haber toplama
- `gundem/backfill.py`: geçmiş günleri Google Haberler aramasıyla doldurma
- `gundem/kurulus.py`: kuruluş yayınları (`kurulus` tablosu). ILO için ilo.org/publications sayfası ayrıştırılır; IMF, Dünya Bankası ve Deloitte için resmî RSS çalışmadığından Google Haberler `site:` aramaları kullanılır
- `gundem/thinktank.py`: think-tank RSS beslemelerini toplar (18 kurum; Brookings, RAND, Chatham House, Carnegie, Urban Institute botlara kapalı ya da beslemesiz olduğu için kapsam dışı)
- `gundem/events.py`: TBMM Genel Kurul gündemi, komisyon toplantıları, TÜİK yayın takvimi
- `gundem/takvim.py`: özel günler ve planlı olaylar; ay takvimi üretimi
- `gundem/forecast.py`: konu serileri, kapsama düzeltmesi, beklenen yön
- `gundem/ozet.py`: haftalık özet, yayın fırsatı puanı, Word notu
- `gundem/theme.py`: görünüm (renkler, yazı tipleri, grafik teması)
- `.streamlit/config.toml`: Streamlit renk teması
- `.github/workflows/collect.yml`: her sabah otomatik toplama, `data/gundem.db` depoya işlenir

## Takvime olay eklemek
`gundem/takvim.py` içindeki `PLANLI` listesine bir satır ekleyin: başlangıç, bitiş, ad, kapsam (TR, DUNYA, MECLIS) ve **kaynak**. Tarihi doğrulanmamış olay eklemeyin. Her yıl tekrarlanan günler `SABIT` listesindedir.

## Konu sözlüğü
`TOPICS` içinde `kelime` kelimenin başında eşleşir (ekler serbest), `=kelime` yalnızca tam kelime eşleşir, `!kelime` ifade varsa konuyu saymaz (gürültü kesici, örn. `!festival`, `!doğum günü`). Sözlüğü değiştirince `python -m gundem.collect` eski kayıtları da yeniden etiketler.

## Önemli haber seçimi
Benzer başlıklar aynı olay sayılır, en çok kaynakta yer alan olay öne çıkar (eşitlikte en yenisi). Haberin yanında "ve N kaynak daha" yazar.

## Yayın fırsatı puanı
Kategori başına: haber yoğunluğu artışı (0-4 puan), 14 gün içindeki özel gün ya da etkinlik (3, bir haftadan yakınsa 4), TÜİK yayını (2), Meclis maddesi başına 0,75 (en çok 3). 6 ve üstü "Güçlü", 2-6 arası "Orta", 2 altı listelenmez. Sezgiseldir, karar için gerekçeleri okuyun.

## Ölçüm notu
Google Haberler yakın günler için çok daha fazla sonuç verdiğinden ham haber sayıları zamanla yapay olarak artar. Trend, tahmin ve haftalık değişim, her günün toplam kapsamına göre düzeltilmiş ve yalnızca Google Haberler sorgularından hesaplanır. Günlük iş akışı bu yüzden `gundem.backfill 2` komutunu da çalıştırır.

## Veri kaynakları ve sınırları
- Haber: AA, BBC Türkçe, DW, Hürriyet, BBC World (RSS), arXiv. Geçmiş günler Google Haberler aramasından, konu odaklı sorgularla doldurulur; bu yüzden geçmiş konu sayıları gerçek haber hacmini değil, bulunan konu haberlerini gösterir.
- TBMM: Genel Kurul ve komisyon gündemi sayfaları (herkese açık HTML). Sayfa biçimi değişirse ayrıştırıcı bozulabilir. Tutanak metinleri henüz yok.
- TÜİK: tuik.gov.tr Ulusal Veri Yayımlama Takvimi sayfasının kendi kullandığı herkese açık JSON.
- X (Twitter) ve diğer sosyal gündem verisi şimdilik kapsam dışı. X API anahtarı hazır olunca eklenecek.

## Yol haritası
X API, TBMM tutanak ve soru önergesi metinleri, konu modeli (BERTopic), günlük özet, dini günler (Diyanet takvimiyle doğrulanınca).


Geliştirici: Meryem Türel, 2026
