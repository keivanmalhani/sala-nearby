#!/usr/bin/env python3
"""Pull today's Cinemex showtimes and splice them into the page.

    /opt/homebrew/bin/python3 refresh-showtimes.py            # fetch, check, write
    /opt/homebrew/bin/python3 refresh-showtimes.py --dry-run  # fetch and check, write nothing

WHY THIS FILE EXISTS AT ALL. The original pipeline was three scripts in a session
scratchpad under /private/tmp, and one of them read the curated venue list out of a fourth
file that also only lived there. /private/tmp is cleaned; a refresh that depends on it is a
refresh that works until the machine reboots. Everything here reads from the repo.

WHERE THE TIMES COME FROM. Cinemex's own public web API, the one cinemex.com calls:

    GET https://api.cinemex.com/rest/v2.37.2/cinemas/
    GET https://api.cinemex.com/rest/v2.37.2/cinemas/<id>/movies
        x-api-consumer-key: XXQha7vz4kdvoMSdixhN

THE VERSION IS IN THE PATH, NOT IN A HEADER. Every header spelling of app-version
(`app-version`, `x-app-version`, `version`, `appversion`) answers 400 "app-update-required",
which reads like an auth wall and is really a URL shape. That dead end cost twenty minutes
the first time.

WHY THE PAYLOAD IS INDEX-ENCODED. 5,000-odd sessions as plain JSON is 1.3 MB. As arrays of
integers into a shared film/format/day table it is about 230 KB, and the whole page is
330 KB. That difference is the whole of "it launches instantly".

THE CONTROLS, and they are the reason this is not a one-liner. A refresh that half-works
writes a page that looks fine and lists nothing on Thursday, so before anything is written
the new payload is compared to the one already in the page and rejected if it is materially
worse: fewer cinemas, a big drop in sessions, fewer films, or a first day that is not today.
An empty answer from the API is a successful HTTP request, and that is exactly the shape
this project has been bitten by three times.
"""
from __future__ import annotations

import json
import math
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import OrderedDict
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

BASE = "https://api.cinemex.com/rest/v2.37.2/"
HEADERS = {
    # The homebrew interpreter's OpenSSL, never /usr/bin/python3's LibreSSL -- the second
    # gets 403 from hosts the first gets 200 from, which is written up in the memory file
    # about probing careers sites and applies to any TLS-fingerprinting host.
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"),
    "Accept": "*/*",
    "Origin": "https://cinemex.com",
    "Referer": "https://cinemex.com/",
    "x-api-consumer-key": "XXQha7vz4kdvoMSdixhN",
}
CTX = ssl.create_default_context()

PARQUE_MEXICO = (19.4117, -99.1690)
RADIUS_KM = 9.0

# The cinemas whose name in the live API differs from the name in the hand-written venue
# audit. Written out rather than fuzzy-matched: a fuzzy match that lands on the wrong room
# points him at the wrong screen, which is worse than showing no audit at all.
HAND = {
    "insurgentes": "Cinemex Insurgentes",
    "pabelloncuauhtemoc": "Cinemex Pabellon Cuauhtemoc",
    "parquedelta": "Cinemex Parque Delta + Parque Delta Platino",
    "parquedeltaplatino": "Cinemex Parque Delta + Parque Delta Platino",
    "reformacasadearte": "Cinemex Reforma Casa de Arte",
    "reforma222market": "Cinemex Reforma 222 Market",
    "patriotismomarket": "Cinemex Patriotismo Market + Patriotismo Platino",
    "patriotismoplatino": "Cinemex Patriotismo Market + Patriotismo Platino",
    "centrotelmex": "Cinemex Centro Telmex",
    "galerias": "Cinemex Galerias (Plaza de las Estrellas)",
    "sanantonio": "Cinemex San Antonio",
    "real": "Cinemex Real",
    "portalcentro": "Cinemex Portal Centro",
    "universidad": "Cinemex Universidad",
    "felixcuevasplatino": "Cinemex Felix Cuevas Platino",
    "manacar": "Cinemex Manacar",
    "galeriasinsurgentesmarket": "Cinemex Galerias Insurgentes Market",
    "antaramarket": "Cinemex Antara Market + Antara Platino",
    "antaraplatino": "Cinemex Antara Market + Antara Platino",
}


