#!/opt/homebrew/bin/python3
"""Render the review analysis as the markdown report and the app-facing JSON."""
import json, sys, datetime

STAMP = "2026-09-09"

HEAD = """# What it is actually like inside: ratings, complaints and temperature

Google Maps reviews for every cinema Sala Nearby lists showtimes for, read on %s.
Every rating, review count and quote below came out of a page that was actually loaded;
nothing here is remembered or inferred.

**Reviews were reachable.** They are read from the rendered Google Maps place page in
Keivan's own Chrome over CDP on 127.0.0.1:9222, in a background tab that is closed
afterwards. Two cheaper routes were tried first and are written up under Method, because
both fail in ways that look like success.

Regenerate with:

    /opt/homebrew/bin/python3 tools/find-places.py <cinemas.json> docs/places.json
    TARGET=100 node tools/scrape-reviews.mjs docs/places.json /tmp/reviews_raw.json
    /opt/homebrew/bin/python3 tools/analyze-reviews.py /tmp/reviews_raw.json docs/cinema-reviews.json
    /opt/homebrew/bin/python3 tools/write-report.py docs/cinema-reviews.json docs/CINEMA-REVIEWS-%s.md

## The short answer on temperature

%s

## Every cinema

Rating and review count are Google's own, read off the place header. "Sample" is how many
distinct reviews were loaded and read for that cinema -- Maps pages them in twenties and
renders each one twice, so the number is what survived de-duplication. Cold and hot are
counts of reviews in that sample whose text complains about the room's temperature.

| Cinema | km | Rating | Reviews | Sample | Cold | Hot | Verdict | Top complaints and praise |
|---|---:|---:|---:|---:|---:|---:|---|---|
"""

