#!/usr/bin/env python3
"""One film, one entry, across both chains.

The two chains publish the same film under their own ids, so the payload carried "La
Odisea" twice: 71948 from Cinemex with 264 showings across 25 cinemas, and ct-HO00009759
from Cineteca with 12 across two sedes. The Films tab listed it twice, and the film sheet
that says "N cinemas, nearest first" quietly left the Cineteca screenings out of both
copies. Cineteca also publishes its own dubbed and subtitled runs as two separate ids --
"Coyote Vs Acme DOB" and "Coyote Vs Acme SUB" -- which is the same defect inside one chain.

This runs over the payload after both refreshes have written it, folds those entries
together and repoints their showings at the surviving id. Every showing keeps its exact
date, time, cinema and ticket link; only the film id on it changes.

    /opt/homebrew/bin/python3 merge-films.py --dry-run
    /opt/homebrew/bin/python3 merge-films.py

refresh-cineteca.py calls merge() itself as its last step, so the ordinary refresh chain
does not need this run by hand. It is idempotent: a second run finds nothing.

WHY THE JOIN KEY IS TWO SIGNALS AND NOT ONE.

The obvious key is the original title, and on its own it is wrong in both directions.
Measured against the 9 September payload, 89 films:

  - It MISSES three of the seven real collisions. Cineteca writes the same original title
    three different ways for one film ("Coyote vs Acme", "Coyote vs. Acme", "Coyote VS
    Acme"), transliterates Arabic differently from Cinemex ("Illi Baqi Minnak" against
    "Allly baqi mink"), and differs in case on a Spanish-language film.
  - It INVENTS one that is not there. Five films carry an empty original title -- one
    Cinemex feature and four Cineteca shorts programmes -- and keying on it alone folds
    all five into one entry.

So the candidate has to come from either the folded original title OR the folded display
title, and then be corroborated before it is believed:

  - Duration within DUR_TOL minutes. The two Odyssey rows read 2h55m and 2h52m, so an
    exact match would refuse the very case this exists for; 40 minutes apart is a
    different film with the same name.
  - Director, when both sides name one. Cinemex truncates the field -- it holds
    "Christopher Nola" where Cineteca has "Christopher Nolan" -- so this is a prefix
    test, not an equality test, and it is skipped entirely when either side is blank
    rather than being treated as a mismatch.

Both corroborators can only ever REFUSE a merge. Neither can create one, which is the
direction that would silently collapse two real films into one row.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "docs", "index.html")

# Minutes of runtime the two chains may disagree by and still be the same film. The
# Odyssey is listed 2h55m by Cinemex and 2h52m by Cineteca; Sobre las Olas is 1h39m and
# 1h37m. Five is comfortably above both and far below any real collision.
DUR_TOL = 5

# A fold that puts more than this many films in one entry is not a merge, it is a bug in
# the fold. The largest real group is three (Coyote vs Acme: one Cinemex, two Cineteca).
MAX_GROUP = 4


def fold(s):
    """Lowercase ascii, punctuation collapsed to single spaces."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fold_dir(s):
    """Same, with Cineteca's trailing full stop taken off first."""
    return fold((s or "").strip().rstrip("."))


def minutes(d):
    """'2h55m' -> 175. '2h03m' -> 123. Anything unparseable -> None, which means the
    duration cannot refuse a merge rather than that it refuses every merge."""
    m = re.match(r"^\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*$", d or "")
    if not m or not (m.group(1) or m.group(2)):
        return None
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)


def same_film(a, b):
    """Would these two film entries be one row on a cinema listing."""
    oa, ob = fold(a.get("o")), fold(b.get("o"))
    na, nb = fold(a.get("n")), fold(b.get("n"))
    if not ((oa and oa == ob) or (na and na == nb)):
        return False
    da, db = minutes(a.get("d")), minutes(b.get("d"))
    if da is not None and db is not None and abs(da - db) > DUR_TOL:
        return False
    ra, rb = fold_dir(a.get("dir")), fold_dir(b.get("dir"))
    if ra and rb and not (ra == rb or ra.startswith(rb) or rb.startswith(ra)):
        return False
    return True


def is_cineteca(fid):
    return str(fid).startswith("ct-")