# ------------------------------------------------------------------ small helpers

def salaOf(s):
    """The room, from whichever field this build of the API is using."""
    n = s.get("auditorium_number")
    if n in (None, ""):
        return ""
    n = str(n).strip()
    return n if n.lower().startswith("sala") else "Sala " + n


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def get(path, tries=3, cap=12_000_000):
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path.lstrip("/"), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
                return json.loads(r.read(cap))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and i < tries - 1:
                time.sleep(3 * (i + 1))
                continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            raise


# ------------------------------------------------------------------ the page's own data

def read_page():
    return open(PAGE, encoding="utf-8").read()


def venue_names(page):
    """The curated venue names, in the order they appear in `const V=` on the page.

    Read out of the page rather than a build file so this script has exactly one input.
    The index into this list is what a cinema's `v` field points at, so the ORDER is
    load-bearing and a change to V without a re-run here would silently mislabel rooms."""
    i = page.find("const V=[")
    j = page.find("const PLAIN=", i)
    if i < 0 or j < 0:
        sys.exit("could not find the venue array in docs/index.html")
    names = re.findall(r'\{name:"([^"]+)"', page[i:j])
    if len(names) < 30:
        sys.exit("only %d venue names found in V -- the page has changed shape" % len(names))
    return names


def current_payload(page):
    i = page.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob")
    j = page.find("\n", i)
    return json.loads(page[i + len("const SHOWS="):j].rstrip().rstrip(";")), i, j


# ------------------------------------------------------------------ fetch

def fetch():
    cinemas = get("cinemas/")
    near = []
    for c in cinemas:
        try:
            d = km(PARQUE_MEXICO, (float(c["lat"]), float(c["lng"])))
        except Exception:
            continue
        if d <= RADIUS_KM:
            near.append((d, c))
    near.sort(key=lambda x: x[0])
    print("%d Cinemex cinemas within %.1f km of Parque Mexico" % (len(near), RADIUS_KM))
    if not near:
        sys.exit("the cinemas endpoint answered with nothing in range -- refusing to write")

    out, failed = [], []
    for d, c in near:
        try:
            movies = get("cinemas/%s/movies" % c["id"])
        except Exception as e:
            failed.append((c["name"], str(e)[:60]))
            print("  %-36s FAILED %s" % (c["name"][:36], str(e)[:50]))
            continue
        films, sessions = [], 0
        for m in movies:
            vers = []
            for v in (m.get("versions") or []):
                # CINEMEX CHANGED THE SESSION SHAPE ON 2026-09-08, some time between the
                # 11:34 pull and 14:45 the same day. It used to send "url" (a full
                # checkout link) and "auditorium_name" ("Sala 5"). It now sends neither:
                # the checkout id is the session's own "id", and the room is
                # "auditorium_number" ("5"). Both old spellings are still read first, so
                # this works whichever shape comes back, and check() below refuses a
                # payload whose sessions have lost their ticket ids -- without that guard
                # the change ships 8,000 dead time chips and every count still looks right.
                ss = [{"t": s.get("datetime"),
                       "sala": s.get("auditorium_name") or salaOf(s),
                       "avail": s.get("availability"),
                       "url": s.get("url"), "sid": s.get("id")}
                      for s in (v.get("sessions") or [])]
                if ss:
                    vers.append({"label": v.get("label"), "type": v.get("type") or [],
                                 "sessions": ss})
                    sessions += len(ss)
            if vers:
                info = m.get("info") or {}
                films.append({"id": m.get("id"), "name": m.get("name"),
                              "dur": info.get("duration"), "rating": info.get("rating"),
                              "genre": info.get("genre") or [], "dir": info.get("director"),
                              "orig": info.get("original_title"), "versions": vers})
        info = c.get("info") or {}
        out.append({"id": c["id"], "name": c["name"], "lat": float(c["lat"]),
                    "lng": float(c["lng"]), "km": round(d, 2),
                    "platinum": bool(c.get("platinum")),
                    "addr": info.get("address", ""), "phone": info.get("phone", ""),
                    "films": films})
        print("  %-36s %5.2f km  %2d films  %4d showtimes"
              % (c["name"][:36], d, len(films), sessions))
        time.sleep(0.35)
    return out, failed


