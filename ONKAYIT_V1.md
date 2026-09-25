# ON KAYIT V1 - Solana Yeni Token Hipotezleri

Kayit tarihi: 2026-09-11 (bu dosyanin GitHub commit zamani resmi kayit zamanidir)
Veri: ilkem85/sol-veri, data2/ ve state2/ (Sol Toplayici V2 / V2.1 / V2.2)
Durum: KILITLI. Sonuclara bakilmadan once yazildi.

Bu belgenin amaci: veriyi gormeden neyi, nasil test edecegimizi ve hangi sonucta ne karar verecegimizi sabitlemek. Sonradan hipotez uydurmak, esik kaydirmak, en iyi hucreyi secmek yasak.

---

## 1. Evren

- Kaynak: state2/tokens.csv icindeki tum tokenlar (ilk gorulme >= 2026-09-11).
- Kosullar toplayicida zaten uygulaniyor: pair yasi <= 7 gun, likidite >= 10.000$ (likidite bos ise mcap >= 20.000$).
- Her token 30 gun izlenir: ilk 10 gun sik snapshot (6 saate kadar), 10-30. gunler arasi gunde 1 snapshot.
- Sonuclar sadece bu "gorunur ve likit" evren icin gecerlidir; tum pump.fun tokenlarina genellenemez.

## 2. Temel tanimlar

**Karar ani (t0):** Hipotezin ihtiyac duydugu tum verinin ilk kez mevcut oldugu an. Hicbir ozellik t0'dan sonraki veriyi kullanamaz.

**Giris fiyati:** ts >= t0 olan ilk snapshot'taki `fiyat`. 1 saat icinde snapshot yoksa gozlem disarida kalir.

**Uygulanabilirlik penceresi:** t0, Turkiye saatiyle 07:00-22:00 (UTC 04:00-19:00) arasinda olmali. Disindakiler ana testte sayilmaz, ayrica raporlanir.

**Takip siniri:** R24, R72 ve R168 icin t0 + H <= ilk + 10 gun olmali (sik snapshot donemi). R336 icin t0 + H <= ilk + 30 gun olmali. Asan gozlem o ufuk icin disarida kalir.

**Sonuc fiyati:** t0 + H saatine en yakin snapshot. Tolerans: 24s icin +-1,5s; 72s icin +-3,5s; 168s icin +-6,5s; 336s icin +-12,5s. Token aktif ama tolerans icinde snapshot yoksa gozlem "eksik" sayilir ve disarida kalir. Eksik orani %10'u gecerse raporda uyari verilir.

**Olum kurali:** Token ufuktan once `olu` veya `yok` durumuna gectiyse net getiri = -%100.

**Maliyet modeli (100$ referans pozisyon):**
- Tek yon maliyet = %0,5 ucret + fiyat etkisi
- Fiyat etkisi = 200 / L (L = USD likidite; 10.000$ likiditede %2)
- L olarak giris ve cikis likiditesinin kucugu kullanilir
- Likidite bos (bonding curve) ise tek yon maliyet %2 kabul edilir
- Gidis-donus maliyet = 2 x tek yon

**Ana sonuc olcusu:** 72 saatlik net getiri (R72). Ikincil (karar vermez, sadece rapor): R24, R168, R336 (14 gun), 14 ve 30 gunluk hayatta kalma orani.

## 3. Kontrol grubu ve FARK

Her sinyal gozlemi, ayni zamanda piyasadaki benzer tokenlarla karsilastirilir:

- **Tabaka:** ayni UTC gunu + ayni yas dilimi. Yas dilimleri (t0 anindaki pair yasi): 0-6s, 6-24s, 1-3g, 3-7g.
- **Kontrol:** ayni tabakada, sinyali olmayan ve t0'a +-1 saat icinde snapshot'i bulunan tum tokenlar. Kontrol getirisi ayni maliyet ve olum kurallariyla hesaplanir.
- **FARK** = ortalama(sinyal net getirisi - eslesmis kontrol ortalamasi)

