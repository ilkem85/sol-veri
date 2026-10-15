# MUM TOPLAYICI V1
# Evrendeki her token icin GeckoTerminal'den gecmise donuk mum (OHLCV) toplar.
#   m1 : 1 dakikalik mumlar, ilk gorulmeden itibaren ~16,7 saat (token ilk+17 saati gectiyse)
#   m15: 15 dakikalik mumlar, ilk gorulmeden itibaren ~10,4 gun (token ilk+10,5 gunu gectiyse)
# Token ayni pencerede birden fazla havuzda goruldiyse her havuz ayri cekilir.
# Eski tokenlar once islenir. Ciktilar gzip CSV. Sadece standart kutuphane.

import os
import csv
import gzip
import glob
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

GT = "https://api.geckoterminal.com/api/v2/networks/solana/pools/"
SNAP_DESEN = "data2/snap/*/*.csv"
TOKENS = "state2/tokens.csv"
HAVUZ = "state3/havuz.csv"
SON_DOSYA = "state3/son_snap_dosyasi.txt"
DURUM = "state3/mum_durum.csv"
KOK = "data3/mum"
LOG = "data3/mum_log.csv"

ARA = [7.0]            # istekler arasi saniye; 429 gelirse artar
ARA_MAX = 15.0
MAX_CAGRI = 100        # kosu basina istek siniri
MAX_SURE = 14 * 60     # bu sureden sonra yeni istek baslatma
MAX_429 = 4
M1_PENCERE = 17 * 3600
M15_PENCERE = int(10.5 * 86400)

BAS = time.time()
SAYAC = {"cagri": 0, "429": 0, "404": 0, "hata": 0, "mum": 0}
SON_ISTEK = [0.0]


def get(url):
    bekle = ARA[0] - (time.time() - SON_ISTEK[0])
    if bekle > 0:
        time.sleep(bekle)
    SAYAC["cagri"] += 1
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (sol-mum-toplayici-v1)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            SON_ISTEK[0] = time.time()
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        SON_ISTEK[0] = time.time()
        if e.code == 429:
            SAYAC["429"] += 1
            ARA[0] = min(ARA[0] * 1.4, ARA_MAX)
            time.sleep(60)
            SON_ISTEK[0] = time.time()
        elif e.code == 404:
            SAYAC["404"] += 1
        else:
            SAYAC["hata"] += 1
        return e.code, None
    except Exception:
        SON_ISTEK[0] = time.time()
        SAYAC["hata"] += 1
        return -1, None


def havuz_guncelle():
    """Yeni snapshot dosyalarindan token -> havuz (ilk gorulme) indeksini gunceller."""
    havuz = {}
    if os.path.exists(HAVUZ):
        with open(HAVUZ, newline="") as f:
            for r in csv.DictReader(f):
                havuz[(r["token"], r["pair"])] = int(r["ilk_ts"])
    son = ""
    if os.path.exists(SON_DOSYA):
        son = open(SON_DOSYA).read().strip()
    dosyalar = sorted(glob.glob(SNAP_DESEN))
    yeni = [p for p in dosyalar if p > son]
    for p in yeni:
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                t, pr = r.get("token"), r.get("pair")
                if not t or not pr:
                    continue
                try:
                    ts = int(float(r["ts"]))
                except (TypeError, ValueError):
                    continue
                k = (t, pr)
                if k not in havuz or ts < havuz[k]:
                    havuz[k] = ts
    if yeni:
        os.makedirs(os.path.dirname(HAVUZ), exist_ok=True)
        tmp = HAVUZ + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["token", "pair", "ilk_ts"])
            for (t, pr), ts in sorted(havuz.items()):
                w.writerow([t, pr, ts])
        os.replace(tmp, HAVUZ)
        with open(SON_DOSYA, "w") as f:
            f.write(yeni[-1])
    return havuz, len(yeni)


def durum_oku():
    d = {}
    if os.path.exists(DURUM):
        with open(DURUM, newline="") as f:
            for r in csv.DictReader(f):
                d[(r["token"], r["pair"], r["tf"])] = r
    return d


def durum_yaz(d):
    os.makedirs(os.path.dirname(DURUM), exist_ok=True)
    tmp = DURUM + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["token", "pair", "tf", "durum", "n_mum", "deneme", "ts"])
        for k in sorted(d):
            r = d[k]
            w.writerow([r["token"], r["pair"], r["tf"], r["durum"], r["n_mum"], r["deneme"], r["ts"]])
    os.replace(tmp, DURUM)


