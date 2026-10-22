# CIKIS SIM V1
# ONKAYIT_CIKIS_V1 kurallarini uygulayan simulasyon ve secim motoru.
# Kullanim:
#   python3 cikis_sim_v1.py <repo> --donem egitim [--kor]
#   python3 cikis_sim_v1.py <repo> --donem dogrulama --adaylar adaylar.json --dogrulama-ac
# --kor: getiri hesaplamaz; sadece giris sayilari ve mum kapsamini raporlar.

import os
import sys
import glob
import json
import argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analiz_v1_1 as A  # noqa: E402

# ---- On kayit sabitleri ----
EGITIM = ("2026-09-11 00:00:00", "2026-10-09 23:59:59")
DOGRULAMA = ("2026-10-10 00:00:00", "2026-11-06 23:59:59")
PENCERE_UTC = (4, 19)            # TR 07:00-22:00
MAX_T0_ILK = 12 * 3600
D_ANA = 5
D_IKINCIL = 2
GIRIS_ARAMA = 30 * 60
M1_SON = 1000 * 60               # ilk + 1000 dk
M15_SON = 1000 * 900             # ilk + ~10,4 gun
ALIM_PAYI = 1.01
SATIS_PAYI = 0.99
ORAN_MALIYET = 0.025             # GMGN %1 + DEX %1 + vergi %0,5 (islem basina)
SABIT_MALIYET = 0.00112 / 0.1    # SOL / pozisyon
RUG_LIQ = 1000.0
MIN_N, MIN_GUN = 100, 10
BOOT = 10000
ADAY_MAX, ADAY_KUME_MAX = 3, 2

STOPLAR = {"SL30": 0.30, "SL50": 0.50, "SLyok": None}
KARLAR = {
    "K1": ("tp", [(0.5, 1.0)]),
    "K2": ("tp", [(1.0, 1.0)]),
    "K3": ("tp", [(2.0, 1.0)]),
    "K4": ("tp", [(1.0, 0.5), (3.0, 1.0)]),   # ikinci kademe kalanin tamami
    "K5": ("iz", (0.5, 0.30)),
    "K6": ("iz", (1.0, 0.30)),
    "K7": ("iz", (0.5, 0.50)),
    "K8": ("iz", (1.0, 0.50)),
}
KURALLAR = [(s, k) for s in STOPLAR for k in KARLAR]


def ts_utc(s):
    return int(pd.Timestamp(s, tz="UTC").timestamp())


# ---------------- GIRISLER ----------------

def girisler(kok):
    snap, bal, inf, ol, st = A.yukle(kok)
    d = A.getiri_tablosu(snap, st, 0)
    ilk = st.set_index("token").ilk.to_dict()
    durum = st.set_index("token").durum.to_dict()
    sin = A.sinyaller(d, bal, inf, ol, st)
    kume = {}

    g0 = d.groupby("token").head(1)
    kume["G0"] = pd.DataFrame({"token": g0.token.values, "t0": g0.ts.values, "t_bilgi": g0.ts.values})

    g = d[d.gt_ts.notna()].drop_duplicates("token")
    a = pd.to_numeric(g.alici_h1, errors="coerce")
    sa = pd.to_numeric(g.satici_h1, errors="coerce")
    m = ((a >= 100) & ((a / sa.replace(0, np.nan)).fillna(99) >= 1.3)).fillna(False)
    g = g[m]
    kume["G1"] = pd.DataFrame({"token": g.token.values, "t0": g.ts.values,
                               "t_bilgi": np.maximum(pd.to_numeric(g.gt_ts).values, g.ts.values)})

    h3 = sin["H3 trend 1s ilk10"][1]
    kume["G2"] = pd.DataFrame({"token": h3.token.values, "t0": h3.ts.values, "t_bilgi": h3.ts.values})

    gor = ol[ol.tur.isin(["boost", "reklam", "siparis_boost", "siparis_tokenAd",
                          "siparis_trendingBarAd"])].copy()
    gor = gor[gor.token.isin(ilk)]
    gor["ilk"] = gor.token.map(ilk)
    gor = gor[gor.ts <= gor.ilk + 900].sort_values("ts").drop_duplicates("token")
    kume["G3"] = pd.DataFrame({"token": gor.token.values, "t0": gor.ilk.values,
                               "t_bilgi": np.maximum(gor.ts.values, gor.ilk.values)})

    h2 = sin["H2 balina alimi"][1]
    kume["G4"] = pd.DataFrame({"token": h2.token.values, "t0": h2.ts.values, "t_bilgi": h2.ts.values})

    i = inf.drop_duplicates("token")
    dev = pd.to_numeric(i.dev_yuzde, errors="coerce")
    bayrak = set(i[((dev >= 10) | (i.mint_yetki == "yes") | (i.freeze_yetki == "yes")).fillna(False)].token)

    for k in kume:
        x = kume[k].copy()
        x["t0"] = x.t0.astype(float)
        x["t_bilgi"] = x.t_bilgi.astype(float)
        x["ilk"] = x.token.map(ilk)
        x = x[x.ilk.notna()]
        x = x.sort_values("t0").drop_duplicates("token")
        x = x[~x.token.isin(bayrak)]
        saat = pd.to_datetime(x.t0, unit="s").dt.hour
        x = x[(saat >= PENCERE_UTC[0]) & (saat < PENCERE_UTC[1])]
        x = x[x.t0 <= x.ilk + MAX_T0_ILK]
        x["durum"] = x.token.map(durum)
        kume[k] = x.reset_index(drop=True)

    snap2 = snap[["token", "ts", "liq"]].copy()
    snap2["liq"] = pd.to_numeric(snap2.liq, errors="coerce")
    return kume, snap2


