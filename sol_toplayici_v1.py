# SOL TOPLAYICI V1
# Solana yeni token ileri veri toplayici (GitHub Actions icin)
# Kaynak: Dexscreener (profil/boost/CTO + pair verisi), GeckoTerminal (rastgele yeni havuz ornegi)
# Sadece standart kutuphane. Ham metrik kaydeder, skor hesaplamaz.

import os
import csv
import json
import time
import random
import urllib.request
import urllib.error
from datetime import datetime, timezone

DS = "https://api.dexscreener.com"
GT = "https://api.geckoterminal.com/api/v2"

MIN_LIQ = 1000.0       # takibe alma: min likidite USD
MIN_MCAP = 5000.0      # likidite bilgisi yoksa min mcap USD
MAX_YAS_SAAT = 72      # pair bundan eskiyse takibe alma
GECKO_SAYFA = 3        # new_pools sayfa sayisi
GECKO_MIN_LIQ = 5000.0
GECKO_MAX = 8          # kosu basina rastgele secilen gecko token
TAKIP_GUN = 8          # ilk gorulmeden sonra takip suresi
OLU_LIQ = 500.0        # 2 ardisik olcumde altindaysa olu

STATE = "state/tokens.csv"
KOSU_LOG = "data/kosu_log.csv"
SNAP_DIR = "data/snap"

QUOTE = set([
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
])

SK = ["token", "kaynak", "ilk", "son_snap", "olu_say", "yok_say", "durum"]
KOLON = [
    "ts", "token", "sembol", "kaynak", "ilk", "pair_yas_saat", "pair", "dex",
    "pair_olusma", "fiyat", "liq", "fdv", "mcap",
    "vol_m5", "vol_h1", "vol_h6", "vol_h24",
    "al_m5", "sat_m5", "al_h1", "sat_h1", "al_h6", "sat_h6", "al_h24", "sat_h24",
    "deg_m5", "deg_h1", "deg_h6", "deg_h24",
    "boost", "n_web", "n_sosyal", "n_pair", "etiket",
]

HATA = []


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def get_json(url, tekrar=3):
    for i in range(tekrar):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (sol-toplayici-v1)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(6 * (i + 1))
                continue
            HATA.append("HTTP %d %s" % (e.code, url[:90]))
            return None
        except Exception:
            time.sleep(3)
    HATA.append("basarisiz %s" % url[:90])
    return None


def ds_liste(yol, etiket, aday):
    d = get_json(DS + yol)
    if d is None:
        return -1
    if isinstance(d, dict):
        d = [d]
    n = 0
    for it in d:
        if not isinstance(it, dict):
            continue
        if it.get("chainId") == "solana" and it.get("tokenAddress"):
            aday.setdefault(it["tokenAddress"], set()).add(etiket)
            n += 1
    return n


def gecko_token(pool, rol):
    rel = (pool.get("relationships") or {}).get(rol) or {}
    tid = (rel.get("data") or {}).get("id") or ""
    return tid.split("_", 1)[1] if "_" in tid else ""


def gecko(aday):
    bulunan = set()
    ok = 0
    for p in range(1, GECKO_SAYFA + 1):
        if p > 1:
            time.sleep(7)
        d = get_json(GT + "/networks/solana/new_pools?page=%d" % p)
        if not isinstance(d, dict):
            continue
        ok += 1
        for pool in d.get("data") or []:
            a = pool.get("attributes") or {}
            liq = fnum(a.get("reserve_in_usd")) or 0.0
            tok = gecko_token(pool, "base_token")
            if tok in QUOTE:
                tok = gecko_token(pool, "quote_token")
            if tok and tok not in QUOTE and liq >= GECKO_MIN_LIQ:
                bulunan.add(tok)
    secim = list(bulunan)
    random.shuffle(secim)
    for t in secim[:GECKO_MAX]:
        aday.setdefault(t, set()).add("gecko")
    return len(bulunan) if ok else -1


def ds_pairler(tokenler):
    veri = {}
    sorgulanan = set()
    tl = sorted(tokenler)
    for i in range(0, len(tl), 30):
        parca = tl[i:i + 30]
        d = get_json(DS + "/tokens/v1/solana/" + ",".join(parca))
        time.sleep(0.3)
        if not isinstance(d, list):
            continue
        ps = set(parca)
        sorgulanan |= ps
        for p in d:
            if not isinstance(p, dict):
                continue
            b = (p.get("baseToken") or {}).get("address")
            if b not in ps:
                continue
            liq = fnum((p.get("liquidity") or {}).get("usd")) or 0.0
            s = veri.setdefault(b, {"best": None, "liq": -1.0, "n": 0})
            s["n"] += 1
            if liq > s["liq"]:
                s["best"] = p
                s["liq"] = liq
    return veri, sorgulanan


def temiz(x):
    return str(x if x is not None else "").replace("\n", " ").replace("\r", " ")[:40]


def satir(now, tok, x, s):
    p = s["best"]
    tx = p.get("txns") or {}
    vo = p.get("volume") or {}
    pc = p.get("priceChange") or {}
    info = p.get("info") or {}
    pca = p.get("pairCreatedAt") or 0
    yas = round((now * 1000 - pca) / 3600000.0, 2) if pca else ""

    def t(k, y):
        return (tx.get(k) or {}).get(y, "")

    return [
        now, tok, temiz((p.get("baseToken") or {}).get("symbol")), x["kaynak"], x["ilk"], yas,
        p.get("pairAddress", ""), p.get("dexId", ""), int(pca / 1000) if pca else "",
        p.get("priceUsd", ""), (p.get("liquidity") or {}).get("usd", ""),
        p.get("fdv", ""), p.get("marketCap", ""),
        vo.get("m5", ""), vo.get("h1", ""), vo.get("h6", ""), vo.get("h24", ""),
        t("m5", "buys"), t("m5", "sells"), t("h1", "buys"), t("h1", "sells"),
        t("h6", "buys"), t("h6", "sells"), t("h24", "buys"), t("h24", "sells"),
        pc.get("m5", ""), pc.get("h1", ""), pc.get("h6", ""), pc.get("h24", ""),
        (p.get("boosts") or {}).get("active", 0),
        len(info.get("websites") or []), len(info.get("socials") or []),
        s["n"], "|".join(p.get("labels") or []),
    ]


