# ON KAYIT - CIKIS CALISMASI V1

Kayit tarihi: 2026-10-15 (bu dosyanin GitHub commit zamani resmi kayit zamanidir)
Veri: ilkem85/sol-veri, data3/mum (dakikalik mumlar) + data2/ ve state2/ (Sol Toplayici V2.x)
Durum: KILITLI. Mum verisiyle hicbir getiri hesaplanmadan once yazildi.

ON KAYIT V1'in (sabit 72 saat tutma) devamidir. Orada tum gruplar 72 saatte ortalama %70-94 kaybetti, ama tokenlarin %22-35'i ilk saatlerde +%50 gordu. Bu calisma su soruyu sorar:

**GMGN'nin uygulayabildigi cikis kurallariyla, 500 TL'lik pozisyonlarda, gercekci maliyetler sonrasi mutlak net kar eden bir giris + cikis kombinasyonu var mi?**

---

## 1. Giris kumeleri (5)

Tanimlar ON KAYIT V1 Bolum 4 ile aynidir.

| Kod | Giris | Neden |
|---|---|---|
| G0 | Taban: her tokenin ilk gozlemi | Sinyalin katkisini olcmek icin referans |
| G1 | H1 tekil talep | En yuksek erken zirve orani (%35'i 24 saatte +%50) |
| G2 | H3 trend 1s ilk 10 | 1. bakista en tutarli aday |
| G3 | H7 odemeli gorunurluk | Uzun ufukta pozitif |
| G4 | H2 balina alimi | Kucuk ama ayri bir mekanizma |

Tum kumelere uygulanan kosullar:
- **H5 filtresi** (1. bakista GECTI): dev_yuzde >= %10 veya mint/freeze yetkisi acik tokenlar cikarilir. Bilgisi olmayanlar kalir.
- t0, TR 07:00-22:00 arasinda olmali (giris elle yapilacak).
- t0 <= ilk gorulme + 12 saat (1 dakikalik mum kapsami icin).
- Token basina sadece ilk sinyal.

## 2. Giris uygulamasi

- **Bilgi ani (t_bilgi):** sinyalin dayandigi verinin toplayicida olustugu en gec an. G0 ve G3: ilk snapshot zamani. G1: tekil alici verisinin geldigi an (gt_ts). G2: trend olayinin kaydedildigi an. G4: balina ozetinin kaydedildigi an. Gecikme t0'dan degil t_bilgi'den sayilir.
- **Gecikme D = 5 dakika (ana olcu, karar verir).** D = 2 dakika ikincil olarak raporlanir, karar vermez.
- Giris fiyati: t_bilgi + D'den sonraki ilk 1 dk mumun acilisi x 1,01 (olumsuz dolum payi).
- t_bilgi + D ile t_bilgi + D + 30 dk arasinda hic mum yoksa (islem yok) gozlem disarida kalir.
- Pozisyon: 0,1 SOL (~500 TL).

## 3. Cikis kurallari ailesi (24 kural)

Sadece GMGN TP/SL ekraninda kurulabilen kurallar.

**Stop (3):** SL -%30, SL -%50, stop yok

**Kar tarafi (8):**

| Kod | Kural |
|---|---|
| K1 | TP +%50'de tumunu sat |
| K2 | TP +%100'de tumunu sat |
| K3 | TP +%200'de tumunu sat |
| K4 | +%100'de %50 sat, +%300'de kalan %50'yi sat |
| K5 | Iz suren: aktivasyon +%50, geri cekilme %30, tumunu sat |
| K6 | Iz suren: aktivasyon +%100, geri cekilme %30, tumunu sat |
| K7 | Iz suren: aktivasyon +%50, geri cekilme %50, tumunu sat |
| K8 | Iz suren: aktivasyon +%100, geri cekilme %50, tumunu sat |

3 stop x 8 kar kurali = 24 kural. 5 giris kumesi x 24 kural = **120 hucre**. Izgara buyutulmez.

## 4. Simulasyon kurallari

**Fiyat yolu:** Ilk ~16,7 saat 1 dk mumlar, sonrasi 15 dk mumlar. 10,4. gunde hala acik pozisyon son kapanistan satilir. Ayni token birden fazla havuzda islem gorduyse her dilim icin hacmi en yuksek havuzun mumu kullanilir.

**Dolumlar (kotumser):**
- TP: mumun yuksegi >= hedef ise hedef x 0,99'dan dolar.
- SL ve iz suren: tetiklenince dolum = min(tetik fiyati, sonraki mumun acilisi) x 0,99.
- Ayni mumda hem TP hem SL mumkunse once SL varsayilir.
- Iz suren tepe sadece onceki mumlarin yuksekleriyle guncellenir; ayni mum icinde iyimser varsayim yok.
- Cikis anindaki son bilinen snapshot likiditesi 1.000$'in altindaysa (rug) dolum 0, yani -%100.
- Pozisyon kapanmadan token olu/yok olduysa ve sonrasinda mum yoksa: -%100.

**Maliyet (her alim ve her satis ayri islem):**
- Oransal: GMGN %1 + DEX/launchpad ucreti %1 + vergi tamponu %0,5 = **islem basina %2,5**
- Sabit: islem basina 0,00112 SOL (tip 0,001 + oncelik ~0,00012) = 0,1 SOL'de **%1,12**
- Kismi satislar ayri islem sayilir.
- Ornek: tek alim + tek satis = yaklasik %7,2 gidis-donus maliyet, dolum paylari haric.

## 5. Olcu

**Ana olcu:** islem basina mutlak net getiri (pozisyona gore %).
Ikincil (karar vermez): medyan, kazanan islem orani, en kotu %5'lik dilim, gunluk islem sayisi, ayni kuralin G0'daki sonucuyla fark, D = 2 dk sonuclari.

## 6. Donemler

| Donem | t0 araligi | Kullanim |
|---|---|---|
| Egitim | 2026-09-11 - 2026-10-09 | Kural secimi |
| Dogrulama | 2026-10-10 - 2026-11-06 | Tek seferlik test (bu veriye hicbir sekilde bakilmadi) |
| Ileri kagit | 2026-11-07 sonrasi | Gecerse |

## 7. Secim (egitim donemi)

1. Her hucre icin: n >= 100 ve >= 10 farkli gun. Saglamayan hucre secilemez.
2. Siralama **en yuksek ortalamaya gore degil**, gun-blok bootstrap (10.000 tekrar) %95 GA alt sinirina gore yapilir.
3. En fazla **3 aday** secilir: GA alt siniri en yuksek 3 hucre; ayni giris kumesinden en fazla 2.
4. Egitimde GA alt siniri > 0 olan hucre yoksa **calisma burada kapanir**; dogrulamaya gecilmez.
5. Secilen kural izgaranin kenarindaysa (ornegin K3 veya SL -%30) raporda belirtilir; yeni izgara eklenmez.

## 8. Dogrulama (tek seferde)

Tarih: dogrulama donemi tokenlarinin mumlari tamamlaninca (tahmini 2026-11-20).

Bir aday, asagidakilerin HEPSI saglanirsa **GECER**:
1. n >= 60 ve >= 10 farkli gun
2. Ortalama net getiri > 0
3. Gun-blok bootstrap **%98,33** GA alt siniri > 0 (3 aday icin Bonferroni)
4. Dogrulama donemi ikiye bolununce iki yarida da ortalama > 0
5. En karli tek islem cikarilinca ortalama hala > 0

## 9. Sonuca gore aksiyon

- **Bir aday gecerse:** canli para yok. Once 2 hafta ileri kagit takibi (canli uyari, kayitli sanal islemler). n >= 30 ve ortalama net > 0 ise 500 TL'lik pozisyonlarla canli teste gecilir. Gunluk islem ve acik pozisyon sinirlari o zaman belirlenir.
- **Hicbiri gecmezse:** cikis calismasi kapanir. Yeni izgara veya yeni giris kumesi denenmez.

## 10. Bilinen sinirlar

- Sinyaller 30 dakikalik toplayici ritmiyle uretiliyor. Canli kullanimda da ayni ritim gecerli olacagi icin gecikme simulasyona dahil (D).
- D = 5 dk varsayimi, uyarinin t_bilgi'den sonra en gec ~1 dakikada telefona ulasmasini ve hemen alim yapilmasini gerektirir. Canli uyari sistemi henuz kurulmadi; ileri kagit takibinde gercek gecikme olculecek ve 5 dakikayi asarsa sonuc gecersiz sayilacak.
- GMGN TP/SL emirlerinin ag yogunlugundaki gercek gecikmesi bilinmiyor; kotumser dolum paylari bunu kismen karsilar.
- Token bazli vergiler verimizde yok; %0,5 tampon ortalama varsayimdir.
- Sandvic (MEV) kaybi ayrica modellenmedi; Anti-MEV "Red." ve %15 kayma limiti kullanilacak.
- Gelistirici satisinda otomatik cikis test edilemiyor (veride gelistirici islemleri yok).

## 11. Degisiklik kurallari

- Bu belge sadece mum verisiyle getiri hesaplanmadan once degistirilebilir.
- Sonuc goruldukten sonra eklenen her sey kesif statusundedir ve karar vermez.
- Her degisiklik asagidaki gunluge tarih ve sebep ile yazilir, ayri commit olarak kaydedilir.

## 12. Degisiklik gunlugu

- 2026-10-15: V1 olusturuldu (taslakta 10 dk olan giris gecikmesi, kullanici talebiyle commit oncesi 5 dk ana / 2 dk ikincil yapildi; gecikme t_bilgi'den sayilir).
