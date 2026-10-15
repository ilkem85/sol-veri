# 1. BAKIŞ RAPORU — Solana Yeni Token Hipotezleri

**Tarih:** 15 Ekim 2026 (planlanan 17 Ekim; gerekçe ön kayıt günlüğünde)
**Veri:** 11 Eylül – 9 Ekim 2026 girişleri (29 gün), sadece TR 07:00–22:00
**Kod:** `analiz/analiz_v1_1.py` (V1.1, sonuçlar görülmeden ön kayıt metnine uyduruldu)
**Ana ölçü:** R72, %1–%99 kırpılmış ortalama. FARK = sinyal getirisi − eşleşmiş kontrol ortalaması.
**Eşik:** %97,5 güven aralığı, Holm (8 hipotez) p < 0,025.

---

## 1. Karar tablosu

| Hipotez | Yön | n | Gün | FARK | %97,5 GA | Holm p | Dönemler (1/2/3) | İlk-3 alt kümesi | Sonuç |
|---|---|---|---|---|---|---|---|---|---|
| H1 Tekil talep | AL | 3.169 | 29 | −2,2% | [−3,7; −0,9] | 1,000 | −2,8 / −2,8 / −1,1 | — | KALDI |
| H2 Balina alımı | AL | 175 | 28 | +1,7% | [−5,3; +9,8] | 1,000 | +3,6 / +0,8 / +0,7 | — | KALDI |
| H3 Trend 1s ilk 10 | AL | 293 | 29 | **+8,2%** | **[+2,1; +14,5]** | **0,008** | +9,7 / +8,3 / +7,2 | ✗ [−1,2; +23,7] | KALDI (yalnız kural 7) |
| H4 Mezuniyet | AL | 2.122 | 29 | −33,7% | [−37,0; −30,4] | 1,000 | −40,2 / −30,8 / −30,8 | — | KALDI |
| **H5 Kırmızı bayrak** | **KAÇIN** | **1.312** | **28** | **−9,7%** | **[−12,5; −6,7]** | **0,0008** | **−4,0 / −14,8 / −8,5** | **✓ [−19,6; −5,1]** | **GEÇTİ** |
| H6 Şişme hacim | KAÇIN | 1.408 | 29 | +0,8% | [−0,9; +2,5] | 1,000 | +1,1 / +1,3 / +0,0 | — | KALDI |
| H7 Ödemeli görünürlük | İKİ | 360 | 29 | +7,5% | [−1,1; +16,8] | 0,009 | −0,0 / +17,4 / +9,8 | ✗ | KALDI |
| H8 CTO | İKİ | 50 | 22 | — | — | — | — | — | YETERSİZ VERİ |

**H3 notu:** 7 kuraldan 6'sını geçti. Kaldığı tek kural "uygulanabilirlik": günde ~10 sinyal var ve her günün yalnızca ilk 3 sinyaline girilseydi, güven aralığı sıfırı kesiyor.

---

## 2. Ham (kırpılmamış) ortalama — ikincil

| Hipotez | Ham FARK | %97,5 GA | Not |
|---|---|---|---|
| H3 | +13,7% | [+0,4; +34,2] | Bölüm 6 "kuyruğa bağımlı bulgu" kuralı uygulanır → ileri kağıt takibinde izlenir |
| H5 | −6,4% | [−16,9; +12,7] | Karar kırpılmış ortalamayla verildi; ham ortalamada nadir uç kazananlar etkiyi örtüyor |
| H4 | −75,7% | [−169,4; −33,1] | |

Diğer hipotezlerde ham ortalama karar tablosundaki tabloyu değiştirmiyor.

---

## 3. İkincil ufuklar — karar vermez

FARK, kırpılmış. **Kalın** = güven aralığı sıfırı dışlıyor.

| Hipotez | R24 | R72 | R168 | R336* |
|---|---|---|---|---|
| H1 Tekil talep | **−23,6%** | **−2,2%** | **−2,2%** | **−1,6%** |
| H2 Balina alımı | −4,5% | +1,7% | +3,5% | +4,2% |
| H3 Trend 1s ilk 10 | +5,7% | **+8,2%** | **+8,8%** | **+7,3%** |
| H4 Mezuniyet | **−43,5%** | **−33,7%** | **−22,4%** | **−13,9%** |
| H5 Kırmızı bayrak | **+18,8%** | **−9,7%** | **−6,4%** | **−2,5%** |
| H6 Şişme hacim | **−14,3%** | +0,8% | −0,3% | −0,5% |
| H7 Ödemeli görünürlük | +1,0% | +7,5% | **+7,9%** | **+4,5%** |

\*R336: sadece 1 Ekim'e kadarki girişler (20 gün).