def zamani_geldi(now, x):
    yas = now - int(x["ilk"])
    son = int(x["son_snap"] or 0)
    if yas < 6 * 3600:
        ara = 0
    elif yas < 24 * 3600:
        ara = 2 * 3600 - 300
    else:
        ara = 6 * 3600 - 300
    return now - son >= ara


def state_oku():
    st = {}
    if os.path.exists(STATE):
        with open(STATE, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                st[r["token"]] = r
    return st


def state_yaz(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SK)
        w.writeheader()
        for t in sorted(st, key=lambda k: int(st[k]["ilk"])):
            w.writerow({k: st[t].get(k, "") for k in SK})
    os.replace(tmp, STATE)


def main():
    bas = time.time()
    now = int(bas)
    st = state_oku()
    aday = {}

    n_prof = ds_liste("/token-profiles/latest/v1", "profil", aday)
    n_boost = ds_liste("/token-boosts/latest/v1", "boost", aday)
    n_top = ds_liste("/token-boosts/top/v1", "topboost", aday)
    n_cto = ds_liste("/community-takeovers/latest/v1", "cto", aday)
    n_gecko = gecko(aday)

    for t, ks in aday.items():
        if t in st:
            eski = set(st[t]["kaynak"].split("+"))
            st[t]["kaynak"] = "+".join(sorted(eski | ks))

    for t, x in st.items():
        if x["durum"] == "aktif" and now - int(x["ilk"]) > TAKIP_GUN * 86400:
            x["durum"] = "bitti"

    takip = [t for t, x in st.items() if x["durum"] == "aktif" and zamani_geldi(now, x)]
    yeni_aday = [t for t in aday if t not in st]
    veri, sorgulanan = ds_pairler(set(takip) | set(yeni_aday))

    n_yeni = 0
    for t in yeni_aday:
        s = veri.get(t)
        if not s:
            continue
        p = s["best"]
        pca = p.get("pairCreatedAt") or 0
        if not pca or now * 1000 - pca > MAX_YAS_SAAT * 3600000:
            continue
        liq = fnum((p.get("liquidity") or {}).get("usd"))
        mcap = fnum(p.get("marketCap")) or fnum(p.get("fdv")) or 0.0
        if liq is not None and liq < MIN_LIQ:
            continue
        if liq is None and mcap < MIN_MCAP:
            continue
        st[t] = {"token": t, "kaynak": "+".join(sorted(aday[t])), "ilk": str(now),
                 "son_snap": "0", "olu_say": "0", "yok_say": "0", "durum": "aktif"}
        takip.append(t)
        n_yeni += 1

    rows = []
    n_olu = 0
    for t in takip:
        x = st[t]
        s = veri.get(t)
        if not s:
            if t in sorgulanan:
                x["yok_say"] = str(int(x["yok_say"]) + 1)
                if int(x["yok_say"]) >= 3:
                    x["durum"] = "yok"
            continue
        x["yok_say"] = "0"
        rows.append(satir(now, t, x, s))
        x["son_snap"] = str(now)
        liq = fnum((s["best"].get("liquidity") or {}).get("usd"))
        if liq is not None and liq < OLU_LIQ:
            x["olu_say"] = str(int(x["olu_say"]) + 1)
        else:
            x["olu_say"] = "0"
        if int(x["olu_say"]) >= 2:
            x["durum"] = "olu"
            n_olu += 1

    zaman = datetime.fromtimestamp(now, timezone.utc)
    if rows:
        klas = os.path.join(SNAP_DIR, zaman.strftime("%Y-%m-%d"))
        os.makedirs(klas, exist_ok=True)
        yol = os.path.join(klas, zaman.strftime("%H%M") + ".csv")
        with open(yol, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(KOLON)
            w.writerows(rows)
    state_yaz(st)

    aktif = sum(1 for x in st.values() if x["durum"] == "aktif")
    sure = round(time.time() - bas, 1)
    os.makedirs(os.path.dirname(KOSU_LOG), exist_ok=True)
    yeni_dosya = not os.path.exists(KOSU_LOG)
    with open(KOSU_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni_dosya:
            w.writerow(["ts", "utc", "profil", "boost", "topboost", "cto", "gecko",
                        "yeni", "aktif", "satir", "olu", "hata", "sure_sn"])
        w.writerow([now, zaman.strftime("%Y-%m-%d %H:%M"), n_prof, n_boost, n_top, n_cto,
                    n_gecko, n_yeni, aktif, len(rows), n_olu, len(HATA), sure])

    print("=" * 44)
    print("SOL TOPLAYICI V1 | " + zaman.strftime("%Y-%m-%d %H:%M UTC"))
    print("Kaynak: profil=%d boost=%d topboost=%d cto=%d gecko=%d"
          % (n_prof, n_boost, n_top, n_cto, n_gecko))
    print("Yeni takibe alinan: %d | Aktif takip: %d" % (n_yeni, aktif))
    print("Bu kosu satir: %d | Olu isaretlenen: %d | Sure: %ss" % (len(rows), n_olu, sure))
    print("Hata sayisi: %d" % len(HATA))
    for h in HATA[:10]:
        print("  - " + h)
    print("=" * 44)


if __name__ == "__main__":
    main()