# ------------------------------------------------------------------ compact

def compact(raw_cinemas, vnames):
    vidx = {norm(n): i for i, n in enumerate(vnames)}
    films, fmts, days, cins, unmatched = OrderedDict(), OrderedDict(), OrderedDict(), [], []

    for c in raw_cinemas:
        key = norm(c["name"])
        vname = HAND.get(key)
        vi = vidx.get(norm(vname)) if vname else vidx.get(key)
        if vi is None:
            unmatched.append(c["name"])
        sess = []
        for f in c["films"]:
            fid = f["id"]
            if fid not in films:
                films[fid] = {"n": f["name"], "d": (f.get("dur") or "").replace(" ", ""),
                              "r": f.get("rating") or "", "g": (f.get("genre") or [])[:2],
                              "o": f.get("orig") or "", "dir": (f.get("dir") or "")[:60],
                              "y": ""}
            for v in f["versions"]:
                lab = v["label"]
                if lab not in fmts:
                    fmts[lab] = {"i": len(fmts), "t": v.get("type") or []}
                fi = fmts[lab]["i"]
                for s in v["sessions"]:
                    t = s.get("t") or ""
                    day, clock = t[:10], t[11:16]
                    if not day or not clock:
                        continue
                    if day not in days:
                        days[day] = len(days)
                    url = s.get("url") or ""
                    cid = url.rsplit("/", 1)[-1] if "/checkout/" in url else ""
                    if not cid and s.get("sid") not in (None, ""):
                        cid = str(s["sid"])
                    sess.append([fid, fi, days[day],
                                 int(clock[:2]) * 60 + int(clock[3:5]),
                                 (s.get("avail") or "high")[0], cid, s.get("sala") or ""])
        cins.append({"id": c["id"], "n": c["name"], "lat": c["lat"], "lng": c["lng"],
                     "km": c["km"], "p": 1 if c["platinum"] else 0,
                     "a": c["addr"], "ph": c.get("phone", ""), "v": vi, "s": sess})

    counts = {}
    for c in cins:
        for s in c["s"]:
            counts[s[0]] = counts.get(s[0], 0) + 1
    for fid in films:
        films[fid]["c"] = counts.get(fid, 0)

    # THE DAY INDEX HAS TO BE CHRONOLOGICAL. It is assigned in parse order above, which is
    # whatever order the API happened to return -- the date rail once read "Wed 9 Sep, Thu
    # 24 Sep, Fri 25 Sep ... Wed 16 Sep" because of exactly this. Renumber by date, then
    # rewrite every session's day field through the map.
    order = sorted(days.keys())
    remap = {days[d]: i for i, d in enumerate(order)}
    dropped = 0
    for c in cins:
        for row in c["s"]:
            row[2] = remap[row[2]]
        c["s"].sort(key=lambda x: (x[2], x[3]))
        # THE API REPEATS A SESSION OCCASIONALLY, and it reaches his eyes as a film listed
        # at the same minute twice -- San Antonio showed Toy Story 5 at 17:45 twice on
        # 2026-09-08, which reads as a bug in the app rather than in the source. One
        # duplicate in 7,853 is small enough that nothing else would ever have flagged it.
        # Keyed on film, format, day and minute, so two genuinely different screenings of
        # the same film can still coexist.
        seen, keep = set(), []
        for row in c["s"]:
            k = (row[0], row[1], row[2], row[3])
            if k in seen:
                dropped += 1
                continue
            seen.add(k)
            keep.append(row)
        c["s"] = keep
    if dropped:
        print("dropped %d duplicate session(s) the API returned twice" % dropped)

    return {"at": datetime.now().astimezone().isoformat()[:16],
            "films": films,
            "fmts": [{"l": k, "t": v["t"]} for k, v in fmts.items()],
            "days": order,
            "cin": cins}, unmatched


