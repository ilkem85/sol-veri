# PROBE MUM V1
# GeckoTerminal'den gecmise donuk dakikalik mum (OHLCV) alinabiliyor mu?
# 24 token x 2 cagri: 1 dk mum (ilk ~16 saat) ve 15 dk mum (ilk ~10 gun).
# Sonuc: probe_mum/ozet.csv + birkac ornek ham JSON. Sadece standart kutuphane.

import os
import csv
import json
import time
import urllib.request
import urllib.error

GT = "https://api.geckoterminal.com/api/v2/networks/solana/pools/"
ARA = 7.0
OUT = "probe_mum"
LISTE = "9HB7uiNQeWTGG1tkuGaMQLhdt9Lg6vmJ4vtLJc1Wpump,5giBZ4FZ89ToVRN3LEjcKPHcV1w53zLdiMCmrjNbAFpm,1789593674,pumpswap,h3_eski;2fWzx35rQMAATQGhJzVTvzeXHcenCQLqCog9Jkg5pump,CXKwgui737V9EDZKLtU5AeHQnWX4kNTnn3gGQT9Tf6wK,1789186817,pumpswap,h3_eski;3o9FX3rc2VbcHugk8MjFxLn3fgHMLiFkDA3QWoUSpump,6VcDLAMaKGEQLX7YiR8JnwUnoyU9mMJuMSYZnK9XmVTN,1789237281,pumpswap,h3_eski;FCVohFrokwz6rELLNgnQT426RbRjXQMy4RY6zrUjpump,41RfVWj5SMhaqGzCvzX1ZozizkfAf14rWg3P7PGQPNDz,1791912748,pumpswap,h3_yeni;7b6dX3nE25xrfNViEKZHL9wVJFcBxQYuWPpmzHUxx28H,9CDKMMGWEnr6ZyU725fr4jdyyFojPW8gz1KKNrYLekCg,1791723756,pumpswap,h3_yeni;FAopSovS2WFJK5qEAmcuwAVH98CvmBwT6Lpq4EK2pump,F2P22SfcG4GKJA2uPyQzEF9BpW3rsec5Q2WmVeWUibL7,1791338553,pumpswap,h3_yeni;3kK8krb2NJoeA96pvvNgVWEQzR7uA4e6t1LQ1Ecgpump,7acMNSRnD4tTyG4rfX78Anpi45VQNxssQo71RZUsXeeX,1791916346,pumpfun,bonding;AprxpUvwka3esMgfRzM7JGhgkGf54bUUq2PwJjJMe181,7u517XkcGosQHA8vhLpshKoohSCX8CrZoeyzvEt2MMTG,1791464559,pumpfun,bonding;37upCgGAmtTvcKJzWy3X9FzLGxw5E4Acb18ZMcVcpump,78XXahkKRdY4o84DBXrUZWJ31Sx3jmFucUs8w7zTbo6z,1791225146,pumpfun,bonding;E81zpDGE1e2RhmLqGXfZL5TMje1nm6Sd9r5KGrsepump,42K9J1nD5wTqW42Er2uK6eSacbAxzcFi82RW955fe22R,1790617718,pumpfun,bonding;EH9vKKVJJoxULovwZZ5seSot3ofdpeMTxWjE9tCSpump,63AqaDm31fUWtdGh1kV6V8onaPEYhxV4tJHXEmDRqL73,1790788979,pumpfun,bonding;34rUxFhaPqVM1SMeRm27coJ6ooBsyb1gDmiEFa8qpump,HuYQ85dzumBzinCg81F6mhcGbJGZUhZqxnJePSJUaiUt,1791914557,pumpfun,bonding;7NUt3oa55ruTU8UNLgfRnGCuaFXsMP57Wpy6yBJyBD6L,FDMUA9tvbrwpeFMevSMicSrUNhCLkSipjWEf1nFVgNT4,1791387146,meteoradbc,olu_havuz;3JTkP2YwxWrqNFqeDepvJmF6XbWgsbsm4VDvfMYFbkWd,7k3bujnjACoreMyTCLKLBLHPgb5jYhZ4cqeVDzPziL2f,1789151026,meteoradbc,olu_havuz;FEHDw48u9YgjDY8USRXoj5riaW91BEG6c2qGEWEfY3G3,djFUYzdMtpEXa4pcDpgQ7sevcz6HMAk5LKGNsgpthVM,1790453979,meteoradbc,olu_havuz;GbuCiNuUzsEfqA6PcgBHthtgV1Xz1hiDvKJWbrv8GEaY,6j54htNJVB6wLmftswDoDjPYuoQRM3Ntj9AJZYGd1dhX,1789629788,meteoradbc,olu_havuz;6eSudEdEsmLsCMHbJEJgVWtS6DumbeZqFQsDF8mMujEX,7HKSsLvNbQsixjNCaJFfJDjGhruoAHkaEknPXaayui98,1791401547,pumpswap,olu_havuz;4V8DGnTYjEZXNtZZmpAXM3Z2k3DnqrjayH3D6suqRHuY,4Vic4yvwc5mLoDQqdEwBggXFS7jTWCsDBvUS1A9rzVqA,1789307095,meteoradbc,olu_havuz;39fz7cnk6qmaRdAhvrxUamvpLyJEMSgVkjoppxw2gDfq,7uNFjoEJPRxp2SCahfGjNwEWQYem6Uq4NREWNkhMBQYg,1789285524,orca,en_eski;G73cGUjED9Y8XPnkn75QUqT5Q4of82t3iLnTubELDadU,AXEJ6FQsJss1589iYaR928NjH6t2nnRnpTxrR4ejGGvX,1789132902,meteoradbc,en_eski;84PqNXQ9xeBG73BsF3kxS91g1oBimLogxRGxNQmLpump,BLCwj1TLZkGvzFjw9cbeX8bpsdFWdvbLQ4hVgeHAZUGQ,1789158045,pumpswap,en_eski;WKdLK4jayoT57sy2Bb6z1er1pFtNJ6CXXJFco1bpump,B5hMoRr7cwhHVdYKm6u9VhEmvStkQxBk4NBhoWJiNCqC,1791945146,pumpswap,en_yeni;9UpqySqQcqxkc3Ru1jHgxaZ2BhUch3Py7LxpnVGWpump,4aF5QfxuHumWs4BuMvijrd94vBHa3EcVM3wXtj96Cx8f,1791905553,pumpswap,en_yeni;BXcVVYNa3eojfTuJfmqEtzxHmqLJD5obUDbZiYrGpump,UiWzhZDLxwEnfui6QfuKMDh3Zrjms98fAk4NB9wUYdG,1791017538,pumpswap,en_yeni"


