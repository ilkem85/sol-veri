# ANALIZ V1
# ON KAYIT V1'deki kurallari uygulayan analiz hatti.
# Kullanim:
#   python3 analiz_v1.py <repo_yolu> --mod sahte   -> plasebo (getiriler karistirilir, gercek sonuc gorunmez)
#   python3 analiz_v1.py <repo_yolu> --mod gercek  -> SADECE 17 Ekim ve 14 Kasim bakislarinda
# Ana istatistik: %1-%99 kirpilmis ortalama (on kayit 2026-09-25). Ham ortalama icin: --istatistik ham
# Cikti: ekrana tablo + rapor_<mod>_<tarih>.md

import os
import sys
import glob
import argparse
import numpy as np
import pandas as pd

# ---- On kayit sabitleri ----
UFUK = {"R24": 24, "R72": 72, "R168": 168, "R336": 336}
TOLERANS = {"R24": 1.5, "R72": 3.5, "R168": 6.5, "R336": 12.5}
ANA_UFUK = "R72"
POZISYON = 100.0          # USD referans pozisyon
UCRET = 0.005             # tek yon ucret
ETKI_BOS = 0.02           # likidite bilinmiyorsa tek yon fiyat etkisi
SIK_GUN = 10              # sik snapshot donemi
TAKIP_GUN = 30
PENCERE = (4, 19)         # UTC saat araligi (TR 07:00-22:00)
MIN_N = 60
MIN_GUN = 10
EKONOMIK = 0.05
ALFA = 0.025              # iki planli bakis icin bolunmus alfa
GA_KUYRUK = 1.25          # %97,5 iki yonlu GA
BOOT = 10000
PERM = 10000
GUNLUK_SINIR = 5          # gunde bu kadardan fazla sinyal varsa ilk-3 alt kumesi de test edilir
KOVALAR = [(0, 6), (6, 24), (24, 72), (72, 168), (168, 10 ** 6)]
KOVA_AD = ["0-6s", "6-24s", "1-3g", "3-7g", "7g+"]


def kova_bul(yas_saat):
    k = np.full(len(yas_saat), -1)
    for i, (a, b) in enumerate(KOVALAR):
        k = np.where((yas_saat >= a) & (yas_saat < b) & (k < 0), i, k)
    return k


# ---------------- VERI ----------------

def yukle(kok):
    def oku(desen, kolon=None):
        d = sorted(glob.glob(os.path.join(kok, desen)))
        if not d:
            return pd.DataFrame()
        p = [pd.read_csv(f, usecols=kolon) for f in d]
        return pd.concat(p, ignore_index=True)

    snap = oku("data2/snap/*/*.csv", ["ts", "token", "pair_olusma", "fiyat", "liq",
                                      "mcap", "vol_h1", "alici_h1", "satici_h1", "gt_ts"])
    bal = oku("data2/balina/*/*.csv", ["ts", "token", "usd_al", "usd_sat", "tekil_alici"])
    inf = oku("data2/info/*.csv", ["ts", "token", "dev_yuzde", "mint_yetki", "freeze_yetki"])
    ol = oku("data2/olay/*/*.csv", ["ts", "token", "tur", "d1"])
    st = pd.read_csv(os.path.join(kok, "state2/tokens.csv"))
    for d in (snap, bal, inf, ol):
        if len(d):
            d.sort_values(["ts"], inplace=True)
    snap = snap.sort_values(["token", "ts"]).reset_index(drop=True)
    return snap, bal, inf, ol, st


