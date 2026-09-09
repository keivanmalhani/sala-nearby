#!/opt/homebrew/bin/python3
"""Two jobs, chosen by argv[1].

  subset  reviews_raw.json places.json out.json  -- write the cinemas that came back
          under-sampled, so they can be scraped again
  merge   reviews_raw.json retry.json           -- keep whichever pass read more reviews

A cinema that Google says has thousands of reviews and that came back with 20 did not
have 20 reviews read; the pager stalled. Silently keeping that 20 would put a number in
the table that looks like every other number.
"""
import json, sys

MIN = 40


def main():
    mode = sys.argv[1]
    raw = json.load(open(sys.argv[2]))
    if mode == "subset":
        places = json.load(open(sys.argv[3]))
        thin = {str(r["id"]) for r in raw
                if len(r.get("sampled") or []) < MIN and (r.get("reviews") or 0) > 200}
        sub = [p for p in places if str(p["id"]) in thin]
        json.dump(sub, open(sys.argv[4], "w"), ensure_ascii=False, indent=1)
        print("%d cinemas came back under %d reviews with a big corpus behind them:"
              % (len(sub), MIN))
        for p in sub:
            print("   ", p["n"])
        return
    if mode == "merge":
        # Key on the cinema id, NOT the place id. Cinemex's Patriotismo Market and
        # Patriotismo Platino share one Google listing, so keying on place_id copied the
        # Platino record over the Market one, name and all, and the table then listed
        # Patriotismo Platino twice.
        retry = {str(r["id"]): r for r in json.load(open(sys.argv[3]))}
        kept = 0
        for i, r in enumerate(raw):
            q = retry.get(str(r["id"]))
            if q and len(q.get("sampled") or []) > len(r.get("sampled") or []):
                raw[i] = q
                kept += 1
                print("replaced %-34s %d -> %d reviews"
                      % (r["sala_name"], len(r.get("sampled") or []), len(q["sampled"])))
        json.dump(raw, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
        print("%d records improved" % kept)
        return
    sys.exit("mode must be subset or merge")


if __name__ == "__main__":
    main()
