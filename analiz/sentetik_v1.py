# SENTETIK VERI V1 - analiz_v1.py'yi dogrulamak icin
# Bilinen bir etki yerlestirir: H1 sinyali olan tokenlar 72 saatte +ETKI kadar farkli.
# Diger hipotezler null (etkisiz) olmalidir.

import os
import csv
import sys
import numpy as np

ETKI = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
KOK = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sentetik"
GURULTU = float(sys.argv[3]) if len(sys.argv) > 3 else 0.08
GUN = 20
TOKEN_GUN = 45
ADIM = 2 * 3600

BAS = 1789000000 - (1789000000 % 86400)
rng = np.random.default_rng(42)

os.makedirs(KOK, exist_ok=True)
snap = {}
bal, inf, ol, st = [], [], [], []


def yaz(yol, baslik, satir):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(baslik)
        w.writerows(satir)


def gunad(ts):
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"), \
           datetime.datetime.utcfromtimestamp(ts).strftime("%H%M")


no = 0
for g in range(GUN):
    for i in range(TOKEN_GUN):
        no += 1
        tok = "T%05d" % no
        ilk = BAS + g * 86400 + int(rng.integers(0, 86400))
        pair = ilk - int(rng.integers(0, 3 * 86400))
        h1 = rng.random() < 0.25          # H1 sinyali
        olur = rng.random() < 0.45        # token oluyor mu
        omur = int(rng.integers(20, 90)) if olur else 90
        fiyat = float(rng.uniform(1e-6, 1e-4))
        liq = float(rng.lognormal(10, 1))
        piyasa = rng.normal(0, 0.02)      # gune ozgu rejim
        ts = ilk
        k = 0
        bonding = rng.random() < 0.4
        mezun_saat = float(rng.uniform(2, 30))
        while k < omur and ts < BAS + (GUN + 12) * 86400:
            sap = rng.normal(piyasa, GURULTU)
            if h1 and 0 < (ts - ilk) <= 72 * 3600:
                sap += ETKI / 36.0
            fiyat = max(fiyat * (1 + sap), 1e-12)
            liq = max(liq * (1 + rng.normal(0, 0.05)), 10)
            bos_liq = bonding and (ts - ilk) < mezun_saat * 3600
            gn, hm = gunad(ts)
            snap.setdefault((gn, hm), []).append([
                ts, tok, pair, "%.12f" % fiyat, "" if bos_liq else round(liq, 2), round(liq * 8, 2),
                round(liq * (rng.uniform(10, 40) if rng.random() < 0.15 else rng.uniform(0.1, 5)), 2),
                int(rng.integers(120, 400)) if h1 else int(rng.integers(5, 140)),
                int(rng.integers(20, 90)) if h1 else int(rng.integers(20, 200)),
                ts])
            ts += 1800 if (ts - ilk) < 24 * 3600 else ADIM
            k += 1
        st.append([tok, "test", "test", ilk, "P" + tok, ts, ilk, ilk, 0, 0,
                   "olu" if olur else "aktif"])
        bal.append([ilk + 400, tok, round(rng.uniform(0, 5e4), 2), round(rng.uniform(0, 5e4), 2),
                    int(rng.integers(0, 20))])
        inf.append([ilk + 400, tok, round(rng.uniform(0, 30), 2),
                    "yes" if rng.random() < 0.05 else "no", "no"])
        if rng.random() < 0.15:
            ol.append([ilk + 400, tok, "trend_1h", int(rng.integers(1, 20)), ""])
        if rng.random() < 0.12:
            ol.append([ilk + 30, tok, "boost", 30, 100])
        if rng.random() < 0.10:
            ol.append([ilk + int(rng.integers(0, 4 * 86400)), tok, "cto", "", ""])

K = ["ts", "token", "pair_olusma", "fiyat", "liq", "mcap", "vol_h1", "alici_h1", "satici_h1", "gt_ts"]
for (gn, hm), satir in snap.items():
    yaz(os.path.join(KOK, "data2/snap", gn, hm + ".csv"), K, satir)
yaz(os.path.join(KOK, "data2/balina/2026-09-11/0000.csv"),
    ["ts", "token", "usd_al", "usd_sat", "tekil_alici"], bal)
yaz(os.path.join(KOK, "data2/info/2026-09-11.csv"),
    ["ts", "token", "dev_yuzde", "mint_yetki", "freeze_yetki"], inf)
yaz(os.path.join(KOK, "data2/olay/2026-09-11/0000.csv"), ["ts", "token", "tur", "d1", "d2"], ol)
yaz(os.path.join(KOK, "state2/tokens.csv"),
    ["token", "ilk_kaynak", "kaynak", "ilk", "pair", "son_snap", "son_info", "son_trade",
     "olu_say", "yok_say", "durum"], st)
print("sentetik veri hazir:", KOK, "| token", no, "| etki %.2f" % ETKI)