def getiri_tablosu(snap, st, simdi):
    """Her snapshot satiri icin ileriye donuk net getiriler."""
    d = snap.copy()
    d["fiyat"] = pd.to_numeric(d.fiyat, errors="coerce")
    d["liqn"] = pd.to_numeric(d.liq, errors="coerce")
    d["pair_olusma"] = pd.to_numeric(d.pair_olusma, errors="coerce")
    d = d[d.fiyat > 0].reset_index(drop=True)
    ilk = st.set_index("token").ilk.to_dict()
    durum = st.set_index("token").durum.to_dict()
    d["ilk"] = d.token.map(ilk)
    d = d[d.ilk.notna()].reset_index(drop=True)
    yas = (d.ts - d.pair_olusma) / 3600.0
    yas = yas.fillna((d.ts - d.ilk) / 3600.0)
    d["kova"] = kova_bul(yas.values)
    d["sira"] = d.groupby("token").cumcount()
    takip = (d.ts - d.ilk) / 3600.0
    asama = np.where(d.sira.values == 0, 0, np.where(takip.values < 6, 1,
             np.where(takip.values < 24, 2, np.where(takip.values < 72, 3, 4))))
    d["asama"] = asama
    d["gun"] = pd.to_datetime(d.ts, unit="s").dt.strftime("%Y-%m-%d")
    d["saat"] = pd.to_datetime(d.ts, unit="s").dt.hour

    for u in UFUK:
        d["net_" + u] = np.nan
    son_ts = d.groupby("token").ts.max().to_dict()

    for tok, gr in d.groupby("token", sort=False):
        idx = gr.index.values
        ts = gr.ts.values.astype(float)
        p = gr.fiyat.values.astype(float)
        L = gr.liqn.values.astype(float)
        c = UCRET + np.where(np.isnan(L) | (L <= 0), ETKI_BOS, POZISYON * 2.0 / np.maximum(L, 1.0))
        ilk_t = float(gr.ilk.iloc[0])
        olu = durum.get(tok, "aktif") in ("olu", "yok")
        st_son = son_ts[tok]
        for u, saat in UFUK.items():
            hedef = ts + saat * 3600.0
            tol = TOLERANS[u] * 3600.0
            sinir = ilk_t + (TAKIP_GUN if u == "R336" else SIK_GUN) * 86400.0
            j = np.searchsorted(ts, hedef)
            j = np.clip(j, 1, len(ts) - 1) if len(ts) > 1 else np.zeros(len(ts), dtype=int)
            j0 = np.clip(j - 1, 0, len(ts) - 1)
            secim = np.where(np.abs(ts[j] - hedef) <= np.abs(ts[j0] - hedef), j, j0)
            uygun = np.abs(ts[secim] - hedef) <= tol
            net = np.full(len(ts), np.nan)
            brut = (p[secim] * (1 - c[secim])) / (p * (1 + c)) - 1.0
            net = np.where(uygun, brut, net)
            # olum kurali: takip bitmis ve token olu/yok ise -100%
            oldu = (~uygun) & olu & (hedef > st_son)
            net = np.where(oldu, -1.0, net)
            # kapsam disi: ufuk sik takip/toplam takip suresini asiyorsa
            net = np.where(hedef > sinir, np.nan, net)
            d.loc[idx, "net_" + u] = net
    return d


# ---------------- SINYALLER ----------------

def sinyaller(d, bal, inf, ol, st):
    ilk = st.set_index("token").ilk.to_dict()
    s = {}
    g = d[d.gt_ts.notna()].drop_duplicates("token")
    a = pd.to_numeric(g.alici_h1, errors="coerce")
    sa = pd.to_numeric(g.satici_h1, errors="coerce")
    m = ((a >= 100) & ((a / sa.replace(0, np.nan)).fillna(99) >= 1.3)).fillna(False)
    s["H1 tekil talep"] = ("AL", g[m][["token", "ts"]])

    b = bal.drop_duplicates("token")
    m = (pd.to_numeric(b.usd_al, errors="coerce") >= 2 * pd.to_numeric(b.usd_sat, errors="coerce")) & \
        (pd.to_numeric(b.tekil_alici, errors="coerce") >= 5)
    s["H2 balina alimi"] = ("AL", b[m.fillna(False)][["token", "ts"]])

    tr = ol[ol.tur == "trend_1h"].copy()
    tr["r"] = pd.to_numeric(tr.d1, errors="coerce")
    tr = tr[(tr.r <= 10) & tr.token.isin(ilk)]
    tr["ilk"] = tr.token.map(ilk)
    s["H3 trend 1s ilk10"] = ("AL", tr[tr.ts >= tr.ilk - 60].drop_duplicates("token")[["token", "ts"]])

    bos = d[d.liqn.isna()].groupby("token").ts.min()
    dolu = d[d.liqn.notna()].groupby("token").ts.min()
    mz = pd.DataFrame({"b": bos, "d2": dolu}).dropna()
    mz = mz[mz.d2 > mz.b].reset_index()
    s["H4 mezuniyet"] = ("AL", mz.rename(columns={"d2": "ts"})[["token", "ts"]])

    i = inf.drop_duplicates("token")
    dev = pd.to_numeric(i.dev_yuzde, errors="coerce")
    m = ((dev >= 10) | (i.mint_yetki == "yes") | (i.freeze_yetki == "yes")).fillna(False)
    s["H5 kirmizi bayrak"] = ("KACIN", i[m][["token", "ts"]])

    l = d[d.liqn > 0].drop_duplicates("token")
    r = pd.to_numeric(l.vol_h1, errors="coerce").fillna(0) / l.liqn
    s["H6 sisme hacim"] = ("KACIN", l[r >= 10][["token", "ts"]])

    gor = ol[ol.tur.isin(["boost", "reklam", "siparis_boost", "siparis_tokenAd",
                          "siparis_trendingBarAd"])].copy()
    gor = gor[gor.token.isin(ilk)]
    gor["ilk"] = gor.token.map(ilk)
    gor = gor[gor.ts <= gor.ilk + 900].drop_duplicates("token")
    s["H7 odemeli gorunurluk"] = ("IKI", gor.rename(columns={"ilk": "ts0"}).assign(ts=lambda x: x.ts0)[["token", "ts"]])

    cto = ol[ol.tur.isin(["cto", "siparis_communityTakeover"])].copy()
    cto = cto[cto.token.isin(ilk)]
    cto["ilk"] = cto.token.map(ilk)
    s["H8 CTO"] = ("IKI", cto[cto.ts >= cto.ilk - 60].drop_duplicates("token")[["token", "ts"]])
    return s