def gorevler(now, havuz, durum):
    ilk = {}
    with open(TOKENS, newline="") as f:
        for r in csv.DictReader(f):
            try:
                ilk[r["token"]] = int(r["ilk"])
            except (TypeError, ValueError):
                pass
    g = []
    for (t, pr), pts in havuz.items():
        i = ilk.get(t)
        if i is None:
            continue
        for tf, pencere, agg, kac in (("1", M1_PENCERE, 1, 60), ("15", M15_PENCERE, 15, 900)):
            if now < i + pencere:
                continue
            if pts > i + pencere:
                continue
            k = (t, pr, tf)
            r = durum.get(k)
            if r and (r["durum"] == "ok" or int(r["deneme"]) >= 3):
                continue
            g.append((i, tf, t, pr, agg, i + 1000 * kac))
    g.sort()
    return g


def main():
    now = int(BAS)
    zaman = datetime.fromtimestamp(now, timezone.utc)
    havuz, n_yeni_dosya = havuz_guncelle()
    durum = durum_oku()
    liste = gorevler(now, havuz, durum)
    satirlar = []
    yapilan = 0
    for i, tf, t, pr, agg, bitis in liste:
        if SAYAC["cagri"] >= MAX_CAGRI or time.time() - BAS > MAX_SURE or SAYAC["429"] >= MAX_429:
            break
        url = "%s%s/ohlcv/minute?aggregate=%d&limit=1000&before_timestamp=%d&currency=usd&token=%s" % (
            GT, pr, agg, bitis, t)
        kod, d = get(url)
        k = (t, pr, tf)
        r = durum.get(k) or {"token": t, "pair": pr, "tf": tf, "durum": "", "n_mum": "0", "deneme": "0", "ts": ""}
        r["deneme"] = str(int(r["deneme"]) + 1)
        r["ts"] = str(int(time.time()))
        if kod == 200 and isinstance(d, dict):
            mumlar = (((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or []
            for m in mumlar:
                try:
                    satirlar.append([t, pr, tf, int(m[0])] + ["%.6g" % float(x) for x in m[1:5]] +
                                    ["%.0f" % float(m[5])])
                except (TypeError, ValueError, IndexError):
                    continue
            r["durum"] = "ok"
            r["n_mum"] = str(len(mumlar))
            SAYAC["mum"] += len(mumlar)
        elif kod == 404:
            r["durum"] = "yok404"
            r["deneme"] = "3"
        else:
            r["durum"] = "hata%s" % kod
        durum[k] = r
        yapilan += 1
    if satirlar:
        klas = os.path.join(KOK, zaman.strftime("%Y-%m-%d"))
        os.makedirs(klas, exist_ok=True)
        yol = os.path.join(klas, zaman.strftime("%H%M") + ".csv.gz")
        with gzip.open(yol, "wt", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["token", "pair", "tf", "ts", "o", "h", "l", "c", "v"])
            w.writerows(satirlar)
    durum_yaz(durum)
    kalan = len(liste) - yapilan
    sure = round(time.time() - BAS, 1)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    yeni = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(["ts", "utc", "yeni_snap_dosya", "gorev", "yapilan", "kalan", "mum",
                        "cagri", "a429", "a404", "hata", "ara_sn", "sure_sn"])
        w.writerow([now, zaman.strftime("%Y-%m-%d %H:%M"), n_yeni_dosya, len(liste), yapilan, kalan,
                    SAYAC["mum"], SAYAC["cagri"], SAYAC["429"], SAYAC["404"], SAYAC["hata"],
                    round(ARA[0], 1), sure])
    print("=" * 46)
    print("MUM TOPLAYICI V1 | " + zaman.strftime("%Y-%m-%d %H:%M UTC"))
    print("Yeni snapshot dosyasi: %d | Havuz kaydi: %d" % (n_yeni_dosya, len(havuz)))
    print("Gorev: %d | Yapilan: %d | Kalan: %d" % (len(liste), yapilan, kalan))
    print("Mum: %d | Istek: %d | 429: %d | 404: %d | Hata: %d | Sure: %ss"
          % (SAYAC["mum"], SAYAC["cagri"], SAYAC["429"], SAYAC["404"], SAYAC["hata"], sure))
    print("=" * 46)


if __name__ == "__main__":
    main()