Bu yapi hem piyasa rejimini (memecoin sezonu, genel cokus) hem de yas etkisini notrlestirir.

## 4. Onaylayici hipotezler (8 adet, esikler sabit)

### AL hipotezleri (beklenen: FARK > 0)

**H1 - Tekil talep dengesi**
- t0: `gt_ts` dolu ilk snapshot
- Sinyal: alici_h1 >= 100 VE alici_h1 / satici_h1 >= 1,3
- Mantik: Hacim tek basina manipule edilebilir; farkli cuzdan sayisi daha zor sisirilir.

**H2 - Balina net alimi**
- t0: tokenin ilk balina ozeti satiri
- Sinyal: usd_al >= 2 x usd_sat VE tekil_alici >= 5 (esik: 1.000$ ustu islemler)
- Not: n_islem = 300 olan satirlarda pencere kesiktir; bu satirlar sinyalde kalir ama ayrica raporlanir.

**H3 - Trending 1 saat girisi**
- t0: tokenin evrendeyken GeckoTerminal trend_1h listesinde ilk 10'a ilk girdigi an
- Sinyal: olayin kendisi. Kontrol, ayni anda evrende olup trende girmemis tokenlar.
- Mantik: Trend ilgisi devam mi ediyor, yoksa gec kalinmis tepe mi? Olculecek.

**H4 - Mezuniyet**
- t0: onceki snapshot'ta `liq` bos iken likiditenin ilk kez dolu geldigi snapshot (bonding curve'den AMM havuzuna gecis)
- Sinyal: olayin kendisi. Kontrol, ayni tabakada o anda gecis yapmamis tokenlar.

### KACIN hipotezleri (beklenen: FARK < 0, filtre adayi)

**H5 - Kirmizi bayrak (dagilim ve yetki)**
- t0: tokenin ilk info satiri
- Sinyal: dev_yuzde >= %10 VEYA mint_yetki = yes VEYA freeze_yetki = yes
- (2026-09-18 degisikligi: top10 kosulu cikarildi, bkz. Bolum 10)
- Bos alanlar bayrak sayilmaz, "bilinmiyor" olarak raporlanir.

**H6 - Sisme hacim (blowoff)**
- t0: `liq` dolu ilk snapshot
- Sinyal: vol_h1 / liq >= 10
- Mantik: Vadeli piyasada dogrulanan "asiri hacim = basarisiz pump" bulgusunun memecoinlere tasinip tasinmadigi.

### IKI YONLU hipotezler (yon onceden bilinmiyor)

**H7 - Odemeli gorunurluk**
- t0: tokenin ilk snapshot'i
- Sinyal: paymentTimestamp <= t0 olan siparis_boost, siparis_tokenAd veya siparis_trendingBarAd kaydi; ya da t0'dan once boost/reklam listesinde gorulmus olmak
- Profil siparisi tek basina sinyal sayilmaz.

