#!/usr/bin/env python3
"""Add Cineteca Nacional's three sedes to the page, and their real showtimes.

    /opt/homebrew/bin/python3 refresh-cineteca.py            # fetch, check, write
    /opt/homebrew/bin/python3 refresh-cineteca.py --dry-run  # fetch and check, write nothing

WHY THIS AND NOT CINEPOLIS. The first attempt was Cinepolis, which is the bigger gap --
half the screens in the city. It cannot be read from this machine at all. Their whole
board comes from api-g.cinepolis.com, a GraphQL host behind a Cloudflare firewall rule
that answers a flat "Sorry, you have been blocked" to everything tried on 2026-09-08:
homebrew Python, macOS curl over HTTP/2 with a complete browser header set, an OPTIONS
preflight, and -- the one that settles it -- a fetch issued by his own signed-in Chrome
from cinepolis.com's own page, which failed the same way. It is not the client and it is
not automation detection; every request from this network is refused. cinepolis.com
itself serves fine and is a pure client-side shell: /robots.txt, /sitemap.xml,
/mx/cartelera and /mx/cines all return the same 4.4 KB app skeleton, so a 200 there is
the catch-all route rather than a document. There is no second door. Worth retrying from
Mexico City in October.

WHAT CINETECA GIVES HIM THAT CINEMEX CANNOT. Repertory and festival programming, the
thing a chain multiplex never carries, four to seven kilometres from Parque Mexico. It
was in none of the 42 audited venues and none of the 32 boards the page already reads.

HOW IT READS, and it is the reading order that found it: the page is a plain PHP site,
and its cartelera renders "cargando..." because the list arrives from an XHR.

    POST https://www.cinetecanacional.net/data/cartelera.php
         vista=full&fecha=YYYY-MM-DD&cinema=000&eventId=000
    -> {"html": "<div>... one card per film, with FilmId and which sedes ..."}

    GET  https://www.cinetecanacional.net/detallePelicula.php?FilmId=<id>&cinemas=<codes>
    -> server-rendered, and it carries EVERY day's times at once, each one an <a> to
       rbvfcn.cinetecanacional.net/Ticketing/visSelectTickets.aspx with the cinemacode
       and the session id in the query string.

TWO THINGS THAT COST TIME AND WILL AGAIN. The POST must carry the page's own hidden
values -- `vista=full`, `cinema=000`, `eventId=000`. Sending them empty answers 200 with
a two-byte body, which is a successful request that says nothing, and is exactly the
absence-shaped success this project keeps being bitten by. And **the system resolver on
this laptop intermittently fails on www.cinetecanacional.net** while 1.1.1.1 answers
201.98.21.38 straight away; two fetches succeeded, then every one raised gaierror. So
this resolves the host itself and falls back to that address rather than reporting the
site down -- a DNS error is not the site saying no.

ON AVATURE, WHICH IS NOT THIS SITE BUT IS THE OTHER ONE READ TODAY: its sitemap is
never the board. Siemens' index is 580 urls of portal page names and HSBC's is five
locale files of thirteen each, zero postings in either. That is the reverse of Cognizant,
where the sitemap WAS the whole board, so neither is the rule -- ask, and read what comes
back. (Checked independently by a parallel session on HSBC.)

THE SEDES AND THEIR COORDINATES come off Cineteca's own footer, out of the Google Maps
links it publishes (the `!8m2!3d<lat>!4d<lng>` pair, which is the place rather than the
map centre). Nothing here is geocoded and nothing is guessed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import socket
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

# merge-films.py folds the entries the two chains publish for the same film into one, and
# it has to run AFTER this script rather than before: refresh-showtimes.py rewrites the
# whole payload from the Cinemex side and drops Cineteca, so this is the last writer in
# the chain and the only point at which both halves are on the page together. Called
# below rather than left as a line in the README, because the defect it fixes is
# invisible on the page -- a film listed twice looks like two films.
_spec = importlib.util.spec_from_file_location(
    "merge_films", os.path.join(ROOT, "merge-films.py"))
MERGE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MERGE)

HOST = "www.cinetecanacional.net"
FALLBACK_IP = "201.98.21.38"          # 1.1.1.1's answer on 2026-09-08; used only if the
                                      # system resolver fails, never in preference to it.
BASE = "https://%s/" % HOST
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()

PARQUE_MEXICO = (19.4117, -99.1690)

# cinemacode -> the sede. Latitude and longitude are Cineteca's own, read off the maps
# links in its footer. `code` is what the site calls the sede in every url it emits.
SEDES = {
    "003": {"name": "Cineteca Nacional Mexico (Xoco)",
            "lat": 19.360612, "lng": -99.1645128,
            "addr": "Av. Mexico Coyoacan 389, Xoco, Benito Juarez"},
    "001": {"name": "Cineteca Nacional Chapultepec",
            "lat": 19.3886975, "lng": -99.228485,
            "addr": "Av. Vasco de Quiroga 1401, Santa Fe, Alvaro Obregon"},
    "002": {"name": "Cineteca Nacional de las Artes",
            "lat": 19.3559633, "lng": -99.1352257,
            "addr": "Av. Rio Churubusco 79, Country Club Churubusco, Coyoacan"},
}

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
         "diciembre": 12}

# The site marks the language in the title itself: "Coyote Vs Acme DOB" and
# "Coyote Vs Acme SUB" are two entries for one film. Split that off so the film name is
# the film name and the language is a format, which is how the page already works.
LANG_SUFFIX = re.compile(r"\s+(DOB|SUB|SUBT|ESP)\s*$", re.I)
LANG_LABEL = {"DOB": "ESPANOL", "ESP": "ESPANOL", "SUB": "SUBTITULADA",
              "SUBT": "SUBTITULADA"}


# ------------------------------------------------------------------ fetching

# A gaierror is a fact about this laptop's resolver, not about Cineteca. Reporting the
# site as unreachable on one is the mistake that nearly retired a live job board on
# 2026-09-07 -- two socket refusals and a DNS error, no HTTP response among them, read as
# the board saying no.
#
# ASKING FIRST AND CONNECTING SECOND DOES NOT WORK HERE, and the first version of this
# file did exactly that: a getaddrinfo probe, then a normal request if it succeeded. The
# resolver on this laptop fails intermittently rather than steadily, so the probe passed
# and the request that followed it a millisecond later raised anyway -- six films were
# lost that way on the first run. The fallback has to be on the FAILURE, not on a
# prediction of it.
_PINNED = [False]


# The fallback is a RESOLVER override rather than a connection override, and the
# difference is not academic: the first attempt built an HTTPSConnection on the address
# and then set `.host` back to the name so SNI and the Host header would be right, which
# is exactly the attribute connect() resolves -- so it looked pinned and resolved anyway.
# Answering inside getaddrinfo leaves the hostname in place everywhere it matters, so TLS
# still validates against the certificate for www.cinetecanacional.net.
_REAL_GETADDRINFO = socket.getaddrinfo


def _getaddrinfo(host, port, *a, **kw):
    try:
        return _REAL_GETADDRINFO(host, port, *a, **kw)
    except socket.gaierror:
        if host == HOST:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (FALLBACK_IP, port or 443))]
        raise


def _pin():
    socket.getaddrinfo = _getaddrinfo


def _opener(_pinned):
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))


def fetch(path, data=None, tries=3, cap=12_000_000):
    headers = {"User-Agent": UA, "Accept": "*/*",
               "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
               "Referer": BASE + "cartelera.php"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
    last = None
    for i in range(tries + 1):
        try:
            op = _opener(_PINNED[0])
            req = urllib.request.Request(BASE + path.lstrip("/"), data=body,
                                         headers=headers)
            with op.open(req, timeout=45) as r:
                return r.read(cap).decode("utf-8", "replace")
        except urllib.error.URLError as e:
            last = e
            if isinstance(e.reason, socket.gaierror) and not _PINNED[0]:
                _PINNED[0] = True
                _pin()
                print("  (the resolver stopped answering for %s; answering it with %s for "
                      "the rest of this run)" % (HOST, FALLBACK_IP))
                continue                              # retry immediately, pinned
            time.sleep(2 * (i + 1))
        except Exception as e:                        # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise last


# ------------------------------------------------------------------ parsing

def strip_tags(h):
    h = re.sub(r"<[^>]+>", " ", h)
    for k, v in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"'),
                 ("&lt;", "<"), ("&gt;", ">"), ("&aacute;", "a"), ("&eacute;", "e")):
        h = h.replace(k, v)
    return re.sub(r"\s+", " ", h).strip()


def film_cards(html):
    """(film_id, title, meta) for every card in one day's cartelera."""
    out = []
    for m in re.finditer(
            r'detallePelicula\.php\?FilmId=([A-Z0-9]+)&cinemas=([0-9,]+)"'
            r'(.*?)(?=detallePelicula\.php\?FilmId=|$)', html, re.S):
        fid, codes, rest = m.group(1), m.group(2), m.group(3)
        t = re.search(r'font-weight-bold" style="min-height:40px;">([^<]+)<', rest)
        meta = re.search(r"<p>\((.*?)\)</p>", rest, re.S)
        out.append({"id": fid, "codes": codes.split(","),
                    "title": strip_tags(t.group(1)) if t else "",
                    "meta": strip_tags(meta.group(1)) if meta else ""})
    # ONE FILM CAN APPEAR MORE THAN ONCE IN A DAY'S GRID, and the key is the FilmId
    # alone. Keying on (id, sedes) looked safer and was wrong: the same film shows up
    # under two cards carrying the SAME sede list, so both survived, its detail page was
    # fetched twice and every one of its showtimes was appended twice. That reached the
    # page -- "14:00 14:00", "15:00 15:00 17:30 17:30" -- before anything noticed, because
    # a doubled showtime is a plausible-looking row rather than an error.
    #
    # Merge the sede lists instead: the detail page takes `cinemas=` as a list and returns
    # every one of them in a single request.
    merged = {}
    for f in out:
        m = merged.setdefault(f["id"], dict(f, codes=[]))
        for c in f["codes"]:
            if c not in m["codes"]:
                m["codes"].append(c)
        if not m.get("title"):
            m["title"] = f["title"]
        if not m.get("meta"):
            m["meta"] = f["meta"]
    return list(merged.values())


