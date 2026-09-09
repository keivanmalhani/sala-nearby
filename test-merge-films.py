#!/usr/bin/env python3
"""Controls for merge-films.py.

    /opt/homebrew/bin/python3 test-merge-films.py
    /opt/homebrew/bin/python3 test-merge-films.py --page /some/other/index.html

Three properties, and each one is required to GO RED before it is allowed to go green.
The red half is not decoration: this file was run against the unfixed page first, where
sections 1 and 2 failed on seven duplicated titles and on zero films reachable in both
chains, and only then against the fixed one.

The red half is kept forever by section 1, which takes the live payload and pulls one
merged film back apart into the two entries the chains published. That is the exact state
the merge exists to remove, built from real data rather than described, so the controls
cannot quietly become tautologies the day the payload changes.
"""
import argparse
import copy
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("merge_films",
                                              os.path.join(HERE, "merge-films.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- the three properties

def prop_no_duplicate_titles(shows):
    """No two film entries are the same film."""
    return not M._title_collisions(shows)


def prop_showings(shows):
    return sum(len(c["s"]) for c in shows["cin"])


def films_in_both_chains(shows):
    """Films whose showings span a Cinemex cinema and a Cineteca sede. Before the merge
    this is zero by construction, because the two chains never share a film id."""
    out = []
    for fid in shows["films"]:
        if len(M.chains_of(shows, fid)) > 1:
            out.append(fid)
    return out


def split_one(shows):
    """Take a merged cross-chain film and put it back the way the chains publish it: the
    Cineteca showings moved onto their own film entry, with Cineteca's own spellings.
    Returns None if there is no such film to split."""
    both = films_in_both_chains(shows)
    if not both:
        return None
    fid = max(both, key=lambda f: sum(1 for c in shows["cin"] for s in c["s"]
                                      if str(s[0]) == str(f)))
    out = copy.deepcopy(shows)
    twin = "ct-SPLIT-CONTROL"
    src = out["films"][str(fid)]
    out["films"][twin] = {"n": src["n"].lower(), "d": src["d"], "r": "", "g": [],
                          "o": src.get("o", ""), "dir": (src.get("dir") or "") + ".",
                          "y": src.get("y", "")}
    moved = 0
    for c in out["cin"]:
        if not str(c["id"]).startswith("cineteca-"):
            continue
        for s in c["s"]:
            if str(s[0]) == str(fid):
                s[0] = twin
                moved += 1
    return (out, fid, twin, moved) if moved else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=M.PAGE)
    a = ap.parse_args()
    _, live, _, _ = M.read_page(a.page)

    # This section is FIRST and runs unconditionally, because it is the one that went red
    # on the unfixed page: 12 duplicated title keys covering 8 films, and not one film
    # reachable in both chains.
    print("section 1 -- the published page")
    col = M._title_collisions(live)
    if col:
        print("  (%d duplicated title keys: %s)" % (len(col), ", ".join(sorted(col)[:6])))
    check("no two film entries share a title, original or displayed",
          prop_no_duplicate_titles(live))
    both = films_in_both_chains(live)
    print("  (%d films are reachable in both chains, %d showings in the payload)"
          % (len(both), prop_showings(live)))
    check("at least one film's cinema list holds a venue from each chain", len(both) >= 1)
    again = copy.deepcopy(live)
    n = prop_showings(again)
    check("running the merge again finds nothing -- it is idempotent",
          M.merge(again) == [] and prop_showings(again) == n)

    print("\nsection 2 -- the controls go red on a payload that is not merged")
    sp = split_one(live)
    if sp is None:
        check("there is a cross-chain film in the payload to pull apart, so the red half "
              "of these controls can run at all", False)
        print("\n%d FAILED" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    broken, fid, twin, moved = sp
    print("  (split %r back into %s + %s, %d showings moved)"
          % (live["films"][str(fid)]["n"], fid, twin, moved))
    check("a payload with the film published twice FAILS the duplicate-title check",
          not prop_no_duplicate_titles(broken))
    check("and FAILS 'every showing of a film is reachable from one entry' -- the twin "
          "is in one chain only",
          len(M.chains_of(broken, twin)) == 1 and len(M.chains_of(broken, fid)) == 1)

    print("\nsection 3 -- merging that payload fixes it, and loses nothing")
    n_before = prop_showings(broken)
    fixed = copy.deepcopy(broken)
    report = M.merge(fixed)
    check("the merge finds it", any(twin in [str(r) for r in rest] for _, rest, _ in report))
    check("the showing count is unchanged: %d" % n_before, prop_showings(fixed) == n_before)
    check("every title is now held by exactly one film entry",
          prop_no_duplicate_titles(fixed))
    check("the film it was folded into is reachable in both chains",
          len(M.chains_of(fixed, fid)) == 2)
    check("no showing points at a film that is gone",
          {str(s[0]) for c in fixed["cin"] for s in c["s"]} <= {str(k) for k in fixed["films"]})
    # Every showing has to survive with its date, time, cinema and ticket link intact --
    # only the film id on it may change. Compare the two payloads on everything else.
    def rows(sh):
        # str() on the cinema id, because Cinemex ids decode as ints and Cineteca's are
        # strings, and sorting the mixture raises rather than comparing.
        return sorted((str(c["id"]), s[1], s[2], s[3], str(s[4]), str(s[5]),
                       str(s[6]) if len(s) > 6 else "")
                      for c in sh["cin"] for s in c["s"])
    check("every showing kept its exact cinema, day, time, availability, ticket id "
          "and room", rows(fixed) == rows(broken))

    print("\nsection 4 -- the join key refuses what it should refuse")
    blank = [f for f in live["films"].values() if not (f.get("o") or "").strip()]
    print("  (%d films carry no original title)" % len(blank))
    check("two films with no original title and different names are NOT one film",
          len(blank) < 2 or not M.same_film(blank[0], blank[1]))
    check("same name, 40 minutes apart, is NOT one film",
          not M.same_film({"n": "La Odisea", "o": "The Odyssey", "d": "2h55m", "dir": ""},
                          {"n": "La Odisea", "o": "The Odyssey", "d": "1h30m", "dir": ""}))
    check("same name, different director, is NOT one film",
          not M.same_film({"n": "Sobre las Olas", "o": "", "d": "1h39m", "dir": "Horacio Alcala"},
                          {"n": "Sobre las olas", "o": "", "d": "1h37m", "dir": "Ismael Rodriguez"}))
    check("a truncated director IS the same director -- Cinemex writes 'Christopher Nola'",
          M.same_film({"n": "La Odisea", "o": "The Odyssey", "d": "2h55m", "dir": "Christopher Nola"},
                      {"n": "La odisea", "o": "The Odyssey", "d": "2h52m", "dir": "Christopher Nolan"}))
    check("a differently-spelled original title still joins on the name",
          M.same_film({"n": "Lo que queda de ti", "o": "Illi Baqi Minnak", "d": "2h25m", "dir": "Cherien Dabis"},
                      {"n": "Lo que queda de ti", "o": "Allly baqi mink", "d": "2h25m", "dir": "Cherien Dabis."}))
    check("a differently-worded name still joins on the original title",
          M.same_film({"n": "La Isla de Azucar", "o": "Sugar Island", "d": "1h30m", "dir": "Johanne Gomez Terrero"},
                      {"n": "Sugar Island, La isla de azucar", "o": "Sugar Island", "d": "1h31m", "dir": "Johanne Gomez Terrero"}))

    print("\nsection 5 -- Cineteca's own language labels can be filtered on")
    def n_typed(sh, t):
        c = 0
        for cin in sh["cin"]:
            for s in cin["s"]:
                if t in (sh["fmts"][s[1]].get("t") or []):
                    c += 1
        return c
    stripped = copy.deepcopy(live)
    for f in stripped["fmts"]:
        if str(f.get("l", "")).strip().upper() in M.CINETECA_LANG:
            f["t"] = []
    sub_before, sub_after = n_typed(stripped, "lang_sub"), n_typed(live, "lang_sub")
    print("  (subtitled showings: %d untagged, %d tagged)" % (sub_before, sub_after))
    check("an untagged payload hides Cineteca's subtitled screenings from the chip",
          sub_after > sub_before)
    check("tagging it recovers exactly those", M.tag_languages(stripped) > 0
          and n_typed(stripped, "lang_sub") == sub_after)
    check("the published page is already tagged", M.tag_languages(copy.deepcopy(live)) == 0)
    # An empty type list and lang_unknown are the same fact, and they behave identically
    # right up to the moment subtitled is a saved default -- at which point the empty one
    # hides 167 of Cineteca's 185 screenings. So the control is that the unknown is
    # EXPLICIT, not that it is absent.
    unk = [f for f in live["fmts"]
           if str(f.get("l", "")).strip().upper() == "CINETECA"]
    check("a screening whose title carried no language suffix is marked unknown, not "
          "left untyped", bool(unk) and all(f.get("t") == ["lang_unknown"] for f in unk))
    check("and it is not quietly recorded as subtitled",
          all("lang_sub" not in (f.get("t") or []) for f in unk))
    # The rule the page filters on is `lang_unknown`, not "no language recorded". Those
    # differ the day a Cinemex format arrives untagged, and then the second one would put
    # dubbed showings under the Subtitled chip.
    def cinemex_untyped(sh):
        n = 0
        for c in sh["cin"]:
            if str(c["id"]).startswith("cineteca-"):
                continue
            for s in c["s"]:
                if not (set(sh["fmts"][s[1]].get("t") or []) & {"lang_sub", "lang_es"}):
                    n += 1
        return n
    check("no Cinemex showing carries an unknown language, so widening the Subtitled "
          "chip cannot let a dubbed one in", cinemex_untyped(live) == 0)
    check("lang_unknown is only ever on a Cineteca format",
          all(str(f.get("l", "")).strip().upper() in M.CINETECA_LANG
              for f in live["fmts"] if "lang_unknown" in (f.get("t") or [])))
    n_unk = sum(1 for c in live["cin"] for s in c["s"]
                if "lang_unknown" in (live["fmts"][s[1]].get("t") or []))
    print("  (%d showings say 'language unknown' rather than nothing)" % n_unk)
    check("there are some, or this whole section is about a case that does not occur",
          n_unk > 0)

    print()
    if fails:
        print("%d FAILED" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("all controls pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
