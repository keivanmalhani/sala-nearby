#!/opt/homebrew/bin/python3
"""Resolve each Sala Nearby cinema to its Google Maps place id and rating.

Uses the tbm=map endpoint the Maps frontend itself calls.

Run with homebrew python by habit, but measured 2026-09-09 this endpoint does NOT care:
/opt/homebrew/bin/python3 (OpenSSL 3.6.3), /usr/bin/python3 (LibreSSL 2.8.3) and macOS
curl all answer 200 with an identical 32,715-byte body. The TLS-fingerprint wall that
bites on some careers sites is not present here, and assuming it is would send the next
person hunting a client problem that does not exist.
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
H = {"User-Agent": UA, "Accept-Language": "es-MX,es;q=0.9"}
PB = ("!4m12!1m3!1d1000!2d{lng}!3d{lat}!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1"
      "!7i20!10b1!12m3!1e2!2b1!4e2!17m1!3e1")


def search(q, lat, lng):
    u = ("https://www.google.com/search?tbm=map&hl=es&gl=mx&q="
         + urllib.parse.quote(q) + "&pb=" + PB.format(lat=lat, lng=lng))
    r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40)
    body = r.read().decode("utf-8", "replace")
    if not body.startswith(")]}'"):
        raise RuntimeError("unexpected body head: %r" % body[:60])
    return r.status, json.loads(body.split("\n", 1)[1])


def place_nodes(d):
    """Yield every place record in a tbm=map answer, single-result or list."""
    try:
        top = d[0][1]
    except (IndexError, TypeError):
        return
    for row in top:
        if isinstance(row, list) and len(row) > 14 and isinstance(row[14], list):
            yield row[14]


FORMATS = {"market", "platino", "premium", "vip", "imax", "casa", "arte"}


def strip_accents(t):
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFD", t)
                   if unicodedata.category(ch) != "Mn")


def field(node, i):
    return node[i] if len(node) > i else None


def haversine(a, b, c, e):
    from math import radians, sin, cos, asin, sqrt
    dl, dp = radians(e - b), radians(c - a)
    h = sin(dp / 2) ** 2 + cos(radians(a)) * cos(radians(c)) * sin(dl / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def main():
    cins = json.load(open(sys.argv[1]))
    out = []
    for c in cins:
        label = c["n"] if str(c["id"]).startswith("cineteca") else "Cinemex " + c["n"]
        q = label + " " + c["a"].split(",")[0] + " Ciudad de Mexico"
        try:
            st, d = search(q, c["lat"], c["lng"])
        except Exception as e:
            print("FAIL %-34s %s" % (c["n"], e))
            out.append(dict(c, http=str(e), place_id=None))
            continue
        # Distance alone cannot separate a Market from a Platino: Cinemex puts both in
        # the same mall at the same coordinate. So score on distance AND on the name,
        # and let the format word (Market / Platino / Premium) break the tie.
        want = set(re.findall(r"\w+", strip_accents(label.lower())))
        best, bestscore, bestkm = None, -9e9, 9e9
        for n in place_nodes(d):
            gp = field(n, 9)
            if not (isinstance(gp, list) and len(gp) > 3):
                continue
            km = haversine(c["lat"], c["lng"], gp[2], gp[3])
            if km > 1.2:
                continue
            have = set(re.findall(r"\w+", strip_accents(str(field(n, 11) or "").lower())))
            score = 3.0 * len(want & have) - 1.5 * len(FORMATS & (want ^ have)) - 4.0 * km
            if score > bestscore:
                bestscore, bestkm, best = score, km, n
        if best is None:
            print("MISS %-34s no candidate within 1.2 km" % c["n"])
            out.append(dict(c, http=st, place_id=None))
            continue
        rat = field(best, 4) or []
        out.append(dict(
            c, http=st,
            g_name=field(best, 11), g_addr=field(best, 18),
            feature_id=field(best, 10), place_id=field(best, 78),
            rating=(rat[7] if len(rat) > 7 else None),
            reviews=(rat[8] if len(rat) > 8 else None),
            km_off=round(bestkm, 3)))
        print("OK   %-34s %-46s r=%-4s n=%-6s %.2fkm" % (
            c["n"], str(field(best, 11))[:46], out[-1]["rating"], out[-1]["reviews"], bestkm))
        time.sleep(1.1)
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    got = sum(1 for x in out if x.get("place_id"))
    print("\n%d of %d resolved to a place id" % (got, len(out)))


if __name__ == "__main__":
    main()