def sessions_for(html, year):
    """Every showtime on one film's detail page: (cinemacode, date, HH:MM, session_id)."""
    out = []
    for m in re.finditer(
            r"visSelectTickets\.aspx\?cinemacode=(\d+)&(?:amp;)?txtSessionId=(\d+)"
            r".*?<div[^>]*>\s*\w+\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s*<br>\s*"
            r"(\d{1,2}):(\d{2})\s*H\s*</div>", html, re.S | re.I):
        code, sid, dd, mes, hh, mm = m.groups()
        month = MESES.get(unicodedata.normalize("NFKD", mes.lower())
                          .encode("ascii", "ignore").decode())
        if not month:
            continue
        y = year
        # A December listing read in January belongs to the year that has just ended, and
        # a January one read in December to the year that has not started. Both happen on
        # a board that publishes a week ahead.
        if month == 1 and date.today().month == 12:
            y = year + 1
        elif month == 12 and date.today().month == 1:
            y = year - 1
        out.append((code, "%04d-%02d-%02d" % (y, month, int(dd)),
                    "%02d:%02d" % (int(hh), int(mm)), sid))
    return out


def split_language(title):
    m = LANG_SUFFIX.search(title or "")
    if not m:
        return title, ""
    return LANG_SUFFIX.sub("", title).strip(), LANG_LABEL.get(m.group(1).upper(), "")