METHOD = """
## Method, and the two routes that do not work

**What was tried, in order.**

1. **Plain HTTP to Google Maps.** `www.google.com/maps/place/...`
   answers **200** and 208 KB, and the body is a JavaScript shell: no rating, no review
   count, no review text, and no place id. Searching that HTML for a rating finds nothing.
   A 200 here is not a refusal, which is exactly why it is worth writing down -- the page
   arrived, it just does not contain the answer.
2. **The `tbm=map` endpoint the Maps frontend itself calls.** This one works over plain
   HTTP and is what `find-places.py` uses. It answers **200** with a JSON array carrying
   the place's name, coordinates, feature id, place id and star rating. It does **not**
   reliably carry the review count, and it carries no review text at all. All 39 venues
   resolved to a place id this way, and this endpoint does answer plain `curl`.
3. **`/maps/rpc/listugcposts`, the reviews RPC.** **403 Forbidden** to a hand-built `pb`
   parameter, and still 403 when called from inside a logged-in Google Maps tab with
   `credentials: 'include'`. `/maps/preview/review/listentitiesreviews`, the older
   endpoint, answers **404**. Watching the network while a place's reviews loaded captured
   **zero** matching requests, because Maps ships the first page of reviews inside the
   document rather than fetching it.
4. **The rendered review pane in his Chrome.** This works, and it is what the numbers
   here come from.

**One thing measured rather than assumed:** the `tbm=map` endpoint does not care which TLS
stack asks. `/opt/homebrew/bin/python3` (OpenSSL 3.6.3), `/usr/bin/python3` (LibreSSL
2.8.3) and macOS `curl` all answer **200** with an identical 32,715-byte body. The
fingerprinting wall that blocks the system stack on some other sites is simply not present
here, and an earlier draft of this file asserted that it was.

**Four defects found and fixed while building the scrape**, each of which produced a
plausible-looking wrong answer:

- **Setting `scrollTop` loads exactly 20 reviews and then stops.** Maps' loader listens
  for a scroll *event*, so the event has to be dispatched by hand. Without that, every
  cinema would have reported a 20-review sample and looked consistent.
- **Every review renders twice.** 20 `data-review-id` nodes are 10 reviews. Counting
  nodes doubles every sample size and every keyword tally at once, so the ratios stay
  believable while every absolute number is wrong.
- **Eight cinemas rendered no review card at all, and their pages were perfectly fine.**
  Google's newer reviews layout shows the star histogram and its own written summary
  first and loads not one review until something scrolls. Every pane-finder here starts
  from a review card, so with zero cards there was nothing to start from -- and the record
  was written out with a sample of 0 and no error against it. Cineteca Nacional in Xoco,
  the most-reviewed venue in the whole app at 63,587 reviews, was one of the eight.
  Scrolling every tall overflowing container instead of starting from a card recovered
  all ten that had come back thin, on the first attempt.
- **Long reviews arrive folded at "... Mas".** 30 of the first 80 were cut off, and the
  temperature complaint is usually in the second half of a review, after the plot summary.
  The expander is a button whose accessible name is exactly "Ver mas", and clicking
  re-renders the card, so it takes several passes.

**How a temperature mention is counted.** Sentence by sentence, over accent-stripped
text. The rules below were not written in advance -- each one was added after reading
every sentence the classifier had flagged and finding a wrong one:

- **`palomitas frias` is cold popcorn, not a cold room.** It is the single most common
  "frio" in a Mexican cinema review -- 16 of them in the first 1,271 reviews, against 8
  genuine cold complaints. A sentence-level food filter is not enough: the sentence that
  defeated the first version was *"llegamos a las 11:30 am y palomitas frias"*, which also
  contains the word "funcion". So the check asks which noun the cold word is attached to,
  three tokens either side, and only falls back to the whole sentence when that window is
  inconclusive -- which is what catches *"por fuera estan calientes y por dentro frios"*.
- **`sin aire acondicionado` is a HEAT complaint** even though it contains the phrase
  "aire acondicionado". Counting that phrase as a cold signal, which is the obvious thing
  to do, gets the sign backwards on exactly the cinemas where the cooling is broken.
- **`lleven chamarra` never uses the word cold and is the strongest cold signal there is**,
  because the reviewer is giving advice. But a jacket only counts when advice is actually
  being given: *"se llevaron mi sueter"* is a theft and *"revision a las mochilas o bolsas
  o chamarras"* is a bag search, and both read as cold complaints until the rule was
  narrowed. The verb forms have to end at a word boundary, because `\bllev a` also matches
  "llevaron" -- which is how a robbery became a temperature reading.
- **`sin frio en exceso` is praise.** A negation immediately before the cold word flips
  its meaning, and that sentence was being counted against the one cinema doing it right.
- **`muros frios` is about the decor**, and `helado` is ice cream far more often than it
  is a freezing sala.

**The precision was measured, not assumed.** Every sentence the classifier flagged across
all 3,267 reviews was read by hand, four times, and each pass found wrong ones that the
previous rules had let through -- 11 of the first 16 "cold" hits were false. What survives
is 12 cold sentences, all of them genuine, and 63 heat sentences of which two are still
misreads: one is a wood-fired pizza oven and one complains about heat in the ticket hall
while saying the auditorium itself was fine. So call it about 3% error on the heat side and
none found on the cold side. The food-cold pile that was excluded is **46 reviews**, which
is nearly four times the number of real cold complaints -- that filter is not a nicety,
it is most of the work.

`analyze-reviews.py` opens with a control: 33 sentences that must classify into four
different verdicts, and every one of them is a real sentence out of these reviews that was
once classified wrongly. It exits non-zero if they collapse, because a classifier that answers the same
thing to every input produces a full, orderly, worthless table.

**What these numbers are not.** The sample is Google's "most relevant" ordering, not a
random draw, and it is roughly 100 reviews out of a corpus that runs to several thousand
at the busy sites. Ratios between cinemas are comparable because every cinema was read the
same way. An absolute rate like "4%% of visitors were cold" is not supported.
"""


def bar(r):
    t = r["temperature"]
    v = t["verdict"]
    return {"cold": "COLD", "hot": "HOT", "mixed": "mixed", "thin": "thin evidence",
            "no signal": "no signal"}.get(v, v)