def donem_filtre(kume, donem):
    a, b = (EGITIM if donem == "egitim" else DOGRULAMA)
    a, b = ts_utc(a), ts_utc(b)
    return {k: v[(v.t0 >= a) & (v.t0 <= b)].reset_index(drop=True) for k, v in kume.items()}


# ---------------- MUMLAR ----------------

def mumlari_yukle(kok, tokenler):
    parca = []
    for f in sorted(glob.glob(os.path.join(kok, "data3/mum/*/*.csv.gz"))):
        x = pd.read_csv(f, dtype={"token": str, "pair": str})
        x = x[x.token.isin(tokenler)]
        if len(x):
            parca.append(x)
    if not parca:
        return {}
    m = pd.concat(parca, ignore_index=True)
    m = m.sort_values(["token", "tf", "ts", "v"]).drop_duplicates(["token", "tf", "ts"], keep="last")
    yol = {}
    for t, g in m.groupby("token", sort=False):
        yol[t] = {tf: gg[["ts", "o", "h", "l", "c"]].to_numpy(dtype=float) for tf, gg in g.groupby("tf")}
    return yol


def fiyat_yolu(mum, ilk):
    """1 dk mumlar (ilk + 1000 dk'ya kadar) + 15 dk mumlar (sonrasi, ~10,4 gune kadar)."""
    m1 = mum.get(1)
    m15 = mum.get(15)
    p = []
    if m1 is not None and len(m1):
        p.append(m1[m1[:, 0] < ilk + M1_SON])
    if m15 is not None and len(m15):
        p.append(m15[(m15[:, 0] >= ilk + M1_SON) & (m15[:, 0] < ilk + M15_SON)])
    if not p:
        return None
    y = np.concatenate(p)
    return y[np.argsort(y[:, 0], kind="stable")]


# ---------------- TEK ISLEM ----------------

def _ilk_indeks(maske, bas=0):
    if bas >= len(maske):
        return None
    w = np.flatnonzero(maske[bas:])
    return int(w[0]) + bas if len(w) else None