# ------------------------------------------------------------------ the controls

def cinemex_only(payload):
    """The published payload with Cineteca Nacional taken out of it.

    This script fetches Cinemex and nothing else, so what it produces is always the
    Cinemex half. Cineteca is merged in afterwards by refresh-cineteca.py, which strips
    and re-adds its own rows and is safe to run in either order. Comparing a Cinemex-only
    pull against a page that already holds both is comparing 40 films to 75 and refusing
    every honest refresh -- which is what happened the first time this ran after Cineteca
    went in on 2026-09-08."""
    cin = [c for c in payload["cin"] if not str(c["id"]).startswith("cineteca-")]
    keep = {str(s[0]) for c in cin for s in c["s"]}
    films = {k: v for k, v in payload["films"].items() if str(k) in keep}
    return dict(payload, cin=cin, films=films)


def check(new, old):
    """Refuse a payload that is materially worse than the one already published.

    Every one of these has a real failure behind it. A partial fetch is a successful set of
    HTTP requests, so nothing upstream raises; the page just quietly lists less."""
    problems = []
    n_new = sum(len(c["s"]) for c in new["cin"])
    n_old = sum(len(c["s"]) for c in old["cin"])

    if len(new["cin"]) < len(old["cin"]) - 2:
        problems.append("cinemas %d -> %d" % (len(old["cin"]), len(new["cin"])))
    if n_new < n_old * 0.6:
        problems.append("showtimes %d -> %d, a drop of %.0f%%"
                        % (n_old, n_new, 100 * (1 - n_new / max(n_old, 1))))
    if len(new["films"]) < len(old["films"]) * 0.7:
        problems.append("films %d -> %d" % (len(old["films"]), len(new["films"])))

    linked = sum(1 for c in new["cin"] if c["v"] is not None)
    linked_old = sum(1 for c in old["cin"] if c["v"] is not None)
    if linked < linked_old:
        problems.append("venue links %d -> %d" % (linked_old, linked))

    # The first day in the data should be today. If it is not, either the fetch is stale or
    # the day renumbering has broken, and both look identical from the page.
    today = date.today().isoformat()
    if new["days"] and new["days"][0] != today:
        problems.append("first day is %s, not today (%s)" % (new["days"][0], today))

    # A TIME CHIP WITH NO TICKET ID LINKS TO "#". Nothing above notices: the cinema is
    # there, the film is there, the count is right, and every one of the times is dead.
    # That is exactly what happened when Cinemex stopped sending "url" on 2026-09-08, so
    # the share of sessions carrying an id is now a control rather than an assumption.
    def ticketed(p):
        n = t = 0
        for c in p["cin"]:
            for s in c["s"]:
                t += 1
                if s[5]:
                    n += 1
        return n, t

    n_id, n_tot = ticketed(new)
    o_id, o_tot = ticketed(old)
    share_new = n_id / max(n_tot, 1)
    share_old = o_id / max(o_tot, 1)
    if share_new < min(0.9, share_old - 0.05):
        problems.append("only %d of %d showtimes carry a ticket id (%.0f%%, was %.0f%%) "
                        "-- every time chip without one links nowhere"
                        % (n_id, n_tot, 100 * share_new, 100 * share_old))

    salas_new = sum(1 for c in new["cin"] for s in c["s"] if len(s) > 6 and s[6])
    salas_old = sum(1 for c in old["cin"] for s in c["s"] if len(s) > 6 and s[6])
    if salas_old and salas_new < salas_old * 0.5:
        problems.append("room names %d -> %d" % (salas_old, salas_new))

    empty = [c["n"] for c in new["cin"] if not c["s"]]
    if empty:
        problems.append("%d cinemas came back with no showtimes at all: %s"
                        % (len(empty), ", ".join(empty[:4])))
    return problems, n_new, n_old, linked