def main():
    data = json.load(open(sys.argv[1]))
    ok = [r for r in data if r["ok"]]
    cold = [r for r in ok if r["temperature"]["verdict"] == "cold"]
    hot = [r for r in ok if r["temperature"]["verdict"] == "hot"]
    mixed = [r for r in ok if r["temperature"]["verdict"] == "mixed"]
    thin = [r for r in ok if r["temperature"]["verdict"] in ("thin", "no signal")]
    tot_reviews = sum(r["sampled"] for r in ok)
    tot_cold = sum(r["temperature"]["cold_mentions"] for r in ok)
    tot_hot = sum(r["temperature"]["heat_mentions"] for r in ok)
    tot_food = sum(r["temperature"]["food_cold_excluded"] for r in ok)

    def pl(n, one, many=None):
        return "%d %s" % (n, one if n == 1 else (many or one + "s"))

    # The framing is computed, not written in advance. An earlier draft asserted that the
    # freezing-cinema reputation was half right before any cinema had been read, which is
    # a conclusion wearing a summary's clothes.
    if tot_hot > 2 * max(tot_cold, 1):
        lede = ("**The freezing-cinema reputation does not survive the reviews.** People "
                "complain about these rooms being too WARM about %.0f times as often as too "
                "cold. What they are describing is air conditioning that is off, broken, or "
                "losing to the afternoon -- not a cinema kept at meat-locker temperature."
                % (tot_hot / max(tot_cold, 1)))
    elif tot_cold > 2 * max(tot_hot, 1):
        lede = ("**The freezing-cinema reputation holds.** Cold complaints outnumber heat "
                "complaints about %.0f to one, so a jacket is the right default." 
                % (tot_cold / max(tot_hot, 1)))
    else:
        lede = ("**It cuts both ways.** Cold and heat complaints are within a factor of two "
                "of each other, so there is no city-wide default and the per-cinema column "
                "below is the whole answer.")

    summary = (
"Across %s and %s read, temperature comes up in %s: %s complaining the room was cold, %s "
"complaining it was hot or that the cooling was off. A further %s say something was cold "
"and mean the popcorn.\n\n%s\n\n"
"Cinema by cinema: %s read cold, %s read hot, %s genuinely mixed, and %s have too few "
"temperature mentions in a hundred reviews to call either way.\n\n"
"**And the honest caveat, which matters more than the ranking:** those %d temperature "
"mentions are %.1f%% of the %d reviews read. Temperature is simply not what people write "
"about at these cinemas -- staff, seats and cleanliness are, by an order of magnitude. "
"%s enough heat complaints to be worth a warning and %s enough cold ones. For the other "
"%d there is no honest reading, and a per-cinema temperature badge on all 39 would be "
"inventing a signal for most of them."
        % (pl(len(ok), "cinema"), pl(tot_reviews, "review"),
           pl(tot_cold + tot_hot, "review"), pl(tot_cold, "review"), pl(tot_hot, "review"),
           pl(tot_food, "review"), lede,
           pl(len(cold), "cinema"), pl(len(hot), "cinema"),
           pl(len(mixed), "cinema"), pl(len(thin), "cinema"),
           tot_cold + tot_hot, 100.0 * (tot_cold + tot_hot) / max(tot_reviews, 1),
           tot_reviews,
           ("%s has" if len(hot) == 1 else "%s have") % pl(len(hot), "cinema"),
           ("%s has" if len(cold) == 1 else "%s have") % pl(len(cold), "cinema"),
           len(thin) + len(mixed)))

    # Two things would otherwise be read as facts about a cinema when they are facts
    # about its Google listing.
    shared = {}
    for r in data:
        shared.setdefault(r["place_id"], []).append(r["sala_name"])
    dupes = {k: v for k, v in shared.items() if len(v) > 1}

    rows = []
    for r in sorted(ok, key=lambda x: (x["km"] if x["km"] is not None else 99)):
        t = r["temperature"]
        flags = []
        if (r["review_count"] or 0) < 100:
            flags.append("thin listing")
        if r["place_id"] in dupes:
            flags.append("shares a listing")
        themes = ", ".join("%s (%d%%)" % (th["theme"], round(th["pct"]))
                           for th in r["themes"][:3]) or "-"
        rows.append("| %s%s | %s | %s | %s | %d | %d | %d | %s | %s |" % (
            r["sala_name"], (" *(%s)*" % ", ".join(flags)) if flags else "",
            ("%.1f" % r["km"]) if r["km"] is not None else "-",
            ("%.1f" % r["rating"]) if r["rating"] is not None else "-",
            "{:,}".format(r["review_count"]) if r["review_count"] else "-",
            r["sampled"], t["cold_mentions"], t["heat_mentions"], bar(r), themes))

    out = [HEAD % (STAMP, STAMP, summary) + "\n".join(rows)]

    notes = []
    thin_listing = [r for r in ok if (r["review_count"] or 0) < 100]
    if thin_listing:
        one = len(thin_listing) == 1
        notes.append("**%s fewer than 100 Google reviews**, so %s star rating is "
                     "not comparable to the four-figure listings beside it: %s. Searching "
                     "those addresses returns one busy listing each, and these are separate "
                     "near-empty pins for the same building."
                     % ("One cinema carries" if one else "%d cinemas carry" % len(thin_listing),
                        "its" if one else "their",
                        "; ".join("%s (%s stars from %d reviews)"
                                  % (r["sala_name"], r["rating"], r["review_count"] or 0)
                                  for r in thin_listing)))
    if dupes:
        notes.append("**Google has one listing where Sala Nearby has two.** %s. The rating, "
                     "the review count and the temperature reading are therefore the same "
                     "number reported twice, not two independent measurements."
                     % "; ".join("%s share one place id" % " and ".join(v) for v in dupes.values()))
    if notes:
        out.append("\n" + "\n\n".join(notes))

    failed = [r for r in data if not r["ok"]]
    if failed:
        out.append("\n**%d cinemas returned nothing** and are not in the table above: %s"
                   % (len(failed), "; ".join("%s (%s)" % (r["sala_name"], r.get("error"))
                                             for r in failed)))

    out.append("\n## Per cinema, with the evidence\n")
    for r in sorted(ok, key=lambda x: -(x["temperature"]["cold_mentions"]
                                        + x["temperature"]["heat_mentions"])):
        t = r["temperature"]
        out.append("### %s\n" % r["sala_name"])
        out.append("%s star%s from %s reviews on Google. %d reviews read for this write-up. "
                   "Google's own name for it is \"%s\".\n" % (
                       "%.1f" % r["rating"] if r["rating"] else "an unpublished", "s",
                       "{:,}".format(r["review_count"]) if r["review_count"] else "an unpublished number of",
                       r["sampled"], r["name"]))
        out.append("- **Temperature: %s.** %d of %d reviews read call the room cold, %d call "
                   "it hot or say the air conditioning was off%s."
                   % (bar(r), t["cold_mentions"], r["sampled"], t["heat_mentions"],
                      ", and %d more say the food was cold" % t["food_cold_excluded"]
                      if t["food_cold_excluded"] else ""))
        raw = t.get("raw_token_counts") or {}
        if raw:
            out.append("- Unfiltered word counts in the same sample: %s."
                       % ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in raw.items()))
        if r["themes"]:
            out.append("- **What people write about:** %s."
                       % "; ".join("%s in %d of %d" % (th["theme"], th["reviews_mentioning"], r["sampled"])
                                   for th in r["themes"][:5]))
        if r.get("google_summary"):
            out.append("- **Google's own summary of its whole review corpus** (not of the "
                       "sample above): \"%s\"" % r["google_summary"])
        if r["star_split"]:
            out.append("- Stars in the sample: %s."
                       % ", ".join("%s*: %d" % (k, v) for k, v in sorted(r["star_split"].items(), reverse=True)))
        for e in t["evidence_cold"]:
            out.append("- Cold, %s stars%s: \"%s\"" % (e["stars"], " %s" % e["when"] if e["when"] else "", e["quote"]))
        for e in t["evidence_hot"]:
            out.append("- Hot, %s stars%s: \"%s\"" % (e["stars"], " %s" % e["when"] if e["when"] else "", e["quote"]))
        out.append("- [Google Maps place](%s)\n" % r["maps_url"])

    out.append(METHOD)
    open(sys.argv[2], "w").write("\n".join(out) + "\n")
    print("wrote %s (%d cinemas, %d reviews)" % (sys.argv[2], len(ok), tot_reviews))


if __name__ == "__main__":
    main()