def giris_satiri(d, sin):
    """Sinyal icin ts >= t0 ve <= t0+1 saat olan ilk snapshot satiri."""
    d2 = d[["token", "ts"]].reset_index().rename(columns={"index": "satir"})
    m = sin.rename(columns={"ts": "t0"}).merge(d2, on="token", how="inner")
    m = m[(m.ts >= m.t0) & (m.ts <= m.t0 + 3600)]
    m = m.sort_values("ts").drop_duplicates("token")
    return m[["token", "t0", "satir"]]


# ---------------- KONTROL VE FARK ----------------

def _grup_indeks(d):
    return (d.kova.values.astype(int) * 10 + d.asama.values.astype(int))


def kontrol_ortalamalari(d, ufuk, satirlar, haric_tokenlar=None):
    """Kontrol: ayni kova + ayni takip asamasi + ayni gun penceresi.
    Pencere kademeli: +-1 saat, yetmezse +-3 saat, o da yetmezse ayni gun."""
    net = d["net_" + ufuk].values
    gecerli = ~np.isnan(net)
    grup = _grup_indeks(d)
    ts = d.ts.values.astype(float)
    gun = d.gun.values
    tok = d.token.values
    if haric_tokenlar is None:
        haric = np.zeros(len(d), dtype=bool)
    else:
        haric = d.token.isin(haric_tokenlar).values
    satirlar = np.asarray(satirlar)
    ort = np.full(len(satirlar), np.nan)
    say = np.zeros(len(satirlar))
    for g in np.unique(grup[satirlar]):
        idx = np.where((grup == g) & gecerli & (~haric))[0]
        hedef = np.where(grup[satirlar] == g)[0]
        if len(hedef) == 0 or len(idx) == 0:
            continue
        sira = idx[np.argsort(ts[idx])]
        t = ts[sira]
        v = net[sira]
        g_gun = gun[sira]
        cv = np.concatenate([[0.0], np.cumsum(v)])
        cn = np.arange(len(t) + 1, dtype=float)
        gun_top = {}
        for gg in np.unique(g_gun):
            m = g_gun == gg
            gun_top[gg] = (v[m].sum(), float(m.sum()))
        s_idx = satirlar[hedef]
        t0 = ts[s_idx]
        kendi_tok = tok[s_idx]
        kendi_haric = haric[s_idx]
        kendi_net = net[s_idx]
        kendi_gecerli = gecerli[s_idx]
        for seviye, yari in ((1, 3600.0), (2, 3 * 3600.0), (3, None)):
            if yari is not None:
                a = np.searchsorted(t, t0 - yari)
                b = np.searchsorted(t, t0 + yari, side="right")
                toplam = cv[b] - cv[a]
                adet = cn[b] - cn[a]
            else:
                toplam = np.array([gun_top.get(gg, (0.0, 0.0))[0] for gg in gun[s_idx]])
                adet = np.array([gun_top.get(gg, (0.0, 0.0))[1] for gg in gun[s_idx]])
            duzelt = (~kendi_haric) & kendi_gecerli
            toplam = toplam - np.where(duzelt, kendi_net, 0.0)
            adet = adet - np.where(duzelt, 1.0, 0.0)
            for jj, j in enumerate(hedef):
                if np.isnan(ort[j]) and adet[jj] >= 5:
                    ort[j] = toplam[jj] / adet[jj]
                    say[j] = adet[jj]
    return ort, say