def parse_meta(meta):
    """"(Orig title, Dir.: Name, Country, 2026, Dur.: 112 mins.)" -> its pieces."""
    dur = re.search(r"Dur\.:\s*(\d+)\s*mins?", meta or "", re.I)
    d = re.search(r"Dir\.:\s*([^,]+)", meta or "", re.I)
    y = re.search(r"\b(19\d{2}|20\d{2})\b", meta or "")
    orig = (meta or "").split(",")[0].strip() if meta else ""
    return {"orig": orig, "dir": (d.group(1).strip() if d else "")[:60],
            "dur": ("%dh%02dm" % (int(dur.group(1)) // 60, int(dur.group(1)) % 60)
                    if dur else ""),
            "y": y.group(1) if y else ""}


def km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


# ------------------------------------------------------------------ the page

def read_shows(page):
    i = page.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob -- has the page changed shape?")
    j = page.find("\n", i)
    return json.loads(page[i + len("const SHOWS="):j].rstrip().rstrip(";")), i, j


def date_set(shows):
    """{(cinema id, film id, 'YYYY-MM-DD HH:MM')} -- the payload's meaning, not its indexes.

    This is what the day remap below has to preserve exactly. Comparing index numbers
    would prove nothing: renumbering the days is precisely the operation that changes
    them, and the whole question is whether the DATES came through unchanged."""
    out = set()
    for c in shows["cin"]:
        for s in c["s"]:
            out.add((c["id"], s[0],
                     "%s %02d:%02d" % (shows["days"][s[2]], s[3] // 60, s[3] % 60)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    page = open(PAGE, encoding="utf-8").read()
    shows, i0, i1 = read_shows(page)
    before = date_set(shows)
    n_before = sum(len(c["s"]) for c in shows["cin"])
    print("the page holds %d cinemas, %d showings, %d days"
          % (len(shows["cin"]), n_before, len(shows["days"])))

    # ---- fetch --------------------------------------------------------------
    today = date.today().isoformat()
    listing = fetch("data/cartelera.php",
                    {"vista": "full", "fecha": today, "cinema": "000", "eventId": "000"})
    try:
        html = json.loads(listing)["html"]
    except Exception:
        sys.exit("the cartelera endpoint did not answer with JSON (%d bytes). The hidden "
                 "form values vista=full / cinema=000 / eventId=000 are required; empty "
                 "ones answer 200 with two bytes." % len(listing))
    cards = film_cards(html)
    print("%d films on Cineteca's cartelera for %s" % (len(cards), today))
    if not cards:
        sys.exit("the cartelera answered with no films -- refusing to write")

    films, rows, failed = {}, [], []
    for n, f in enumerate(cards, 1):
        try:
            detail = fetch("detallePelicula.php?FilmId=%s&cinemas=%s"
                           % (f["id"], ",".join(f["codes"])))
        except Exception as e:                        # noqa: BLE001
            failed.append((f["title"], str(e)[:50]))
            continue
        ss = sessions_for(detail, date.today().year)
        # DEDUPE ON THE SESSION ID, which is unique per showing. The detail page emits
        # every showtime twice -- merging the duplicate cartelera cards was not the cause,
        # the repetition is inside one page -- and the first version of this shipped
        # "14:00 14:00" and "15:00 15:00 17:30 17:30" to the page. The id is the site's
        # own key for a screening, so this cannot collapse two genuinely different ones.
        seen_sid = set()
        deduped = []
        for x in ss:
            if x[3] not in seen_sid:
                seen_sid.add(x[3])
                deduped.append(x)
        ss = deduped
        name, lang = split_language(f["title"])
        meta = parse_meta(f["meta"])
        fid = "ct-" + f["id"]
        films[fid] = {"n": name, "d": meta["dur"], "r": "", "g": [],
                      "o": meta["orig"], "dir": meta["dir"], "y": meta["y"]}
        for code, day, clock, sid in ss:
            rows.append((code, fid, lang, day, clock, sid))
        print("  %-52s %2d showings" % (name[:52], len(ss)))
        time.sleep(0.3)

    if failed:
        print("  %d films could not be read, first: %s" % (len(failed), failed[0]))
    if not rows:
        sys.exit("no showtimes were parsed from any film page -- refusing to write")
    print("%d Cineteca showings across %d films, %d sedes"
          % (len(rows), len(films), len({r[0] for r in rows})))

    # ---- merge --------------------------------------------------------------
    # Idempotent: drop whatever Cineteca rows are already there before adding. Re-running
    # this, or running it after the Cinemex refresh has rewritten SHOWS, must converge on
    # the same page rather than stacking duplicates.
    shows["cin"] = [c for c in shows["cin"] if not str(c["id"]).startswith("cineteca-")]
    shows["films"] = {k: v for k, v in shows["films"].items() if not k.startswith("ct-")}
    shows["films"].update(films)

    # Days. Cineteca publishes a week; Cinemex publishes a month, so normally every
    # Cineteca date is already present. Any that is not extends the list, and then EVERY
    # cinema's day index is remapped -- which is why date_set() above exists.
    days = sorted(set(shows["days"]) | {r[3] for r in rows})
    remap = {shows["days"].index(d): days.index(d) for d in shows["days"]}
    for c in shows["cin"]:
        for s in c["s"]:
            s[2] = remap[s[2]]
    added_days = [d for d in days if d not in shows["days"]]
    shows["days"] = days
    if added_days:
        print("days extended by %d: %s" % (len(added_days), ", ".join(added_days)))

    # Formats. Reuse the label if the page already has it so the filter chips do not gain
    # a duplicate that means the same thing.
    def fmt_index(label):
        for n, f in enumerate(shows["fmts"]):
            if f["l"] == label:
                return n
        shows["fmts"].append({"l": label, "t": []})
        return len(shows["fmts"]) - 1

    for code, sede in SEDES.items():
        mine = [r for r in rows if r[0] == code]
        if not mine:
            continue
        d = km(PARQUE_MEXICO, (sede["lat"], sede["lng"]))
        sess = []
        for _c, fid, lang, day, clock, sid in mine:
            sess.append([fid, fmt_index(lang or "CINETECA"), days.index(day),
                         int(clock[:2]) * 60 + int(clock[3:5]), "h",
                         "cineteca:%s:%s" % (code, sid), ""])
        sess.sort(key=lambda x: (x[2], x[3]))
        shows["cin"].append({"id": "cineteca-" + code, "n": sede["name"],
                             "lat": sede["lat"], "lng": sede["lng"], "km": round(d, 2),
                             "p": 0, "a": sede["addr"], "ph": "", "v": None, "s": sess})
        print("  %-40s %5.2f km  %4d showings" % (sede["name"][:40], d, len(sess)))

    # ---- the controls -------------------------------------------------------
    # Each of these has a real failure behind it. A merge that half-works writes a page
    # that looks fine and lists the wrong day.
    problems = []
    after = date_set(shows)
    lost = before - after
    if lost:
        problems.append("the remap changed or lost %d existing showings, first %s"
                        % (len(lost), sorted(lost)[0]))
    n_after = sum(len(c["s"]) for c in shows["cin"])
    if n_after <= n_before:
        problems.append("showings did not grow: %d -> %d" % (n_before, n_after))
    if len(shows["days"]) < len(days):
        problems.append("the day list shrank")
    for c in shows["cin"]:
        for s in c["s"]:
            if not 0 <= s[2] < len(shows["days"]):
                problems.append("a session points at day index %d of %d"
                                % (s[2], len(shows["days"])))
                break
    # str() on BOTH sides, and that is not cosmetic. A session's film id is whatever JSON
    # gave it -- Cinemex ids decode as ints, the ct- ones are strings -- while the film
    # table is a JSON object, so its keys are always strings. Comparing the two raw
    # reported all 40 existing films as orphans and refused a merge that was correct.
    known = {str(k) for k in shows["films"]}
    # No cinema may list the same film at the same minute twice. This is the control the
    # doubled-showtime bug walked straight past: the merge grew the count and preserved
    # every existing row, which is all the other checks ask.
    #
    # SCOPED TO CINETECA ON PURPOSE. Cinemex's own data already carries one duplicate --
    # San Antonio lists film 71757 twice at 17:45 on 2026-09-08 -- and refusing on it
    # would block this merge over a row it did not create. It is reported instead, which
    # is the honest half: this script is not the place to fix the Cinemex reader.
    inherited = 0
    for c in shows["cin"]:
        seen, keep, mine = set(), [], str(c["id"]).startswith("cineteca-")
        for s in c["s"]:
            k = (str(s[0]), s[1], s[2], s[3])
            if k in seen:
                if mine:
                    # Mine is a defect in this file and must stop the run.
                    problems.append("%s lists film %s twice at %s %02d:%02d"
                                    % (c["n"], s[0], shows["days"][s[2]],
                                       s[3] // 60, s[3] % 60))
                    break
                # Inherited is a defect in the Cinemex reader, fixed there too, but it is
                # on his page NOW and leaving it there because it is not mine would be
                # tidy bookkeeping and a visible bug.
                inherited += 1
                continue
            seen.add(k)
            keep.append(s)
        c["s"] = keep
    if inherited:
        print("  dropped %d duplicate showing(s) that came with the Cinemex data "
              "(refresh-showtimes.py now removes these at the source)" % inherited)

    orphan = {str(s[0]) for c in shows["cin"] for s in c["s"]} - known
    if orphan:
        problems.append("%d showings name a film that is not in the film table, first %s"
                        % (len(orphan), sorted(orphan)[0]))
    if problems:
        for p in problems:
            print("  REFUSING: %s" % p)
        sys.exit(1)
    print("controls pass: every one of the %d showings already on the page kept its "
          "exact date and time, and the page gained %d" % (len(before), n_after - n_before))

    # ---- one film, one entry -----------------------------------------------
    # Both chains are on the page now, so this is where "La Odisea" stops being two
    # films. It moves showings between film ids and never adds or drops one; if it
    # cannot do that it raises, and nothing is written.
    n_films = len(shows["films"])
    try:
        merged = MERGE.merge(shows)
    except ValueError as e:
        print("  REFUSING: the film merge: %s" % e)
        sys.exit(1)
    tagged = MERGE.tag_languages(shows)
    for base, rest, total in merged:
        print("  one film, one entry: %-34s %s, %d showings"
              % (shows["films"][base]["n"][:34],
                 " + ".join([str(base)] + [str(r) for r in rest]), total))
    if merged:
        print("  %d films folded into %d, showings unchanged at %d"
              % (n_films, len(shows["films"]), sum(len(c["s"]) for c in shows["cin"])))
    if tagged:
        print("  %d Cineteca language formats can now be filtered on" % tagged)

    if a.dry_run:
        print("--dry-run: nothing written")
        return 0

    shows["at"] = datetime.now().astimezone().isoformat()[:16]
    out = page[:i0] + "const SHOWS=" + json.dumps(shows, separators=(",", ":"),
                                                  ensure_ascii=False) + page[i1:]
    open(PAGE, "w", encoding="utf-8").write(out)
    print("wrote docs/index.html: %s bytes" % format(len(out), ","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