def islem(yol, giris_i, stop, kar, liq_ts, liq_v, olu):
    """Tek islemin net getirisi. yol: [ts,o,h,l,c] dizisi, giris_i: giris mumu indeksi."""
    y = yol[giris_i:]
    ts, o, h, lo, c = y[:, 0], y[:, 1], y[:, 2], y[:, 3], y[:, 4]
    giris = o[0] * ALIM_PAYI
    n = len(y)

    def sonraki_acilis(i):
        return o[i + 1] if i + 1 < n else None

    def rug(t):
        if liq_ts is None or len(liq_ts) == 0:
            return False
        j = np.searchsorted(liq_ts, t, side="right") - 1
        if j < 0:
            return False
        v = liq_v[j]
        return (not np.isnan(v)) and v < RUG_LIQ

    satislar = []          # (oran, dolum_fiyati)
    kalan = 1.0
    sl_i = None
    sl_fiyat = None
    if stop is not None:
        sl_fiyat = giris * (1 - stop)
        sl_i = _ilk_indeks(lo <= sl_fiyat)

    def stop_dolumu(i):
        no = sonraki_acilis(i)
        f = sl_fiyat if no is None else min(sl_fiyat, no)
        return f * SATIS_PAYI

    tur, par = KARLAR[kar]
    if tur == "tp":
        bas = 0       # TP aramasi baslangici (sonraki kademe ayni mumda dolabilir)
        sl_bas = 0    # SL aramasi baslangici
        for seviye, oran in par:
            hedef = giris * (1 + seviye)
            tp_i = _ilk_indeks(h >= hedef, bas)
            sl_k = None if stop is None else _ilk_indeks(lo <= sl_fiyat, sl_bas)
            if sl_k is not None and (tp_i is None or sl_k <= tp_i):
                satislar.append((kalan, stop_dolumu(sl_k), ts[sl_k]))
                kalan = 0.0
                break
            if tp_i is None:
                break
            miktar = kalan * oran
            satislar.append((miktar, hedef * SATIS_PAYI, ts[tp_i]))
            kalan -= miktar
            if kalan <= 1e-12:
                kalan = 0.0
                break
            bas = tp_i
            sl_bas = tp_i + 1   # tp_i mumunda SL olsaydi once o secilirdi
    else:
        akt, dd = par
        onceki_tepe = np.concatenate([[-np.inf], np.maximum.accumulate(h)[:-1]])
        aktif = onceki_tepe >= giris * (1 + akt)
        tetik = onceki_tepe * (1 - dd)
        iz_i = _ilk_indeks(aktif & (lo <= tetik))
        cand = []
        if iz_i is not None:
            no = sonraki_acilis(iz_i)
            f = tetik[iz_i] if no is None else min(tetik[iz_i], no)
            cand.append((iz_i, f * SATIS_PAYI))
        if sl_i is not None:
            cand.append((sl_i, stop_dolumu(sl_i)))
        if cand:
            i_min = min(c_[0] for c_ in cand)
            ayni = [c_ for c_ in cand if c_[0] == i_min]
            f_min = min(c_[1] for c_ in ayni)
            satislar.append((1.0, f_min, ts[i_min]))
            kalan = 0.0

    if kalan > 1e-12:
        if olu:
            satislar.append((kalan, 0.0, ts[-1]))
        else:
            satislar.append((kalan, c[-1], ts[-1]))
        kalan = 0.0

    getiri = 0.0
    n_satis = 0
    for oran, fiyat, t in satislar:
        if fiyat <= 0 or rug(t):
            continue
        getiri += oran * (fiyat / giris) * (1 - ORAN_MALIYET) * (1 - ORAN_MALIYET)
        n_satis += 1
    return getiri - 1.0 - SABIT_MALIYET * (1 + n_satis)


# ---------------- SIMULASYON ----------------

def simule(kume, yollar, liq, D):
    sonuc = []
    kapsam = {}
    liq_g = {t: (g.ts.to_numpy(dtype=float), g.liq.to_numpy(dtype=float))
             for t, g in liq.sort_values("ts").groupby("token")}
    for k, x in kume.items():
        bulunan = 0
        for r in x.itertuples(index=False):
            mum = yollar.get(r.token)
            if mum is None:
                continue
            yol = fiyat_yolu(mum, r.ilk)
            if yol is None:
                continue
            hedef = r.t_bilgi + D * 60
            i = np.searchsorted(yol[:, 0], hedef, side="left")
            if i >= len(yol) or yol[i, 0] > hedef + GIRIS_ARAMA or yol[i, 0] >= r.ilk + M1_SON:
                continue
            bulunan += 1
            lts, lv = liq_g.get(r.token, (None, None))
            olu = r.durum in ("olu", "yok")
            gun = pd.Timestamp(r.t0, unit="s").strftime("%Y-%m-%d")
            for s, kk in KURALLAR:
                R = islem(yol, i, STOPLAR[s], kk, lts, lv, olu)
                sonuc.append((k, s + "_" + kk, r.token, gun, R))
        kapsam[k] = (len(x), bulunan)
    df = pd.DataFrame(sonuc, columns=["kume", "kural", "token", "gun", "R"])
    return df, kapsam


def gun_bootstrap(degerler, gunler, alt=2.5, ust=97.5, tekrar=BOOT, tohum=7):
    ug, ters = np.unique(gunler, return_inverse=True)
    toplam = np.bincount(ters, weights=degerler)
    adet = np.bincount(ters).astype(float)
    rng = np.random.default_rng(tohum)
    sec = rng.integers(0, len(ug), size=(tekrar, len(ug)))
    ort = toplam[sec].sum(axis=1) / adet[sec].sum(axis=1)
    return np.percentile(ort, [alt, ust])


def ozet(df, alt=2.5, ust=97.5):
    sat = []
    g0 = df[df.kume == "G0"].groupby("kural").R.mean().to_dict()
    for (k, kural), g in df.groupby(["kume", "kural"]):
        v = g.R.to_numpy()
        ngun = g.gun.nunique()
        lo, hi = gun_bootstrap(v, g.gun.to_numpy(), alt, ust) if len(v) > 1 else (np.nan, np.nan)
        sat.append(dict(kume=k, kural=kural, n=len(v), gun=ngun, ort=v.mean(), med=np.median(v),
                        kazanan=(v > 0).mean(), en_kotu5=np.percentile(v, 5), gunluk=len(v) / max(ngun, 1),
                        ga_alt=lo, ga_ust=hi, g0_fark=v.mean() - g0.get(kural, np.nan)))
    return pd.DataFrame(sat)