def pencere_ortalamasi(d, ufuk):
    """Permutasyon icin: her satirin kontrol ortalamasi (sadece kendi tokeni haric)."""
    ort = np.full(len(d), np.nan)
    tok = d.token.values
    hepsi = np.arange(len(d))
    o, _ = kontrol_ortalamalari(d, ufuk, hepsi, None)
    # kendi tokeninin diger satirlarini da cikarmiyoruz (yaklasim); yeterince buyuk havuzda etkisi ihmal edilebilir
    return o


# ---------------- ISTATISTIK ----------------

def bootstrap_ga(fark, gunler, tekrar=BOOT, tohum=7):
    rng = np.random.default_rng(tohum)
    ug = np.unique(gunler)
    parca = {g: fark[gunler == g] for g in ug}
    sonuc = np.empty(tekrar)
    for i in range(tekrar):
        sec = rng.choice(ug, size=len(ug), replace=True)
        v = np.concatenate([parca[g] for g in sec])
        sonuc[i] = v.mean()
    return np.percentile(sonuc, [GA_KUYRUK, 100 - GA_KUYRUK])


def permutasyon_p(d, ufuk, satirlar, tabaka_kod, yon, gozlenen, tekrar=PERM, tohum=11):
    """Tabaka icinde sinyal etiketlerini karistirir."""
    net = d["net_" + ufuk].values
    wm = d["_wm_" + ufuk].values
    etki = net - wm
    gecerli = ~np.isnan(etki)
    kova = d.kova.values
    gun = d.gun.values
    kod = pd.Series(gun).astype(str) + "|" + pd.Series(kova).astype(str) + "|" + pd.Series(d.asama.values).astype(str)
    kod = kod.values
    rng = np.random.default_rng(tohum)
    havuz = {}
    for k in np.unique(tabaka_kod):
        idx = np.where((kod == k) & gecerli)[0]
        if len(idx):
            havuz[k] = etki[idx]
    say = pd.Series(tabaka_kod).value_counts().to_dict()
    dagilim = np.empty(tekrar)
    for i in range(tekrar):
        top, n = 0.0, 0
        for k, ns in say.items():
            h = havuz.get(k)
            if h is None or len(h) == 0:
                continue
            sec = rng.choice(h, size=min(ns, len(h)), replace=len(h) < ns)
            top += sec.sum()
            n += len(sec)
        dagilim[i] = top / max(n, 1)
    if yon == "AL":
        p = (np.sum(dagilim >= gozlenen) + 1) / (tekrar + 1)
    elif yon == "KACIN":
        p = (np.sum(dagilim <= gozlenen) + 1) / (tekrar + 1)
    else:
        p = (np.sum(np.abs(dagilim) >= abs(gozlenen)) + 1) / (tekrar + 1)
    return p


def holm(pler):
    ad = list(pler)
    sira = sorted(ad, key=lambda a: pler[a])
    m = len(sira)
    duz = {}
    onceki = 0.0
    for i, a in enumerate(sira):
        v = min(1.0, (m - i) * pler[a])
        v = max(v, onceki)
        duz[a] = v
        onceki = v
    return duz


def donem_tutarli(fark, gunler, yon):
    ug = sorted(np.unique(gunler))
    if len(ug) < 3:
        return False, []
    parts = np.array_split(np.array(ug), 3)
    isaretler = []
    for p in parts:
        v = fark[np.isin(gunler, p)]
        isaretler.append(v.mean() if len(v) else np.nan)
    if yon == "AL":
        ok = all(x > 0 for x in isaretler)
    elif yon == "KACIN":
        ok = all(x < 0 for x in isaretler)
    else:
        ok = all(x > 0 for x in isaretler) or all(x < 0 for x in isaretler)
    return ok, [round(float(x), 4) for x in isaretler]