---

## 4. Mutlak getiri — karar vermez ama en önemli bağlam

R72 net getiri (maliyet ve ölüm kuralı dahil, kırpılmış):

| Hipotez | n | Ortalama | Medyan | Kârda kapananlar | −%100 olanlar | Kontrol ortalaması |
|---|---|---|---|---|---|---|
| H1 | 3.197 | −93,7% | −100,0% | %2 | %67 | −92,0% |
| H2 | 175 | −82,1% | −97,0% | %3 | %39 | −83,8% |
| H3 | 295 | −74,4% | −94,7% | %6 | %17 | −82,8% |
| H4 | 2.172 | −87,0% | −100,0% | %1 | %76 | −53,9% |
| H5 | 1.312 | −92,2% | −100,0% | %2 | %87 | −82,5% |
| H6 | 1.410 | −91,3% | −99,3% | %2 | %48 | −92,2% |
| H7 | 390 | −71,2% | −95,9% | %8 | %22 | −81,8% |
| H8 | 50 | −48,5% | −73,8% | %12 | %2 | −69,7% |

FARK, akranlara göre **daha az kötü** olmayı ölçer; kâr anlamına gelmez. 72 saat tutulan hiçbir sinyal grubu ortalamada para kazandırmıyor.

---

## 5. Yorum

1. **Tek kanıtlanmış bulgu bir filtre (H5).** Geliştiricisi arzın %10'undan fazlasını tutan ya da mint/freeze yetkisi açık tokenlar, 72 saatte akranlarının ~%10 gerisinde kalıyor. Dikkat: ilk 24 saatte tam tersine akranlarından +%19 iyiler. Klasik "önce pompala, sonra boşalt" deseni. Filtre ancak birkaç gün tutulan pozisyonlarda anlamlı.
2. **En tutarlı aday H3.** GeckoTerminal 1 saatlik trend listesinde ilk 10'a giren tokenlar, akranlarını her ufukta (24 saat – 14 gün) ve her dönemde geçiyor. Ancak mutlak getiri yine de −%74.
3. **"Heyecanı satın almak" en kötüsü.** Mezuniyet anında alım (H4) akranlara göre −%34, keşif anındaki tekil alıcı patlaması (H1) ertesi gün −%24. Asıl AL beklentimizin tam tersi yönde ve çok güçlü.
4. **Şişme hacim (H6) sadece kısa vadede zararlı:** 24 saatte −%14, 72 saatte etki kayboluyor. Vadeli piyasadaki "blowoff hacim başarısızlık işaretidir" bulgusu, burada sadece ilk gün için geçerli.
5. **Temel gerçek:** Bu evrende 72 saatlik al-tut ortalamada sermayenin %70–94'ünü siliyor. Hiçbir sinyal bunu kâra çevirmiyor.

---

## 6. Ön kayda göre sonraki adımlar

- **H5 (GEÇTİ, KAÇIN):** Sadece bundan sonraki ileri testlerde filtre olarak kullanılır. Geçmiş veride filtre + sinyal optimizasyonu yapılmaz.
- **H3 (kuyruğa bağımlı bulgu):** İleri kağıt takibinde izlenir; 2. bakışta tüm veriyle yeniden test edilir.
- **H1, H2, H4, H6, H7, H8:** 2. bakışta (14 Kasım; girişler ≤ 6 Kasım) tüm veriyle bir kez daha test edilir. Son karar odur.
- **Hiçbir AL hipotezi geçmedi:** canlı para yok.
- 9 Ekim sonrası girişlerin sonuçlarına hiç bakılmadı; 2. bakış için temiz kalıyor.

---

## 7. Veri kalitesi

- **"Kayıp" (yok) durumu:** 9.973 tokenın son snapshot'ında medyan likidite 2.368$, saatlik hacim 0$. Sadece 29'u (%0,3) sonradan başka bir listede canlı görüldü. −%100 kuralı veriyle uyumlu; kalıntı likiditesi olan tokenlar için ise karamsar bir varsayım. İki gruba da eşit uygulanıyor.
- **Ölçülemeyen sonuç oranı:** hipotez başına %0,3–4,3 (sınır %10).
- **Koşu kayıpları:** 3–4 Ekim'de GitHub zamanlayıcısı koşuları düşürdü; 5 Ekim'den beri cron-job.org ile düzenli. Kayıp zamana bağlı, sinyal ve kontrolü eşit etkiliyor.
- **Elle doğrulama:** Rastgele seçilen H3 tokenlarının ham fiyat serileri incelendi; getiriler fiyat ve likidite hareketleriyle tutarlı.
- **Hayatta kalma oranları** (14 ve 30 gün, ikincil) 2. bakışta raporlanacak.