def get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (sol-probe-mum-v1)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(60)
                continue
            return e.code, None
        except Exception:
            time.sleep(5)
    return -1, None


def main():
    os.makedirs(OUT, exist_ok=True)
    satir = []
    ornek = 0
    kayitlar = [x.split(",") for x in LISTE.split(";") if x]
    for k, (tok, pair, t0, dex, etiket) in enumerate(kayitlar):
        t0 = int(t0)
        for tur, agg, kac in (("m1", 1, 60), ("m15", 15, 900)):
            bitis = t0 + 1000 * kac
            url = "%s%s/ohlcv/minute?aggregate=%d&limit=1000&before_timestamp=%d&currency=usd&token=%s" % (
                GT, pair, agg, bitis, tok)
            kod, d = get(url)
            liste = []
            if isinstance(d, dict):
                liste = (((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or []
            ts = sorted(int(x[0]) for x in liste) if liste else []
            ilk_mum = ts[0] if ts else ""
            son_mum = ts[-1] if ts else ""
            giris = None
            if liste:
                sonra = sorted([x for x in liste if int(x[0]) >= t0 - kac], key=lambda x: int(x[0]))
                if sonra:
                    giris = float(sonra[0][1])
            yuk = max(float(x[2]) for x in liste) if liste else None
            dus = min(float(x[3]) for x in liste) if liste else None
            satir.append([tok, pair, dex, etiket, tur, t0, kod, len(liste), ilk_mum, son_mum,
                          round((ilk_mum - t0) / 60.0, 1) if ts else "",
                          round((son_mum - t0) / 3600.0, 2) if ts else "",
                          giris if giris else "",
                          round(yuk / giris - 1, 4) if (giris and yuk) else "",
                          round(dus / giris - 1, 4) if (giris and dus) else ""])
            if liste and ornek < 3 and tur == "m1":
                with open(os.path.join(OUT, "ornek_%d.json" % ornek), "w") as f:
                    json.dump(d, f)
                ornek += 1
            print("%2d/%d %-9s %-4s kod=%s mum=%d" % (k + 1, len(kayitlar), etiket, tur, kod, len(liste)), flush=True)
            time.sleep(ARA)
    with open(os.path.join(OUT, "ozet.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["token", "pair", "dex", "etiket", "tur", "t0", "http", "n_mum", "ilk_mum", "son_mum",
                    "ilk_mum_t0dan_dk", "son_mum_t0dan_saat", "giris_open", "max_yuk", "min_dus"])
        w.writerows(satir)
    ok = sum(1 for s in satir if s[7] > 0)
    print("=" * 44)
    print("PROBE MUM V1 | cagri %d | mum donen %d | 404 %d | 429/hata %d"
          % (len(satir), ok, sum(1 for s in satir if s[6] == 404), sum(1 for s in satir if s[6] not in (200, 404))))
    print("=" * 44)


if __name__ == "__main__":
    main()
