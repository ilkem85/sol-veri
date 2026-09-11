# PROBE V1
# Hangi API uclari GitHub sunucusundan calisiyor ve hangi alanlar geliyor?
# Sonuclar probe/ klasorune yazilir (ozet + ornek JSON).

import os
import json
import time
import urllib.request
import urllib.error

DS = "https://api.dexscreener.com"
GT = "https://api.geckoterminal.com/api/v2"
OUT = "probe"
SATIR = []


def get(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (sol-probe-v1)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return "ERR:" + str(e)[:40], None


def ozet(ad, url, gecko=False):
    kod, d = get(url)
    n = ""
    ornek = None
    if isinstance(d, list):
        n = len(d)
        ornek = d[0] if d else None
    elif isinstance(d, dict):
        if isinstance(d.get("data"), list):
            n = len(d["data"])
            ornek = d["data"][0] if d["data"] else None
        elif isinstance(d.get("pairs"), list):
            n = len(d["pairs"])
            ornek = d["pairs"][0] if d["pairs"] else None
        else:
            n = "dict"
            ornek = d
    anahtar = ""
    if isinstance(ornek, dict):
        anahtar = ",".join(sorted(ornek.keys()))[:160]
    SATIR.append("%-20s kod=%s n=%s | %s" % (ad, kod, n, anahtar))
    if d is not None:
        metin = json.dumps(d, indent=1, ensure_ascii=False)
        if len(metin) > 150000:
            if isinstance(d, list):
                metin = json.dumps(d[:5], indent=1, ensure_ascii=False)
            elif isinstance(d, dict) and isinstance(d.get("data"), list):
                kisa = dict(d)
                kisa["data"] = d["data"][:5]
                metin = json.dumps(kisa, indent=1, ensure_ascii=False)[:150000]
            else:
                metin = metin[:150000]
        with open(os.path.join(OUT, ad + ".json"), "w", encoding="utf-8") as f:
            f.write(metin)
    time.sleep(7 if gecko else 1.2)
    return d


def main():
    os.makedirs(OUT, exist_ok=True)

    prof = ozet("ds_profil_latest", DS + "/token-profiles/latest/v1")
    ozet("ds_profil_recent", DS + "/token-profiles/recent-updates/v1")
    ozet("ds_boost_latest", DS + "/token-boosts/latest/v1")
    ozet("ds_boost_top", DS + "/token-boosts/top/v1")
    ozet("ds_cto_latest", DS + "/community-takeovers/latest/v1")
    ozet("ds_ads_latest", DS + "/ads/latest/v1")
    ozet("ds_metas_trending", DS + "/metas/trending/v1")
    ozet("ds_meta_cat", DS + "/metas/meta/v1/cat")
    ozet("ds_search", DS + "/latest/dex/search?q=cat")

    tok = ""
    for it in prof or []:
        if isinstance(it, dict) and it.get("chainId") == "solana":
            tok = it.get("tokenAddress", "")
            break
    if tok:
        ozet("ds_orders", DS + "/orders/v1/solana/" + tok)

    tr = ozet("gt_trending_6h", GT + "/networks/solana/trending_pools?duration=6h", True)
    ozet("gt_trending_5m", GT + "/networks/solana/trending_pools?duration=5m", True)

    pool = ""
    ptok = ""
    if isinstance(tr, dict) and tr.get("data"):
        p0 = tr["data"][0]
        pool = (p0.get("attributes") or {}).get("address", "")
        rel = ((p0.get("relationships") or {}).get("base_token") or {}).get("data") or {}
        tid = rel.get("id") or ""
        ptok = tid.split("_", 1)[1] if "_" in tid else ""
    if pool:
        ozet("gt_pool_detay", GT + "/networks/solana/pools/" + pool, True)
        ozet("gt_trades_1000", GT + "/networks/solana/pools/" + pool
             + "/trades?trade_volume_in_usd_greater_than=1000", True)
    if ptok:
        ozet("gt_token_info", GT + "/networks/solana/tokens/" + ptok + "/info", True)
        ozet("gt_token", GT + "/networks/solana/tokens/" + ptok, True)

    baslik = "PROBE V1 | " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    with open(os.path.join(OUT, "sonuc.txt"), "w", encoding="utf-8") as f:
        f.write(baslik + "\n" + "\n".join(SATIR) + "\n")
    print("=" * 44)
    print(baslik)
    for s in SATIR:
        print(s)
    print("=" * 44)


if __name__ == "__main__":
    main()
