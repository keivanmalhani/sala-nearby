#!/opt/homebrew/bin/python3
import os
"""Guard docs/cinema-reviews.json against the page it is meant to be read by.

The app renders a cinema through cinemaSheet(cid), which looks a cinema up by the `id`
in SHOWS.cin. If the ids in this file do not match those, the file loads fine, parses
fine, and joins to nothing -- which looks exactly like a cinema having no reviews.
"""
import json, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "docs", "index.html")
REVIEWS = os.path.join(ROOT, "docs", "cinema-reviews.json")

fails = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (("  -- " + detail) if detail else ""))
    if not ok:
        fails.append(name)


def main():
    page = open(PAGE, encoding="utf-8").read()
    ids = set(re.findall(r'\{"id":("?[\w\-]+"?),"n":"[^"]+","lat":', page))
    ids = {i.strip('"') for i in ids}
    revs = json.load(open(REVIEWS))
    rids = {str(r["id"]) for r in revs}

    check("the page still exposes a cinema list", len(ids) > 20, "%d ids in SHOWS.cin" % len(ids))
    missing = ids - rids
    check("every cinema on the page has a review record", not missing,
          "no record for: %s" % sorted(missing)[:6])
    # indie-* records are the four independent cinemas that are on the MAP but carry no
    # showtimes, so they are keyed to the venue list V rather than to SHOWS.cin. They are
    # deliberate, not orphans -- but they still have to name a venue the map actually has.
    orphan = {i for i in rids - ids if not i.startswith("indie-")}
    check("no review record points at a cinema the page dropped", not orphan,
          "orphans: %s" % sorted(orphan)[:6])

    # Join on the map's own spelling, carried in map_venue. Matching on sala_name would
    # have missed "Cine Tonala" and "Cinematografo del Chopo", which the map writes
    # without accents -- a miss that looks exactly like a venue having no reviews.
    vnames = set(re.findall(r'\{name:"([^"]+)",op:', page))
    indie = [r for r in revs if str(r["id"]).startswith("indie-")]
    unmatched = [r["sala_name"] for r in indie if r.get("map_venue") not in vnames]
    check("every indie record joins to a map venue by exact name", not unmatched,
          "not on the map: %s" % unmatched)

    rated = [r for r in revs if r.get("rating")]
    check("every record carries a rating", len(rated) == len(revs),
          "%d of %d" % (len(rated), len(revs)))
    sampled = [r for r in revs if r.get("sampled", 0) >= 40]
    check("at least 30 cinemas were read deeply", len(sampled) >= 30,
          "%d records have 40+ reviews read" % len(sampled))

    verdicts = {r["temperature"]["verdict"] for r in revs}
    # The control that matters: if every cinema came out with the same verdict, the
    # classifier is not discriminating and the column is decoration.
    check("the temperature verdict is not one value for every cinema", len(verdicts) > 1,
          "verdicts present: %s" % sorted(verdicts))

    quoted = [r for r in revs
              if r["temperature"]["evidence_cold"] or r["temperature"]["evidence_hot"]]
    check("temperature verdicts carry quotable evidence", len(quoted) >= 8,
          "%d records have at least one quote" % len(quoted))

    themed = [r for r in revs if len(r.get("themes") or []) >= 3]
    check("themes were extracted for most cinemas", len(themed) >= 30,
          "%d records have 3+ themes" % len(themed))

    print("\n%d checks, %d failed" % (8, len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