**H8 - Topluluk devralmasi (CTO)**
- t0: token evrendeyken gorulen ilk cto olayi veya siparis_communityTakeover kaydinin ani (olay tabanli, H3 ve H4 ile ayni yapi)
- Sinyal: olayin kendisi. Kontrol, ayni tabakada o anda CTO olayi olmayan tokenlar.
- (2026-09-25 degisikligi: onceki tanim sadece kesif aninda CTO'su olan tokenlari sayiyordu, bkz. Bolum 10)

## 5. Karar kurallari

Bir hipotezin **GECTI** sayilmasi icin asagidakilerin HEPSI saglanmali:

1. **Orneklem:** sinyal grubu >= 60 gozlem VE >= 10 farkli gun. Saglanmazsa sonuc "YETERSIZ VERI" olur.
2. **Guven araligi:** FARK icin gun-blok bootstrap (10.000 tekrar, gunler yeniden orneklenir) %97,5 GA (iki planli bakis oldugu icin):
   - AL icin alt sinir > 0
   - KACIN icin ust sinir < 0
   - IKI YONLU icin aralik 0'i icermemeli
3. **Permutasyon:** sinyal etiketleri tabaka icinde karistirilir (10.000 tekrar). 8 hipotez icin Holm duzeltmeli p < 0,025 (toplam 0,05'lik hata payi iki bakisa esit bolundu).
4. **Zaman tutarliligi:** giris gunleri ardisik 3 esit doneme bolunur; FARK 3 donemde de ayni yonde olmali.
5. **Kuyruk saglamligi:** FARK'in isareti su iki durumda da korunmali: (a) sonucu en cok destekleyen tek gozlem cikarildiginda, (b) getiriler %1-%99 araligina kirpildiginda.
6. **Ekonomik anlamlilik:** AL icin net FARK >= +%5; KACIN icin <= -%5; IKI YONLU icin |FARK| >= %5.
7. **Uygulanabilirlik:** sinyal gunde ortalama 5'ten fazla ise, her gunun ilk 3 sinyalinden olusan alt kume de 2. ve 4. kurallari gecmeli.

## 6. Sonuca gore aksiyon

**Iki planli bakis:** 1. bakista GECTI olan hipotez kesinlesir, 2. bakista sadece raporlanir. 1. bakista gecemeyen her hipotez (YETERSIZ VERI dahil) 2. bakista tum veriyle, ayni kurallarla bir kez daha test edilir. 2. bakis son karardir; ucuncu bakis yoktur.

- **AL hipotezi GECTI:** Canli para yok. Once 2 haftalik ileri kagit takibi yapilir. Kural: n >= 30 ve ileri FARK > 0 ise kaybi goze alinabilecek kucuk pozisyonla canli teste gecilir; FARK <= 0 ise durulur.
- **KACIN hipotezi GECTI:** Filtre olarak sadece bundan sonraki ileri testlerde kullanilir. Gecmis veride "filtre + sinyal" optimizasyonu yapilmaz.
- **IKI YONLU hipotez GECTI:** Yonune gore AL veya KACIN gibi ele alinir, ayni ileri test kuraliyla.
- **2. bakista da hicbiri gecmezse:** Onaylayici kisim kapanir. Yeni esik taramasi yapilmaz. Sadece Bolum 7'deki kesif bulgulari yeni ileri veriyle test edilebilir; o da gecmezse proje kapanir.

## 7. Kesif bolumu (karar vermez)

Asagidakiler serbestce incelenebilir ama hicbiri dogrudan karar dogurmaz:

- Akilli cuzdan skoru (kazanan tokenlara erken giren cuzdanlar)
- Meta ivmesi (mcap_deg_h24) ve meta uyeligi
- gt_skor ve alt skorlari
- Holder sayisi buyume hizi
- Kilitli likidite yuzdesi
- Ilk 10 cuzdan payi (top10), bonding curve / AMM ayrimi yapilarak
- Trend 5m/6h/24h siralari
- Boost miktari, reklam gosterim sayisi, sosyal link sayisi

**Kesif kurali:** Arama sadece ilk 2/3 gunlerde yapilir; bulunan en fazla 3 aday son 1/3 gunlerde tek seferde test edilir. Gecen aday bile para icin yeterli degildir: toplayicinin yeni topladigi, analizde hic kullanilmamis veride Bolum 5 kurallarini ayrica gecmelidir.

## 8. Takvim

| Tarih | Adim | Sinir |
|---|---|---|
| 2026-09-18 | Haftalik kor rapor 1 | Bolum 8a. Ozellik dagilimlari ilk kez incelenir (H5 notu icin). |
| 2026-09-25, 10-02, 10-09, 10-16 | Haftalik kor raporlar 2-5 | Bolum 8a. |
| 2026-10-09 23:59 UTC | 1. bakis son giris gunu | Bu tarihten sonraki t0'lar 1. bakista kullanilmaz. |
| 2026-10-17 | **1. bakis** | R72 ile karar. R336 sadece 2026-10-01'e kadar girislerde raporlanir. |
| 2026-10-23 - 11-13 | Haftalik kor raporlar 6-9 | Bolum 8a. Gecemeyen hipotezler icin sonuc hesabi YOK. |
| 2026-11-06 23:59 UTC | 2. bakis son giris gunu | |
| 2026-11-14 | **2. bakis (son)** | R72 ile karar. R336 sadece 2026-10-30'a kadar girislerde raporlanir. |

### 8a. Haftalik kor rapor

Amac: toplayicinin sagligini ve orneklemin buyumesini izlemek, sonucu izlememek. Her hafta sonuca bakip "iyi gorundugu gun" durmak, 6 gelene kadar zar atmaya benzer; on kaydi gecersiz kilar.

**Rapora girebilir:**
- Kosu sagligi: planlanan / gerceklesen kosu, atlanan saatler, hata ve 429 sayilari, dosya boyutlari
- Evren: yeni takibe alinan token sayisi, kaynak dagilimi, aktif / olu / yok / bitti sayilari (tum evren, gruplara bolunmeden)
- Veri kapsami: her alanin bos orani (holder, balina, tekil alici vb.)
- Her hipotez icin sinyal sayisi ve farkli gun sayisi, n >= 60 ve >= 10 gun hedefine ilerleme, tahmini yeterli veri tarihi
- Ozellik dagilimlari (ornek: top10 medyani, vol_h1/liq dagilimi)

**Rapora giremez:**
- Sinyal ve kontrol gruplarinin getirisi, hayatta kalmasi veya herhangi bir sonuc karsilastirmasi
- Tek tek tokenlarin sinyal sonrasi performansi
- "Su hipotez iyi gidiyor" turunden her yorum

## 9. Degisiklik kurallari

- Bu belge sadece sonuclara bakilmadan once degistirilebilir.
- Izin verilen tek degisiklik sebebi veri kapsami veya hatadir (ornek: bir alan hep bos geliyor, bir esik veri yapisi yuzunden anlamsiz).
- Ozel not (H5): Bu maddede ongorulen kontrol 2026-09-18'de yapildi ve uygulandi (Bolum 10). Madde kapandi.
- Her degisiklik asagidaki gunluge tarih ve sebep ile yazilir ve ayri commit olarak kaydedilir.
- Sonuclar goruldukten sonra eklenen her sey Bolum 7 (kesif) statusundedir.

## 10. Degisiklik gunlugu

- 2026-09-11: V1 olusturuldu (takip 30 gun, R336 ikincil olcu, iki planli bakis ve haftalik kor rapor dahil).
- 2026-09-18: H5'ten top10 (ilk 10 cuzdan payi) kosulu cikarildi. Sebep: 1. haftalik kor raporda top10 medyani %60,2 cikti; bonding curve'deki tokenlarda medyan %94,5, AMM havuzundakilerde %46,8 ve bazi degerler %100'u asiyor. Alan cuzdan yogunlasmasini degil, buyuk olcude tokenin asamasini olcuyor. top10 Bolum 7'ye kesif degiskeni olarak tasindi. Degisiklik sonuclara bakilmadan yapildi; hicbir getiri hesaplanmamistir.
- 2026-09-25: H8 olay tabanli hale getirildi. Sebep: onceki tanim (kesif aninda CTO kaydi olmasi) 15 gunde sadece 12 pencere ici sinyal uretti; ayni donemde evrene girdikten SONRA CTO alan 69 token tanim disinda kaldi. Bu bir kapsam kusuru: H3 ve H4 olay tabanli kurulmusken H8 yanlislikla kesif anina baglanmisti. Yeni tanimla ayni donemde 43 pencere ici sinyal olusuyor. Takvim degismedi. Degisiklik sonuclara bakilmadan yapildi; hicbir getiri hesaplanmamistir.
