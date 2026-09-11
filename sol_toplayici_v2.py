# SOL TOPLAYICI V2
# Solana yeni token ileri veri toplayici (GitHub Actions)
# Evren: pair yasi <= 7 gun, likidite >= 10K USD (likidite bilgisi yoksa mcap >= 20K)
# Kayit: snapshot, gorunurluk olaylari, holder/guvenlik, buyuk islemler, cuzdanlar, meta anlatilar
# Sadece standart kutuphane. Skor hesaplamaz, ham veri tutar.

import os
import csv
import json
import time
import random
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

DS = "https://api.dexscreener.com"
GT = "https://api.geckoterminal.com/api/v2"

YAS_MAX_SAAT = 7 * 24
MIN_LIQ = 10000.0
MIN_MCAP_BC = 20000.0
TAKIP_GUN = 10
OLU_LIQ = 1000.0
OLU_MCAP_BC = 5000.0

GT_BUTCE = 45          # kosu basina max GeckoTerminal cagrisi
GT_ARA = 6.5           # cagrilar arasi saniye (anahtarsiz limit ~10/dk)
GT_YENI_SAYFA = 2
GT_YENI_MAX = 10       # new_pools'tan rastgele eklenecek aday
GT_MULTI_MAX = 6       # pools/multi cagri siniri (30 havuz/cagri)
BALINA_USD = 1000      # islem ozeti esigi
CUZDAN_USD = 2500      # ham cuzdan kaydi esigi
MAX_SURE = 13 * 60     # bu sureden sonra yeni GeckoTerminal isi baslatma
DS_ARA_YAVAS = 1.1     # dakikada 60 limitli uclar icin
ORDER_MAX = 30

KOK = "data2"
STATE = "state2/tokens.csv"
RED = "state2/red.csv"

QUOTE = set([
    "So11111111111111111111111111111111111111112",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
])
TREND_SURE = ["5m", "1h", "6h", "24h"]

SK = ["token", "ilk_kaynak", "kaynak", "ilk", "pair", "son_snap", "son_info",
      "son_trade", "olu_say", "yok_say", "durum"]
KOLON_SNAP = [
    "ts", "token", "sembol", "pair", "dex", "pair_olusma", "fiyat", "liq", "fdv", "mcap",
    "vol_m5", "vol_h1", "vol_h6", "vol_h24",
    "al_m5", "sat_m5", "al_h1", "sat_h1", "al_h6", "sat_h6", "al_h24", "sat_h24",
    "deg_m5", "deg_h1", "deg_h6", "deg_h24",
    "boost", "n_web", "n_sosyal", "n_pair", "etiket",
    "gt_ts", "alici_m5", "satici_m5", "alici_h1", "satici_h1",
    "alici_h6", "satici_h6", "alici_h24", "satici_h24", "kilitli_liq",
]
KOLON_OLAY = ["ts", "token", "tur", "d1", "d2"]
KOLON_INFO = [
    "ts", "token", "holder", "top10", "h11_20", "h21_40", "kalan", "holder_guncel",
    "dev_yuzde", "dev_adres", "mint_yetki", "freeze_yetki", "honeypot",
    "gt_skor", "s_pool", "s_islem", "s_olusum", "s_bilgi", "s_holder",
    "gt_dogrulu", "kategori", "twitter", "telegram", "n_web",
]
KOLON_BALINA = ["ts", "token", "pair", "esik", "n_islem", "n_al", "n_sat", "usd_al", "usd_sat",
                "tekil_alici", "tekil_satici", "max_al", "ilk_islem", "son_islem"]
KOLON_CUZDAN = ["ts", "token", "islem_ts", "tur", "cuzdan", "usd", "tx"]
KOLON_META = ["ts", "slug", "ad", "token_sayi", "mcap", "liq", "hacim",
              "mcap_deg_m5", "mcap_deg_h1", "mcap_deg_h6", "mcap_deg_h24"]
KOLON_KOSU = ["ts", "utc", "ds_cagri", "gt_cagri", "gt_429", "aday", "yeni", "aktif",
              "snap", "info", "islem", "olu", "hata", "sure_sn"]

