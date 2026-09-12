#!/usr/bin/env python3
"""Download a poster for every film the page lists, and prove each one is a picture.

    /opt/homebrew/bin/python3 refresh-posters.py          # fetch, verify, write
    /opt/homebrew/bin/python3 refresh-posters.py --check  # verify what is on disk, write nothing
    /opt/homebrew/bin/python3 refresh-posters.py --meta   # refresh cast, country, year, trailer; touch no image

WHERE THE POSTERS COME FROM. Cinemex's own API, the same one cinemex.com calls:

    GET https://api.cinemex.com/rest/v2.37.2/movies/
        x-api-consumer-key: XXQha7vz4kdvoMSdixhN

The version is IN THE PATH, which is why plain /rest/v2/movies answers 400 rather than 404,
and the consumer key is required or it answers 401 "credentials-missing". Both were read out
of the request cinemex.com's own page makes -- see CINEMEX-API.md.

WHY THIS RUNS AT BUILD TIME AND NOT IN THE PAGE. The API answers
`access-control-allow-origin: https://cinemex.com` and nothing else, so a browser on
keivanmalhani.github.io is refused by CORS no matter what. The posters have to be on our own
origin. That is also what makes them work with no signal, which is the point of the app.

THE CONTROL, and it is the whole reason this is a script rather than a loop. Three free map
tile hosts were tried for this app and TWO of them answered HTTP 200 with a refusal painted
into the image -- "API KEY REQUIRED" across a real-looking map. A status code cannot tell a
picture from a polite no. So every download here is opened as an image, its dimensions read,
and anything that is not a portrait JPEG of plausible poster shape is rejected loudly rather
than written to disk. `--check` re-runs that over what is already there.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
OUT = os.path.join(ROOT, "docs", "posters")

API = "https://api.cinemex.com/rest/v2.37.2/movies/"
KEY = "XXQha7vz4kdvoMSdixhN"
HEADERS = {
    "x-api-consumer-key": KEY,
    "Origin": "https://cinemex.com",
    "Referer": "https://cinemex.com/",
    "Accept": "application/json",
    # The homebrew interpreter, never /usr/bin/python3: its LibreSSL gets 403 from hosts
    # that OpenSSL gets 200 from. Same reason find-ats probes with homebrew python.
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/605.1.15"),
}

# A poster is portrait, and these are the bounds a real one falls inside. A 1x1 tracking
# pixel, a square logo and an error page rendered as an image all fail at least one.
MIN_W, MIN_H = 120, 160
MAX_RATIO, MIN_RATIO = 0.90, 0.50          # width / height

YOUTUBE = re.compile(r"^https?://(?:www\.|m\.)?(?:youtube\.com/watch\?(?:\S*&)?v=|youtu\.be/)([\w-]{11})(?![\w-])")


def film_meta(m):
    """What the film sheet shows besides the poster, out of the same API record.

    Idea 8 in docs/IDEAS-2026-09-09.md: Cinemex sends cast, country, year and a trailer for
    nearly every film, and the app threw all of it away. Normalised here so the page can
    trust it. A trailer is kept only when it is a real YouTube video id -- one record on
    12 September sent the bare "https://www.youtube.com/", which would have been a button
    that opens YouTube's home page -- and the cast is cut to the first four names, because
    the longest record that day was 631 characters and a sheet is not a credits roll."""
    info = m.get("info") or {}
    t = YOUTUBE.match((info.get("trailer") or "").strip())
    cast = [c.strip() for c in (info.get("cast") or "").split(",") if c.strip()]
    year = str(info.get("year") or "").strip()
    return {
        "syn": info.get("sinopsis") or "",
        "cast": ", ".join(cast[:4]),
        "country": (info.get("country") or "").strip(),
        "year": year if re.fullmatch(r"\d{4}", year) else "",
        "trailer": "https://www.youtube.com/watch?v=" + t.group(1) if t else "",
    }


def jpeg_size(path):
    """(width, height) read out of the JPEG's own SOF marker, or None if it is not a JPEG.

    Deliberately not `sips -g`, which shells out 39 times and answers for formats this does
    not want to accept. If the bytes are not a JPEG this returns None and the caller rejects
    the file, which is the behaviour an error page delivered with a .jpg name needs."""
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            b = f.read(1)
            while b and b != b"\xff":
                b = f.read(1)
            if not b:
                return None
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            if not marker:
                return None
            m = marker[0]
            if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
                continue
            ln = f.read(2)
            if len(ln) < 2:
                return None
            size = struct.unpack(">H", ln)[0]
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                data = f.read(7)
                if len(data) < 5:
                    return None
                h, w = struct.unpack(">HH", data[1:5])
                return w, h
            f.seek(size - 2, 1)


def verify(path):
    """(ok, why). A picture of a poster, or a reason it is not one."""
    if not os.path.exists(path):
        return False, "missing"
    n = os.path.getsize(path)
    if n < 2000:
        return False, "only %d bytes, too small to be a poster" % n
    wh = jpeg_size(path)
    if wh is None:
        return False, "not a JPEG at all (%d bytes) -- probably an error page" % n
    w, h = wh
    if w < MIN_W or h < MIN_H:
        return False, "%dx%d is too small" % (w, h)
    r = w / h
    if not (MIN_RATIO <= r <= MAX_RATIO):
        return False, "%dx%d is not portrait (ratio %.2f)" % (w, h, r)
    return True, "%dx%d, %d KB" % (w, h, n // 1024)


def page_film_ids():
    """The ids the page actually lists, read out of its own SHOWS blob."""
    s = open(PAGE, encoding="utf-8").read()
    i = s.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob -- did the page change shape?")
    j = s.find("\n", i)
    blob = s[i + len("const SHOWS="):j].rstrip().rstrip(";")
    return json.loads(blob)["films"]


def fetch_movies():
    r = urllib.request.urlopen(urllib.request.Request(API, headers=HEADERS), timeout=40)
    if r.status != 200:
        sys.exit("the movies API answered %s" % r.status)
    return json.load(r)


def main():
    check_only = "--check" in sys.argv
    films = page_film_ids()
    os.makedirs(OUT, exist_ok=True)

    if check_only:
        bad = []
        for fid in sorted(films):
            ok, why = verify(os.path.join(OUT, "%s.jpg" % fid))
            print("  %-8s %s  %s" % (fid, "ok  " if ok else "BAD ", why))
            if not ok:
                bad.append(fid)
        print("\n%d of %d posters are real pictures" % (len(films) - len(bad), len(films)))
        return 1 if bad else 0

    if "--meta" in sys.argv:
        # THE WORDS WITHOUT THE PICTURES. Re-downloading and re-encoding every poster to
        # refresh a cast list rewrites forty-odd JPEGs in git for no visible change, so this
        # updates the text of the entries already on disk and touches no image. The fetch
        # happens before the file is opened for writing, so a failed fetch leaves it alone.
        path = os.path.join(OUT, "index.json")
        manifest = json.load(open(path, encoding="utf-8"))
        movies = {str(m["id"]): m for m in fetch_movies()}
        done = 0
        for fid, entry in manifest.items():
            if fid in movies:
                entry.update(film_meta(movies[fid]))
                done += 1
        json.dump(manifest, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
        have = lambda k: sum(1 for e in manifest.values() if e.get(k))
        print("updated %d of %d entries: cast %d, country %d, year %d, trailer %d"
              % (done, len(manifest), have("cast"), have("country"), have("year"), have("trailer")))
        return 0 if done else 1

    movies = {str(m["id"]): m for m in fetch_movies()}
    print("the API knows %d films; the page lists %d" % (len(movies), len(films)))

    missing = [f for f in films if f not in movies]
    if missing:
        print("NOT IN THE API, no poster for these: %s" % ", ".join(sorted(missing)))

    got, failed = 0, []
    manifest = {}
    # SORT BY THE ID AS TEXT, PADDED. Cinemex's film ids are numbers and Cineteca's are
    # "ct-HO00009798", so int() stopped being a safe key the moment Cineteca went into the
    # page on 2026-09-08 -- this line raised ValueError and took the whole poster refresh
    # down with it, after the fetch had already succeeded.
    for fid in sorted(films, key=lambda f: (0, int(f), "") if str(f).isdigit() else (1, 0, str(f))):
        m = movies.get(fid)
        if not m:
            continue
        # medium rather than small: small is 200 px wide and a poster on a 3x phone in a
        # two-column grid needs about 340 to stop looking soft, which is the same
        # complaint that started this work.
        url = m.get("poster_medium") or m.get("poster") or m.get("poster_small")
        if not url:
            failed.append((fid, "the API record carries no poster url"))
            continue
        # SOME RECORDS GIVE A PROTOCOL-RELATIVE URL and urllib answers "unknown url type"
        # rather than fetching it. Two of thirty-nine on the first run, and one of them was
        # Nolan's Odyssey -- the single most prominent film on the page. A browser would
        # have resolved it silently, which is exactly why this was invisible until a
        # non-browser client asked.
        if url.startswith("//"):
            url = "https:" + url
        dest = os.path.join(OUT, "%s.jpg" % fid)
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40)
            body = r.read()
        except Exception as e:
            failed.append((fid, "download failed: %s" % str(e)[:60]))
            continue
        tmp = dest + ".part"
        open(tmp, "wb").write(body)
        # DOWNSCALE. Cinemex serves 750x1125 at about 110 KB, and thirty-nine of those is
        # 4.1 MB -- for an app whose whole claim is that it opens instantly and works with
        # no signal, that is the wrong trade. The grid shows two posters across a 390 pt
        # phone, so each is about 170 pt, which is 510 device pixels on a 3x screen. 520
        # wide is therefore sharp with a little to spare and costs about a third as much.
        subprocess.run(["sips", "-Z", "520", "-s", "format", "jpeg",
                        "-s", "formatOptions", "78", tmp, "--out", tmp],
                       capture_output=True, timeout=60)
        ok, why = verify(tmp)
        if not ok:
            os.remove(tmp)
            failed.append((fid, why))
            continue
        os.replace(tmp, dest)
        got += 1
        manifest[fid] = {
            "w": jpeg_size(dest)[0], "h": jpeg_size(dest)[1],
            "url": "https:" + m["url"] if m.get("url", "").startswith("//") else m.get("url", ""),
            **film_meta(m),
        }
        print("  %-8s %-46s %s" % (fid, (m.get("name") or "")[:46], why))

    json.dump(manifest, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, sort_keys=True)

    print("\n%d posters written to docs/posters, %d failed" % (got, len(failed)))
    for fid, why in failed:
        print("  FAILED %-8s %s" % (fid, why))
    # A poster that is not a picture must not reach the page. Failing loudly here is the
    # difference between a missing image and a broken one, and Apple rejects the second.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