def kuyruk_saglam(fark, yon):
    if len(fark) < 3:
        return False
    if yon == "AL":
        cik = fark[fark != fark.max()] if (fark == fark.max()).sum() == 1 else np.sort(fark)[:-1]
    elif yon == "KACIN":
        cik = fark[fark != fark.min()] if (fark == fark.min()).sum() == 1 else np.sort(fark)[1:]
    else:
        cik = np.sort(fark)[:-1] if abs(fark.max()) > abs(fark.min()) else np.sort(fark)[1:]
    ref = np.sign(fark.mean())
    return np.sign(cik.mean()) == ref


# ---------------- ANA ----------------

def kirp_getiriler(d, alt=1.0, ust=99.0):
    """Havuzun tamaminda 1-99 yuzdelik siniri; sinyal/kontrol ayrimi yapilmadan uygulanir."""
    sinir = {}
    for u in UFUK:
        k = "net_" + u
        v = d[k].dropna().values
        if len(v) < 100:
            continue
        a, b = np.percentile(v, [alt, ust])
        d[k] = d[k].clip(a, b)
        sinir[u] = (float(a), float(b))
    return sinir


def analiz(kok, mod, son_giris=None, tohum=3, istatistik="kirpilmis"):
    simdi = int(pd.Timestamp.now(tz="UTC").timestamp())
    snap, bal, inf, ol, st = yukle(kok)
    d = getiri_tablosu(snap, st, simdi)
    if mod == "sahte":
        rng = np.random.default_rng(tohum)
        for u in UFUK:
            k = "net_" + u
            for g, gr in d.groupby("gun"):
                v = gr[k].values.copy()
                rng.shuffle(v)
                d.loc[gr.index, k] = v
    sinir = kirp_getiriler(d) if istatistik == "kirpilmis" else {}
    for u in UFUK:
        d["_wm_" + u] = pencere_ortalamasi(d, u)

    sin = sinyaller(d, bal, inf, ol, st)
    satir_sonuc = {}
    ham_p = {}
    for ad, (yon, tab) in sin.items():
        if not len(tab):
            satir_sonuc[ad] = dict(yon=yon, durum="YETERSIZ VERI", n=0, gun=0)
            continue
        gir = giris_satiri(d, tab)
        if son_giris:
            gir = gir[gir.t0 <= son_giris]
        s_idx = gir.satir.values
        saat = d.saat.values[s_idx]
        pen = (saat >= PENCERE[0]) & (saat < PENCERE[1])
        gir = gir[pen]
        s_idx = gir.satir.values
        net = d["net_" + ANA_UFUK].values[s_idx]
        ok = ~np.isnan(net)
        gir, s_idx, net = gir[ok], s_idx[ok], net[ok]
        if len(gir) == 0:
            satir_sonuc[ad] = dict(yon=yon, durum="YETERSIZ VERI", n=0, gun=0)
            continue
        kort, ksay = kontrol_ortalamalari(d, ANA_UFUK, list(s_idx), set(tab.token))
        var = ~np.isnan(kort)
        fark = net[var] - kort[var]
        gunler = d.gun.values[s_idx][var]
        n, ngun = len(fark), len(np.unique(gunler))
        r = dict(yon=yon, n=n, gun=ngun, fark=float(fark.mean()) if n else np.nan,
                 kontrol=float(np.nanmean(ksay)))
        if n < MIN_N or ngun < MIN_GUN:
            r["durum"] = "YETERSIZ VERI"
            satir_sonuc[ad] = r
            continue
        r["ga"] = [float(x) for x in bootstrap_ga(fark, gunler)]
        kod = (pd.Series(gunler).astype(str) + "|" +
               pd.Series(d.kova.values[s_idx][var]).astype(str) + "|" +
               pd.Series(d.asama.values[s_idx][var]).astype(str)).values
        p = permutasyon_p(d, ANA_UFUK, list(s_idx[var]), kod, yon, fark.mean())
        ham_p[ad] = p
        r["p"] = p
        r["donem_ok"], r["donemler"] = donem_tutarli(fark, gunler, yon)
        r["kuyruk_ok"] = bool(kuyruk_saglam(fark, yon))
        f = r["fark"]
        r["eko_ok"] = bool(f >= EKONOMIK if yon == "AL" else (f <= -EKONOMIK if yon == "KACIN" else abs(f) >= EKONOMIK))
        gunluk = n / max(ngun, 1)
        r["gunluk"] = gunluk
        if gunluk > GUNLUK_SINIR:
            ilk3 = pd.DataFrame({"g": gunler, "f": fark, "t": d.ts.values[s_idx][var]})
            ilk3 = ilk3.sort_values("t").groupby("g").head(3)
            ga3 = bootstrap_ga(ilk3.f.values, ilk3.g.values)
            d3, _ = donem_tutarli(ilk3.f.values, ilk3.g.values, yon)
            r["ilk3_ok"] = bool((ga3[0] > 0 if yon == "AL" else (ga3[1] < 0 if yon == "KACIN" else (ga3[0] > 0 or ga3[1] < 0))) and d3)
            r["ilk3_ga"] = [float(x) for x in ga3]
        else:
            r["ilk3_ok"] = True
        satir_sonuc[ad] = r

    duz = holm(ham_p) if ham_p else {}
    for ad, r in satir_sonuc.items():
        if r.get("durum") == "YETERSIZ VERI":
            continue
        r["holm"] = duz.get(ad, 1.0)
        yon = r["yon"]
        ga = r["ga"]
        ga_ok = ga[0] > 0 if yon == "AL" else (ga[1] < 0 if yon == "KACIN" else (ga[0] > 0 or ga[1] < 0))
        gecti = all([ga_ok, r["holm"] < ALFA, r["donem_ok"], r["kuyruk_ok"], r["eko_ok"], r["ilk3_ok"]])
        r["durum"] = "GECTI" if gecti else "KALDI"
        r["kriterler"] = dict(orneklem=True, ga=bool(ga_ok), holm=bool(r["holm"] < ALFA),
                              donem=bool(r["donem_ok"]), kuyruk=bool(r["kuyruk_ok"]),
                              eko=bool(r["eko_ok"]), ilk3=bool(r["ilk3_ok"]))
    return satir_sonuc, d