def _better_dir(a, b):
    """Cinemex truncates this field. Prefer the spelling that was not cut short."""
    a, b = (a or "").strip().rstrip("."), (b or "").strip().rstrip(".")
    if not b:
        return a
    if not a:
        return b
    return b if len(b) > len(a) else a


def _better_o(a, b):
    """Prefer a populated original title, and a cased one over a shouted one --
    'Teenage Sex and Death at Camp Miasma' over 'TEENAGE SEX AND DEATH AT CAMP MIASMA'."""
    a, b = (a or "").strip(), (b or "").strip()
    if not b:
        return a
    if not a:
        return b
    if a.isupper() and not b.isupper():
        return b
    return a


def groups(shows):
    """Every set of film ids that are one film. Singletons are not returned."""
    F = shows["films"]
    ids = list(F)
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if find(a) != find(b) and same_film(F[a], F[b]):
                parent[find(a)] = find(b)

    out = {}
    for i in ids:
        out.setdefault(find(i), []).append(i)
    return [g for g in out.values() if len(g) > 1]


def merge(shows):
    """Fold duplicate film entries together in place.

    Returns a list of (surviving_id, [absorbed ids], showings_now) for reporting, or
    raises ValueError if a control fails -- in which case nothing has been written,
    because everything up to the controls happens on the caller's dict only after they
    pass.
    """
    F = shows["films"]
    before_showings = sum(len(c["s"]) for c in shows["cin"])
    before_films = len(F)

    counts = {}
    for c in shows["cin"]:
        for s in c["s"]:
            counts[str(s[0])] = counts.get(str(s[0]), 0) + 1

    gs = groups(shows)
    for g in gs:
        if len(g) > MAX_GROUP:
            raise ValueError(
                "a group of %d films folded together, which is a loose fold rather than "
                "a merge: %s" % (len(g), ", ".join(F[i]["n"] for i in g)))

    remap, report = {}, []
    for g in gs:
        # THE SURVIVOR IS THE CINEMEX ID WHENEVER THERE IS ONE, and only then the entry
        # with the most showings. Posters and synopses are keyed by film id and are
        # fetched from Cinemex, so every ct- id has neither; sorting by showings first
        # looked more principled and silently dropped the poster from three of the eight
        # merges, because Cineteca happened to run those films more often that week.
        # Cinemex's display title is also the cased one -- "La Odisea", not "La odisea".
        # Its truncated director and shouted original title are handled field by field
        # below, so nothing is lost by taking it as the base.
        g = sorted(g, key=lambda i: (is_cineteca(i), -counts.get(str(i), 0), str(i)))
        base, rest = g[0], g[1:]
        f = F[base]
        for other in rest:
            o = F[other]
            f["dir"] = _better_dir(f.get("dir"), o.get("dir"))
            f["o"] = _better_o(f.get("o"), o.get("o"))
            if not (f.get("y") or "").strip():
                f["y"] = o.get("y", "")
            if not (f.get("r") or "").strip():
                f["r"] = o.get("r", "")
            if len(o.get("g") or []) > len(f.get("g") or []):
                f["g"] = o["g"]
            remap[str(other)] = base
        total = sum(counts.get(str(i), 0) for i in g)
        # c is what both lists sort films by, and it means "how many showings". It has to
        # mean that after the merge too, or the merged film sorts by its Cinemex half.
        f["c"] = total
        report.append((base, rest, total))

    if not remap:
        return report

    for c in shows["cin"]:
        for s in c["s"]:
            k = str(s[0])
            if k in remap:
                s[0] = remap[k]
    for old in remap:
        del F[old]

    # ---- the controls, on the result rather than on the intention ------------------
    after_showings = sum(len(c["s"]) for c in shows["cin"])
    problems = []
    if after_showings != before_showings:
        problems.append("the merge changed the showing count: %d -> %d"
                        % (before_showings, after_showings))
    if len(F) != before_films - len(remap):
        problems.append("the film table lost %d entries, not the %d that were absorbed"
                        % (before_films - len(F), len(remap)))
    orphan = {str(s[0]) for c in shows["cin"] for s in c["s"]} - {str(k) for k in F}
    if orphan:
        problems.append("%d showings now name a film that is not in the table, first %s"
                        % (len(orphan), sorted(orphan)[0]))
    dupes = _title_collisions(shows)
    if dupes:
        problems.append("%d titles are still duplicated after the merge, first %r"
                        % (len(dupes), sorted(dupes)[0]))
    if problems:
        raise ValueError("; ".join(problems))
    return report