# ------------------------------------------------------------------ main

def by_day(payload):
    """{date: n showtimes}. The single most useful diagnostic here.

    A total that moves is ambiguous -- a 44% jump could be a real week of new listings or a
    double-count -- and the per-day shape tells them apart in one look: real new listings
    land on days the old pull did not have, or on days whose schedule was not published
    yet. A double-count raises every day at once."""
    out = {}
    for c in payload["cin"]:
        for s in c["s"]:
            d = payload["days"][s[2]]
            out[d] = out.get(d, 0) + 1
    return out


def main():
    dry = "--dry-run" in sys.argv
    page = read_page()
    vnames = venue_names(page)
    old, i, j = current_payload(page)
    print("the page currently holds %s: %d cinemas, %d films, %d showtimes\n"
          % (old["at"], len(old["cin"]), len(old["films"]),
             sum(len(c["s"]) for c in old["cin"])))

    cache = os.path.join(os.environ.get("TMPDIR", "/tmp"), "sala-cinemex-raw.json")
    if "--cached" in sys.argv and os.path.exists(cache):
        blob = json.load(open(cache, encoding="utf-8"))
        raw, failed = blob["cinemas"], blob["failed"]
        print("using the cached pull from %s (%s)\n" % (cache, blob["at"]))
    else:
        raw, failed = fetch()
        json.dump({"at": datetime.now().astimezone().isoformat()[:16],
                   "cinemas": raw, "failed": failed},
                  open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    new, unmatched = compact(raw, vnames)
    had_cineteca = [c["n"] for c in old["cin"] if str(c["id"]).startswith("cineteca-")]
    problems, n_new, n_old, linked = check(new, cinemex_only(old))

    print("\nfilms %d, formats %d, days %d, cinemas %d, showtimes %d"
          % (len(new["films"]), len(new["fmts"]), len(new["days"]),
             len(new["cin"]), n_new))
    print("linked to a curated venue: %d of %d" % (linked, len(new["cin"])))
    print("days %s .. %s" % (new["days"][0], new["days"][-1]))

    nd, od = by_day(new), by_day(cinemex_only(old))
    print("\n  day          now    was")
    for d in sorted(set(nd) | set(od)):
        a, b = nd.get(d, 0), od.get(d, 0)
        mark = "  <- new day" if b == 0 and a else ("  <- gone" if a == 0 else "")
        print("  %s %6d %6d%s" % (d, a, b, mark))
    if unmatched:
        print("not linked to an audit (live times only, expected outside the 5 km study):")
        for n in unmatched:
            print("   ", n)
    if failed:
        print("cinemas that would not answer:")
        for n, why in failed:
            print("   %-36s %s" % (n[:36], why))

    if problems:
        print("\nREFUSING TO WRITE. The new data is worse than what is published:")
        for p in problems:
            print("  -", p)
        return 2

    blob = json.dumps(new, ensure_ascii=False, separators=(",", ":"))
    print("\npayload %.0f KB (was %.0f KB)"
          % (len(blob.encode()) / 1024, (j - i - len("const SHOWS=")) / 1024))
    if dry:
        print("--dry-run, nothing written")
        return 0

    out = page[:i] + "const SHOWS=" + blob + ";" + page[j:]
    open(PAGE, "w", encoding="utf-8").write(out)
    print("wrote docs/index.html: %s bytes" % format(len(out), ","))
    if had_cineteca:
        print("\nCINETECA IS NOT IN THE PAGE RIGHT NOW. This script writes the Cinemex half")
        print("      and nothing else, so %d sedes just left the page:" % len(had_cineteca))
        for n in had_cineteca:
            print("        " + n)
        print("      Run refresh-cineteca.py before you commit or push anything.")
    print("\nNEXT: refresh-cineteca.py, then refresh-posters.py for any new films, then bump")
    print("      the sw.js cache name, or a phone with the old version installed keeps")
    print("      serving it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