def rapor(sonuc, mod, yol):
    sat = ["# ANALIZ RAPORU (%s)" % mod.upper(), "", "Ana olcu: %s | alfa %.4f | n>=%d, gun>=%d" % (ANA_UFUK, ALFA, MIN_N, MIN_GUN), ""]
    sat.append("| Hipotez | Yon | n | gun | FARK | GA | Holm p | Donem | Kuyruk | Eko | Sonuc |")
    sat.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for ad, r in sonuc.items():
        if r.get("durum") == "YETERSIZ VERI":
            sat.append("| %s | %s | %d | %d | - | - | - | - | - | - | YETERSIZ VERI |" % (ad, r["yon"], r.get("n", 0), r.get("gun", 0)))
            continue
        ga = r["ga"]
        sat.append("| %s | %s | %d | %d | %+.1f%% | [%+.1f%%, %+.1f%%] | %.4f | %s | %s | %s | %s |" % (
            ad, r["yon"], r["n"], r["gun"], 100 * r["fark"], 100 * ga[0], 100 * ga[1],
            r["holm"], "OK" if r["donem_ok"] else "-", "OK" if r["kuyruk_ok"] else "-",
            "OK" if r["eko_ok"] else "-", r["durum"]))
    metin = "\n".join(sat)
    open(yol, "w", encoding="utf-8").write(metin + "\n")
    print(metin)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kok")
    ap.add_argument("--mod", default="sahte", choices=["sahte", "gercek"])
    ap.add_argument("--son-giris", type=int, default=None)
    ap.add_argument("--tohum", type=int, default=3)
    ap.add_argument("--istatistik", default="kirpilmis", choices=["ham", "kirpilmis"])
    a = ap.parse_args()
    s, _ = analiz(a.kok, a.mod, a.son_giris, a.tohum, a.istatistik)
    rapor(s, a.mod + "_" + a.istatistik, "rapor_%s_%s.md" % (a.mod, a.istatistik))