def secim(oz):
    uygun = oz[(oz.n >= MIN_N) & (oz.gun >= MIN_GUN)].sort_values("ga_alt", ascending=False)
    aday, sayac = [], {}
    for r in uygun.itertuples(index=False):
        if len(aday) >= ADAY_MAX:
            break
        if r.ga_alt <= 0:
            break
        if sayac.get(r.kume, 0) >= ADAY_KUME_MAX:
            continue
        aday.append(dict(kume=r.kume, kural=r.kural, egitim_ort=float(r.ort), egitim_ga_alt=float(r.ga_alt)))
        sayac[r.kume] = sayac.get(r.kume, 0) + 1
    return aday


def dogrula(df, adaylar):
    """On kayit Bolum 8: her aday icin 5 kural."""
    alt = (100.0 - 98.33) / 2   # %98,33 iki yonlu GA (3 aday icin Bonferroni)
    sonuc = []
    for ad in adaylar:
        g = df[(df.kume == ad["kume"]) & (df.kural == ad["kural"])].sort_values("gun")
        v = g.R.to_numpy()
        gunler = g.gun.to_numpy()
        ug = np.unique(gunler)
        r = dict(ad, n=len(v), gun=len(ug))
        if len(v) < 60 or len(ug) < 10:
            r["sonuc"] = "YETERSIZ VERI"
            sonuc.append(r)
            continue
        lo, hi = gun_bootstrap(v, gunler, alt, 100 - alt)
        yari = np.array_split(ug, 2)
        y1 = v[np.isin(gunler, yari[0])].mean()
        y2 = v[np.isin(gunler, yari[1])].mean()
        enbuyuk_cik = np.delete(v, np.argmax(v)).mean()
        k = dict(ortalama=v.mean() > 0, ga=lo > 0, yarilar=(y1 > 0) and (y2 > 0), kuyruk=enbuyuk_cik > 0)
        r.update(ort=float(v.mean()), ga_alt=float(lo), ga_ust=float(hi), yari1=float(y1), yari2=float(y2),
                 enbuyuk_cik=float(enbuyuk_cik), kriterler=k, sonuc="GECTI" if all(k.values()) else "KALDI")
        sonuc.append(r)
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok")
    ap.add_argument("--donem", choices=["egitim", "dogrulama"], required=True)
    ap.add_argument("--kor", action="store_true")
    ap.add_argument("--dogrulama-ac", action="store_true")
    ap.add_argument("--cikti", default="cikis_sonuc")
    ap.add_argument("--adaylar", default="adaylar.json")
    a = ap.parse_args()
    if a.donem == "dogrulama" and not a.dogrulama_ac:
        sys.exit("Dogrulama verisi kilitli. Sadece on kayittaki tarihte --dogrulama-ac ile acilir.")
    os.makedirs(a.cikti, exist_ok=True)
    kume, liq = girisler(a.kok)
    kume = donem_filtre(kume, a.donem)
    tok = set().union(*[set(v.token) for v in kume.values()])
    yollar = mumlari_yukle(a.kok, tok)
    if a.kor:
        print("KOR MOD | donem:", a.donem)
        for k, x in kume.items():
            var = sum(1 for t in x.token if t in yollar)
            print("%s: giris %d | mumu olan token %d" % (k, len(x), var))
        df, kapsam = simule(kume, yollar, liq, D_ANA)
        for k, (n, b) in kapsam.items():
            print("%s: giris mumu bulunan %d / %d (%.0f%%)" % (k, b, n, 100.0 * b / max(n, 1)))
        return
    if a.donem == "dogrulama":
        adaylar = json.load(open(a.adaylar))
    for D, ad in ((D_ANA, "D5"), (D_IKINCIL, "D2")):
        df, kapsam = simule(kume, yollar, liq, D)
        df.to_csv(os.path.join(a.cikti, "islemler_%s_%s.csv.gz" % (a.donem, ad)), index=False)
        oz = ozet(df)
        oz.to_csv(os.path.join(a.cikti, "ozet_%s_%s.csv" % (a.donem, ad)), index=False)
        json.dump({k: list(v) for k, v in kapsam.items()}, open(os.path.join(a.cikti, "kapsam_%s_%s.json" % (a.donem, ad)), "w"))
        if a.donem == "egitim" and D == D_ANA:
            aday = secim(oz)
            json.dump(aday, open(os.path.join(a.cikti, "adaylar.json"), "w"), indent=1)
            print("ADAYLAR:", json.dumps(aday, indent=1) if aday else "YOK -> calisma kapanir")
        if a.donem == "dogrulama" and D == D_ANA:
            dsonuc = dogrula(df, adaylar)
            json.dump(dsonuc, open(os.path.join(a.cikti, "dogrulama.json"), "w"), indent=1, default=str)
            print("DOGRULAMA:", json.dumps(dsonuc, indent=1, default=str))


if __name__ == "__main__":
    main()