BAS = time.time()
HATA = []
OLAY = []
CUZDAN = []
SAYAC = {"ds": 0, "gt": 0, "gt429": 0}
GT_SON = [0.0]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def temiz(x, n=40):
    if isinstance(x, (dict, list)):
        x = json.dumps(x, separators=(",", ":"))
    return str(x if x is not None else "").replace("\n", " ").replace("\r", " ")[:n]


def sure_doldu():
    return time.time() - BAS > MAX_SURE


def istek(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (sol-toplayici-v2)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return -1, None


def ds_get(yol, ara=0.3):
    kod = 0
    for i in range(3):
        SAYAC["ds"] += 1
        kod, d = istek(DS + yol)
        time.sleep(ara)
        if kod == 200:
            return d
        if kod == 429 or kod >= 500 or kod == -1:
            time.sleep(5 * (i + 1))
            continue
        break
    if kod != 404:
        HATA.append("DS %s %s" % (kod, yol[:60]))
    return None


def gt_get(yol):
    if SAYAC["gt"] >= GT_BUTCE:
        return 0, None
    bekle = GT_ARA - (time.time() - GT_SON[0])
    if bekle > 0:
        time.sleep(bekle)
    SAYAC["gt"] += 1
    kod, d = istek(GT + yol)
    GT_SON[0] = time.time()
    if kod == 200:
        return kod, d
    if kod == 429:
        SAYAC["gt429"] += 1
        if SAYAC["gt429"] >= 3:
            SAYAC["gt"] = GT_BUTCE
        time.sleep(25)
    elif kod != 404:
        HATA.append("GT %s %s" % (kod, yol[:60]))
    return kod, None


def csv_yaz(yol, baslik, satirlar):
    if not satirlar:
        return
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(baslik)
        w.writerows(satirlar)


def csv_ekle(yol, baslik, satirlar):
    if not satirlar:
        return
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    yeni = not os.path.exists(yol)
    with open(yol, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(baslik)
        w.writerows(satirlar)


def csv_oku(yol, anahtar):
    d = {}
    if os.path.exists(yol):
        with open(yol, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d[r[anahtar]] = r
    return d


def state_yaz(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SK)
        w.writeheader()
        for t in sorted(st, key=lambda k: int(st[k]["ilk"])):
            w.writerow({k: st[t].get(k, "") for k in SK})
    os.replace(tmp, STATE)


def red_yaz(red, now):
    os.makedirs(os.path.dirname(RED), exist_ok=True)
    with open(RED, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["token", "sebep", "ts"])
        for t, r in red.items():
            if now - int(r["ts"]) < 8 * 86400:
                w.writerow([t, r["sebep"], r["ts"]])


def red_atla(red, t, now):
    r = red.get(t)
    if not r:
        return False
    if r["sebep"] == "yas":
        return True
    return now - int(r["ts"]) < 3 * 3600


# ---------------- KESIF ----------------

def ds_liste(yol, tur, aday, a1="", a2=""):
    d = ds_get(yol, DS_ARA_YAVAS)
    if d is None:
        return -1
    if isinstance(d, dict):
        d = [d]
    n = 0
    ts = int(time.time())
    for it in d:
        if not isinstance(it, dict) or it.get("chainId") != "solana":
            continue
        t = it.get("tokenAddress")
        if not t:
            continue
        aday.setdefault(t, set()).add(tur)
        OLAY.append([ts, t, tur, temiz(it.get(a1, "")) if a1 else "",
                     temiz(it.get(a2, "")) if a2 else ""])
        n += 1
    return n


def metalar(aday, meta_uye, now):
    d = ds_get("/metas/trending/v1", DS_ARA_YAVAS)
    if not isinstance(d, list):
        return -1
    satir = []
    for m in d:
        if not isinstance(m, dict):
            continue
        mc = m.get("marketCapChange") or {}
        satir.append([now, m.get("slug", ""), temiz(m.get("name")), m.get("tokenCount", ""),
                      temiz(m.get("marketCap")), temiz(m.get("liquidity")), temiz(m.get("volume")),
                      mc.get("m5", ""), mc.get("h1", ""), mc.get("h6", ""), mc.get("h24", "")])
    csv_ekle(os.path.join(KOK, "meta_log.csv"), KOLON_META, satir)
    n = 0
    for m in d:
        slug = m.get("slug") if isinstance(m, dict) else None
        if not slug:
            continue
        md = ds_get("/metas/meta/v1/" + urllib.parse.quote(slug), DS_ARA_YAVAS)
        pairs = md.get("pairs") if isinstance(md, dict) else None
        for p in pairs or []:
            if not isinstance(p, dict) or p.get("chainId") != "solana":
                continue
            t = (p.get("baseToken") or {}).get("address")
            if not t or t in QUOTE:
                continue
            aday.setdefault(t, set()).add("meta")
            meta_uye.setdefault(t, set()).add(slug)
            n += 1
    return n


def gecko_token(pool):
    def al(rol):
        rel = ((pool.get("relationships") or {}).get(rol) or {}).get("data") or {}
        tid = rel.get("id") or ""
        return tid.split("_", 1)[1] if "_" in tid else ""
    t = al("base_token")
    if t in QUOTE:
        t = al("quote_token")
    return "" if t in QUOTE else t


def gecko_kesif(aday):
    bulunan = {}
    for s in range(1, GT_YENI_SAYFA + 1):
        kod, d = gt_get("/networks/solana/new_pools?page=%d" % s)
        for pool in (d or {}).get("data") or []:
            liq = fnum((pool.get("attributes") or {}).get("reserve_in_usd")) or 0.0
            t = gecko_token(pool)
            if t and liq >= MIN_LIQ:
                bulunan[t] = liq
    secim = list(bulunan)
    random.shuffle(secim)
    ts = int(time.time())
    for t in secim[:GT_YENI_MAX]:
        aday.setdefault(t, set()).add("gecko_yeni")
        OLAY.append([ts, t, "gecko_yeni", round(bulunan[t]), ""])
    n_trend = 0
    for sure in TREND_SURE:
        kod, d = gt_get("/networks/solana/trending_pools?duration=" + sure)
        ts = int(time.time())
        for i, pool in enumerate((d or {}).get("data") or []):
            t = gecko_token(pool)
            if not t:
                continue
            aday.setdefault(t, set()).add("trend")
            OLAY.append([ts, t, "trend_" + sure, i + 1,
                         (pool.get("attributes") or {}).get("address", "")])
            n_trend += 1
    return len(bulunan), n_trend


# ---------------- ZENGINLESTIRME ----------------

def ds_pairler(tokenler):
    veri = {}
    sorgulanan = set()
    tl = sorted(tokenler)
    for i in range(0, len(tl), 30):
        parca = tl[i:i + 30]
        d = ds_get("/tokens/v1/solana/" + ",".join(parca), 0.3)
        ts = int(time.time())
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
            s = veri.setdefault(b, {"best": None, "liq": -1.0, "n": 0, "ts": ts})
            s["n"] += 1
            if liq > s["liq"]:
                s["best"] = p
                s["liq"] = liq
    return veri, sorgulanan


def snap_satir(t, s):
    p = s["best"]
    tx = p.get("txns") or {}
    vo = p.get("volume") or {}
    pc = p.get("priceChange") or {}
    info = p.get("info") or {}
    pca = p.get("pairCreatedAt") or 0

    def g(k, y):
        return (tx.get(k) or {}).get(y, "")

    return [
        s["ts"], t, temiz((p.get("baseToken") or {}).get("symbol")),
        p.get("pairAddress", ""), p.get("dexId", ""), int(pca / 1000) if pca else "",
        p.get("priceUsd", ""), (p.get("liquidity") or {}).get("usd", ""),
        p.get("fdv", ""), p.get("marketCap", ""),
        vo.get("m5", ""), vo.get("h1", ""), vo.get("h6", ""), vo.get("h24", ""),
        g("m5", "buys"), g("m5", "sells"), g("h1", "buys"), g("h1", "sells"),
        g("h6", "buys"), g("h6", "sells"), g("h24", "buys"), g("h24", "sells"),
        pc.get("m5", ""), pc.get("h1", ""), pc.get("h6", ""), pc.get("h24", ""),
        (p.get("boosts") or {}).get("active", 0),
        len(info.get("websites") or []), len(info.get("socials") or []),
        s["n"], "|".join(str(x) for x in (p.get("labels") or [])),
    ]


def gt_multi(pairler):
    sonuc = {}
    for k, i in enumerate(range(0, len(pairler), 30)):
        if k >= GT_MULTI_MAX or sure_doldu():
            break
        kod, d = gt_get("/networks/solana/pools/multi/" + ",".join(pairler[i:i + 30]))
        ts = int(time.time())
        for pool in (d or {}).get("data") or []:
            a = pool.get("attributes") or {}
            tx = a.get("transactions") or {}
            r = [ts]
            for per in ["m5", "h1", "h6", "h24"]:
                r.append((tx.get(per) or {}).get("buyers", ""))
                r.append((tx.get(per) or {}).get("sellers", ""))
            r.append(a.get("locked_liquidity_percentage", ""))
            sonuc[a.get("address", "")] = r
    return sonuc


def info_satir(t, d):
    a = (d.get("data") or {}).get("attributes") or {}
    h = a.get("holders") or {}
    dp = h.get("distribution_percentage") or {}
    sd = a.get("gt_score_details") or {}
    return [
        int(time.time()), t, h.get("count", ""), dp.get("top_10", ""), dp.get("11_20", ""),
        dp.get("21_40", ""), dp.get("rest", ""), h.get("last_updated", ""),
        a.get("developer_holding_percentage", ""), a.get("developer_address", ""),
        a.get("mint_authority", ""), a.get("freeze_authority", ""), a.get("is_honeypot", ""),
        a.get("gt_score", ""), sd.get("pool", ""), sd.get("transaction", ""),
        sd.get("creation", ""), sd.get("info", ""), sd.get("holders", ""),
        a.get("gt_verified", ""), "|".join(str(x) for x in (a.get("categories") or [])),
        temiz(a.get("twitter_handle")), temiz(a.get("telegram_handle")),
        len(a.get("websites") or []),
    ]


def balina_satir(t, pair, d):
    ts = int(time.time())
    liste = (d or {}).get("data") or []
    n_al = n_sat = 0
    usd_al = usd_sat = max_al = 0.0
    alici = set()
    satici = set()
    zaman = []
    for tr in liste:
        a = tr.get("attributes") or {}
        usd = fnum(a.get("volume_in_usd")) or 0.0
        w = a.get("tx_from_address") or ""
        bt = a.get("block_timestamp") or ""
        if bt:
            zaman.append(bt)
        if a.get("to_token_address") == t:
            tur = "al"
        elif a.get("from_token_address") == t:
            tur = "sat"
        else:
            tur = "al" if a.get("kind") == "buy" else "sat"
        if tur == "al":
            n_al += 1
            usd_al += usd
            alici.add(w)
            max_al = max(max_al, usd)
        else:
            n_sat += 1
            usd_sat += usd
            satici.add(w)
        if usd >= CUZDAN_USD and w:
            CUZDAN.append([ts, t, bt, tur, w, round(usd, 2), a.get("tx_hash", "")])
    zaman.sort()
    return [ts, t, pair, BALINA_USD, len(liste), n_al, n_sat, round(usd_al, 2), round(usd_sat, 2),
            len(alici), len(satici), round(max_al, 2),
            zaman[0] if zaman else "", zaman[-1] if zaman else ""]


def zamani_geldi(now, x):
    yas = now - int(x["ilk"])
    son = int(x["son_snap"] or 0)
    if yas < 6 * 3600:
        ara = 0
    elif yas < 48 * 3600:
        ara = 2 * 3600 - 600
    else:
        ara = 6 * 3600 - 600
    return now - son >= ara


# ---------------- ANA AKIS ----------------

def main():
    now = int(BAS)
    zaman = datetime.fromtimestamp(now, timezone.utc)
    gun = zaman.strftime("%Y-%m-%d")
    dosya = zaman.strftime("%H%M") + ".csv"
    st = csv_oku(STATE, "token")
    red = csv_oku(RED, "token")
    aday = {}
    meta_uye = {}

    ds_liste("/token-profiles/latest/v1", "profil", aday)
    ds_liste("/token-profiles/recent-updates/v1", "profil_guncel", aday, "updatedAt")
    ds_liste("/token-boosts/latest/v1", "boost", aday, "amount", "totalAmount")
    ds_liste("/token-boosts/top/v1", "topboost", aday, "totalAmount")
    ds_liste("/community-takeovers/latest/v1", "cto", aday, "claimDate")
    ds_liste("/ads/latest/v1", "reklam", aday, "impressions", "type")
    metalar(aday, meta_uye, now)
    gecko_kesif(aday)

    for t, ks in aday.items():
        if t in st:
            eski = set(st[t]["kaynak"].split("+"))
            st[t]["kaynak"] = "+".join(sorted(eski | ks))

    for x in st.values():
        if x["durum"] == "aktif" and now - int(x["ilk"]) > TAKIP_GUN * 86400:
            x["durum"] = "bitti"

    takip = [t for t, x in st.items() if x["durum"] == "aktif" and zamani_geldi(now, x)]
    yeni_aday = [t for t in aday if t not in st and not red_atla(red, t, now)]
    veri, sorgulanan = ds_pairler(set(takip) | set(yeni_aday))

    yeniler = []
    for t in yeni_aday:
        if t not in sorgulanan:
            continue
        s = veri.get(t)
        if not s:
            red[t] = {"sebep": "yok", "ts": str(now)}
            continue
        p = s["best"]
        pca = p.get("pairCreatedAt") or 0
        if not pca or now * 1000 - pca > YAS_MAX_SAAT * 3600000:
            red[t] = {"sebep": "yas", "ts": str(now)}
            continue
        liq = fnum((p.get("liquidity") or {}).get("usd"))
        mcap = fnum(p.get("marketCap")) or fnum(p.get("fdv")) or 0.0
        if (liq is not None and liq < MIN_LIQ) or (liq is None and mcap < MIN_MCAP_BC):
            red[t] = {"sebep": "liq", "ts": str(now)}
            continue
        ks = "+".join(sorted(aday[t]))
        st[t] = {"token": t, "ilk_kaynak": ks, "kaynak": ks, "ilk": str(now),
                 "pair": p.get("pairAddress", ""), "son_snap": "0", "son_info": "0",
                 "son_trade": "0", "olu_say": "0", "yok_say": "0", "durum": "aktif"}
        red.pop(t, None)
        takip.append(t)
        yeniler.append(t)

    snap = []
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
        p = s["best"]
        x["pair"] = p.get("pairAddress", "") or x["pair"]
        x["son_snap"] = str(now)
        snap.append((t, s))
        liq = fnum((p.get("liquidity") or {}).get("usd"))
        mcap = fnum(p.get("marketCap")) or fnum(p.get("fdv")) or 0.0
        olu = (liq < OLU_LIQ) if liq is not None else (mcap < OLU_MCAP_BC)
        x["olu_say"] = str(int(x["olu_say"]) + 1) if olu else "0"
        if int(x["olu_say"]) >= 2:
            x["durum"] = "olu"
            n_olu += 1

    for t in yeniler[:ORDER_MAX]:
        d = ds_get("/orders/v1/solana/" + t, DS_ARA_YAVAS)
        ts = int(time.time())
        if isinstance(d, dict):
            for o in d.get("orders") or []:
                OLAY.append([ts, t, "siparis_" + temiz(o.get("type")), o.get("paymentTimestamp", ""),
                             temiz(o.get("status"))])
            for b in d.get("boosts") or []:
                OLAY.append([ts, t, "siparis_boost", b.get("paymentTimestamp", ""),
                             temiz(b.get("amount"))])

    sirali = sorted(snap, key=lambda ts_: -int(st[ts_[0]]["ilk"]))
    pairler = [st[t]["pair"] for t, s in sirali if st[t]["pair"]]
    gtm = gt_multi(pairler)
    bos = [""] * 10
    satirlar = []
    for t, s in snap:
        satirlar.append(snap_satir(t, s) + gtm.get((s["best"] or {}).get("pairAddress", ""), bos))

    gorev = []
    for t, x in st.items():
        if x["durum"] != "aktif" or not x["pair"]:
            continue
        yas = now - int(x["ilk"])
        si = int(x["son_info"] or 0)
        so = int(x["son_trade"] or 0)
        yeni_once = -int(x["ilk"])
        if si == 0:
            gorev.append((0, yeni_once, "info", t))
        elif now - si >= 24 * 3600 - 600:
            gorev.append((3, yeni_once, "info", t))
        if so == 0:
            gorev.append((0, yeni_once, "trade", t))
        elif yas < 48 * 3600 and now - so >= 2 * 3600 - 600:
            gorev.append((1, yeni_once, "trade", t))
        elif now - so >= 12 * 3600 - 600:
            gorev.append((2, yeni_once, "trade", t))
    gorev.sort(key=lambda g: (g[0], g[1], g[3], g[2]))

    info = []
    balina = []
    for oncelik, _, tur, t in gorev:
        if SAYAC["gt"] >= GT_BUTCE or sure_doldu():
            break
        x = st[t]
        if tur == "info":
            kod, d = gt_get("/networks/solana/tokens/%s/info" % t)
            if d:
                info.append(info_satir(t, d))
            if kod in (200, 404):
                x["son_info"] = str(now)
        else:
            kod, d = gt_get("/networks/solana/pools/%s/trades?trade_volume_in_usd_greater_than=%d"
                            % (x["pair"], BALINA_USD))
            if d:
                balina.append(balina_satir(t, x["pair"], d))
            if kod in (200, 404):
                x["son_trade"] = str(now)

    ts = int(time.time())
    for t, slugs in meta_uye.items():
        if t in st and st[t]["durum"] == "aktif":
            for slug in sorted(slugs):
                OLAY.append([ts, t, "meta", slug, ""])

    csv_yaz(os.path.join(KOK, "snap", gun, dosya), KOLON_SNAP, satirlar)
    csv_yaz(os.path.join(KOK, "olay", gun, dosya), KOLON_OLAY, OLAY)
    csv_yaz(os.path.join(KOK, "balina", gun, dosya), KOLON_BALINA, balina)
    csv_yaz(os.path.join(KOK, "cuzdan", gun, dosya), KOLON_CUZDAN, CUZDAN)
    csv_ekle(os.path.join(KOK, "info", gun + ".csv"), KOLON_INFO, info)
    state_yaz(st)
    red_yaz(red, now)

    aktif = sum(1 for x in st.values() if x["durum"] == "aktif")
    sure = round(time.time() - BAS, 1)
    csv_ekle(os.path.join(KOK, "kosu_log.csv"), KOLON_KOSU, [[
        now, zaman.strftime("%Y-%m-%d %H:%M"), SAYAC["ds"], SAYAC["gt"], SAYAC["gt429"],
        len(aday), len(yeniler), aktif, len(satirlar), len(info), len(balina), n_olu,
        len(HATA), sure]])

    print("=" * 46)
    print("SOL TOPLAYICI V2 | " + zaman.strftime("%Y-%m-%d %H:%M UTC"))
    print("Cagri: DS=%d GT=%d (429: %d)" % (SAYAC["ds"], SAYAC["gt"], SAYAC["gt429"]))
    print("Aday: %d | Yeni takip: %d | Aktif: %d" % (len(aday), len(yeniler), aktif))
    print("Snap: %d | Info: %d | Balina: %d | Cuzdan: %d | Olu: %d"
          % (len(satirlar), len(info), len(balina), len(CUZDAN), n_olu))
    print("Olay: %d | Sure: %ss | Hata: %d" % (len(OLAY), sure, len(HATA)))
    for h in HATA[:12]:
        print("  - " + h)
    print("=" * 46)


if __name__ == "__main__":
    main()
