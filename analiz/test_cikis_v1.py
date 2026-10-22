# TEST CIKIS V1 - cikis_sim_v1.py icin elle hesaplanmis senaryolar
# Kullanim: python3 test_cikis_v1.py analiz
import sys, numpy as np
sys.path.insert(0, sys.argv[1])
import cikis_sim_v1 as C
F = (1 - C.ORAN_MALIYET) ** 2
def beklenen(satislar, giris):  # satislar: [(oran, dolum)] dolum>0
    return sum(o * f / giris * F for o, f in satislar) - 1 - C.SABIT_MALIYET * (1 + len(satislar))
def yol(mumlar):  # [(o,h,l,c)]
    return np.array([[1000 + 60 * i, *m] for i, m in enumerate(mumlar)], dtype=float)
G = 1.0 * C.ALIM_PAYI
ok = True
def kontrol(ad, R, E):
    global ok
    d = abs(R - E) < 1e-9
    ok &= d
    print("%-38s R=%+.5f beklenen=%+.5f %s" % (ad, R, E, "OK" if d else "HATA"))
y = yol([(1.0, 1.05, 0.98, 1.02), (1.02, 1.6, 1.0, 1.5), (1.5, 1.5, 1.2, 1.3)])
kontrol("T1 K1 TP+%50 doldu", C.islem(y, 0, None, "K1", None, None, False), beklenen([(1, G * 1.5 * .99)], G))
y = yol([(1.0, 1.05, 0.98, 1.02), (1.02, 1.6, 0.6, 1.5), (0.8, 0.9, 0.7, 0.8)])
kontrol("T2 ayni mumda TP+SL -> SL", C.islem(y, 0, 0.30, "K1", None, None, False), beklenen([(1, min(G * .7, 0.8) * .99)], G))
y = yol([(1.0, 1.05, 0.98, 1.02), (1.0, 1.0, 0.6, 0.65), (0.3, 0.35, 0.2, 0.3)])
kontrol("T3 bosluklu dusus SL30", C.islem(y, 0, 0.30, "K2", None, None, False), beklenen([(1, 0.3 * .99)], G))
y = yol([(1.0, 1.0, 0.99, 1.0), (1.0, 1.3, 1.0, 1.3), (1.3, 1.6, 1.25, 1.6), (1.6, 2.0, 1.5, 1.9), (1.9, 1.9, 1.3, 1.35), (1.35, 1.4, 1.2, 1.3)])
kontrol("T4 iz suren K5 (akt50 dd30)", C.islem(y, 0, None, "K5", None, None, False), beklenen([(1, min(2.0 * .7, 1.35) * .99)], G))
y = yol([(1.0, 1.0, 0.99, 1.0), (1.0, 2.1, 1.0, 2.0), (2.0, 4.2, 1.9, 4.0), (4.0, 4.0, 1.0, 1.0)])
kontrol("T5 K4 iki kademe", C.islem(y, 0, None, "K4", None, None, False), beklenen([(0.5, G * 2 * .99), (0.5, G * 4 * .99)], G))
y = yol([(1.0, 1.0, 0.99, 1.0), (1.0, 2.1, 1.0, 2.0), (2.0, 2.0, 0.4, 0.45), (0.45, 0.5, 0.4, 0.45)])
kontrol("T6 K4 TP1 sonra SL50", C.islem(y, 0, 0.50, "K4", None, None, False), beklenen([(0.5, G * 2 * .99), (0.5, min(G * .5, 0.45) * .99)], G))
y = yol([(1.0, 1.1, 0.9, 1.0), (1.0, 1.2, 0.8, 0.9), (0.9, 0.95, 0.5, 0.6)])
kontrol("T7 olu token, stop yok", C.islem(y, 0, None, "K3", None, None, True), -1 - C.SABIT_MALIYET)
y = yol([(1.0, 1.05, 0.98, 1.02), (1.02, 1.6, 1.0, 1.5)])
lts = np.array([900.0, 1050.0]); lv = np.array([5000.0, 500.0])
kontrol("T8 rug: TP aninda likidite < 1000$", C.islem(y, 0, None, "K1", lts, lv, False), -1 - C.SABIT_MALIYET)
y = yol([(1.0, 1.1, 0.9, 1.0), (1.0, 1.2, 0.8, 1.1), (1.1, 1.2, 1.0, 1.15)])
kontrol("T9 yol sonu, canli token", C.islem(y, 0, None, "K3", None, None, False), beklenen([(1, 1.15)], G))
y = yol([(1.0, 1.0, 0.99, 1.0), (1.0, 1.3, 1.0, 1.3), (1.3, 1.6, 1.25, 1.6), (1.6, 1.6, 1.0, 1.05), (1.05, 1.1, 0.6, 0.65), (0.65, 0.7, 0.6, 0.6)])
kontrol("T10 K7+SL30 ayni mum, kotu dolum", C.islem(y, 0, 0.30, "K7", None, None, False), beklenen([(1, min(1.6 * .5, 0.65) * .99)], G))
print("TUM TESTLER:", "GECTI" if ok else "HATA VAR")