# Cineteca marks the language in its own title -- "Coyote Vs Acme DOB", "Coyote Vs Acme
# SUB" -- and refresh-cineteca.py already splits that off into a format label. It files
# the label with an EMPTY type list, which is what the page filters on, so 30 Cineteca
# showings that say Subtitulada or Espanol on Cineteca's own site were invisible to the
# Subtitled chip. That is harmless while the chip is something he taps now and then and
# actively wrong the moment subtitled becomes a saved default, because the default would
# hide the screenings most likely to BE subtitled.
#
# "CINETECA" is deliberately not in this table. It is the label for a screening whose
# title carried no language suffix, so the language is genuinely unknown, and guessing
# subtitled because it is a repertory house is exactly the kind of assumption this app
# says "unknown" instead of making.
CINETECA_LANG = {"SUBTITULADA": "lang_sub", "ESPANOL": "lang_es"}


def tag_languages(shows):
    """Give Cineteca's language formats the type the page filters on. Returns the number
    of formats changed."""
    n = 0
    for f in shows["fmts"]:
        want = CINETECA_LANG.get(str(f.get("l", "")).strip().upper())
        if want and want not in (f.get("t") or []):
            f["t"] = list(f.get("t") or []) + [want]
            n += 1
    return n


def _title_collisions(shows):
    """Folded titles -- original where there is one, display otherwise -- held by more
    than one film entry. This is the property the whole file exists to establish, so it
    is also what the controls read back."""
    F = shows["films"]
    seen = {}
    for fid, f in F.items():
        for key in {fold(f.get("o")), fold(f.get("n"))}:
            if key:
                seen.setdefault(key, []).append(fid)
    return {k: v for k, v in seen.items() if len(v) > 1}


# ------------------------------------------------------------------ page in, page out

def read_page(path=PAGE):
    src = open(path, encoding="utf-8").read()
    m = re.search(r"^const SHOWS=", src, re.M)
    if not m:
        raise SystemExit("no `const SHOWS=` in %s" % path)
    shows, end = json.JSONDecoder().raw_decode(src, m.end())
    return src, shows, m.end(), end


def write_page(src, shows, i, j, path=PAGE):
    blob = json.dumps(shows, separators=(",", ":"), ensure_ascii=False)
    open(path, "w", encoding="utf-8").write(src[:i] + blob + src[j:])
    return len(src[:i]) + len(blob) + len(src[j:])


def chains_of(shows, fid):
    out = set()
    for c in shows["cin"]:
        if any(str(s[0]) == str(fid) for s in c["s"]):
            out.add("cineteca" if str(c["id"]).startswith("cineteca-") else "cinemex")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would fold together and write nothing")
    ap.add_argument("--page", default=PAGE)
    a = ap.parse_args()

    src, shows, i, j = read_page(a.page)
    before = sum(len(c["s"]) for c in shows["cin"])
    n_films = len(shows["films"])
    try:
        report = merge(shows)
    except ValueError as e:
        print("REFUSING: %s" % e)
        return 1
    tagged = tag_languages(shows)
    if tagged:
        print("  %d Cineteca language formats can now be filtered on" % tagged)

    if not report and not tagged:
        print("nothing to merge: %d films, %d showings, no title held twice"
              % (n_films, before))
        return 0

    for base, rest, total in report:
        f = shows["films"][base]
        print("  %-46s %s" % (f["n"][:46], " + ".join([str(base)] + [str(r) for r in rest])))
        print("     %d showings, %s" % (total, " and ".join(sorted(chains_of(shows, base)))))
    if report:
        print("%d films folded into %d, %d showings unchanged"
              % (n_films, len(shows["films"]), sum(len(c["s"]) for c in shows["cin"])))

    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    n = write_page(src, shows, i, j, a.page)
    print("wrote %s: %s bytes" % (a.page, format(n, ",")))
    print("NEXT: bump the cache name in docs/sw.js, or a phone with the app installed "
          "keeps serving the old build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
