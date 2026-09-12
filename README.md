# Sala Nearby

Every cinema within walking distance of Parque Mexico, with real showtimes, as an app you
install from the browser rather than from a store.

**https://keivanmalhani.github.io/sala-nearby/**

Open it on a phone, tap Share, then Add to Home Screen. It gets its own icon, opens full
screen with no browser bars, and works with no signal after the first launch.

## What it does

- **Showtimes** for 35 venues within 9 km, filterable by day and by any combination of
  "starting soon", subtitled-not-dubbed, IMAX, Atmos and Platino. The chips stack, so
  "subtitled IMAX" is a thing you can ask for, and the combination is remembered between
  launches -- on the 11 September pull it is 6,999 dubbed showings against 3,442 subtitled,
  and the ratio has held at roughly two to one on every pull so far, so the default in this
  city is against you and re-tapping it every time was the wrong
  shape. "Starting soon" is deliberately not remembered. Every time links straight to the
  cinema's own checkout, which is always current even when the listing here is not.
- **Map** of 42 venues, coloured by what kind of room they are, with walking distance from
  wherever you are. Tapping one opens its full write-up and a walking-directions link.
  Fifteen of them cost nothing, and the map says so: those dots are gold, and the pill in
  the corner opens the list of them, nearest first. It is also the only caption the map
  has had since the legend came off -- it explains one colour rather than four.
- **Coming up.** Twenty of the eighty films in the current payload are not on today at
  all, and the only way to find them was to tap along thirty date chips. The Films tab
  now ends with them, in date order, with their dates spelled out where there are one or
  two: PULP on Thursday 24 September at eight cinemas, Queen: Budapest on 7 and 10
  October, Always Lalisa on the 12th and 14th. Tapping one moves the whole app to that
  day. A film in its last day carries a badge saying so, and that badge means something
  -- see below.
- **Films** index. There was a fourth tab, a Guide carrying the venue audit, and it was
  removed on 8 September on his own instruction -- "i dont like the guide tab to begin w".
  The audit did not go with it: the screen sizes, the projection, the sound and the note
  saying which of those was verified rather than assumed all live on each cinema's own
  sheet now, which is where somebody is actually asking the question.
- **The day rail starts today.** The showtimes are a snapshot baked into the page, and the
  page is opened on later days than the one it was built on. Until 11 September the rail led
  with whatever day the payload was pulled on, so a two-day-old build put two days that were
  over ahead of Today, and tapping one listed showtimes that had already finished with
  nothing on the row to say so. It offers days that have not been and gone now, and opens on
  the first of them. If the whole payload is in the past it hands back the full list rather
  than an empty rail, because an empty rail says less than a stale one.
- **It says when its own listing has run out.** The rail dropping past days covers a page
  that is a few days old. A page that is months old has nothing left to offer, so the rail
  hands back the full list and every time on the screen has already happened. On the day
  after the last date the payload holds, both lists carry one sentence saying so, naming
  that date and saying that tapping a time still opens the cinema's own page, which is
  live. It does not appear a day early -- the last day is a day he can still buy a ticket
  for -- and it is not on the map, because the venues do not go stale with the showtimes.
- **Find a film by its director or its genre.** The search box read the title and the
  original title only, so "nolan" returned nothing while La Odisea played at twenty-five
  cinemas and "terror" returned nothing on a board carrying four horror films. Cinemex
  truncates director names at a fixed width -- their pull says "Christopher Nola" -- and
  `director-truncation.py` restores the longer spelling this project already published,
  which is the only repair it makes. One field is still cut off mid-word at the source and
  is left that way rather than filled in with a name nobody read.
- **Whether there is a bar.** Seven of the forty-two venues serve a drink and the audit
  already said so in prose that nothing on screen could reach. There is no snack or drink
  menu to be had -- `candybar` is false on all seventy CDMX Cinemex sites and their own
  dulceria page is a 404 -- so this is the only part of that request the data supports. The
  classification is a local model reading the write-ups, and every answer had to come back
  with a verbatim quote that gets checked against the source before it ships: `bar.py` and
  `test-bar.py`. A venue with no Drinks row is one whose audit does not mention a drink,
  which is a weaker claim than "no bar", and the page does not make the stronger one.
- **Star a film.** Every film's sheet has a Star button, starred films sit at the top of
  both lists with a small star, and a Starred chip stacks with the others. The stars are
  saved on the phone; the chip is not, for the same reason Starting soon is not -- it is
  a way of looking, and restoring it would open the app with most of the films hidden.
- **Walkable.** A chip that keeps only the cinemas whose own row says "min walk": up to
  forty minutes at 4.5 km/h, about three kilometres, which is the line the rows have
  always used to switch to a drive time. Nobody has measured how far is too far, so it
  does not invent a new number, and the rows and the chip share one function so they
  cannot disagree. It measures from wherever the distances do, so it follows the
  location button, and like Starting soon it is not remembered between launches.
- **Cast, country and trailer.** A film's sheet says where it is from, when, and who is
  in it, and has a Trailer button beside Walk to that opens YouTube rather than embedding
  a player, so the app still works with no signal. Cinemex sends these for almost every
  film; Cineteca sends none, and its sheets show nothing rather than an empty line.
  `refresh-posters.py --meta` refreshes them without touching an image.
- **Four tabs.** Movies, Showtimes, Map and Settings, left to right, opening on Movies.
  Settings holds Appearance (System, Light, Dark), where distances are measured from,
  and when the showtimes were read. The theme is no longer a button in the header.
- **When to leave.** Each cinema says "leave 20:11 for the 20:30", computed from the
  travel time already on the row. There is deliberately no allowance for the ad reel in
  that subtraction. Cinemex reels do run fifteen to twenty minutes, but nobody has
  measured it and the error would be the dangerous way round -- too generous an allowance
  sends you out of the door late. Against the billed time the worst it can do is make you
  early.

## Working with no signal, and how that was nearly not true

The map used to run offline out of the **browser's** own HTTP cache, and
`maplibre-gl.min.js` was in no cache this app controls. Reading `sw.js` does not show
that. Opening the caches does:

    sala-v23-shell    8
    sala-v23-posters  37
    sala-v23-tiles    11
    sala-v23-lib      5    <- five font files from fonts.gstatic.com, and nothing else

A plain cross-origin `<script>` or `<link>` is a **no-cors** request, so `fetch` inside the
worker resolves to an opaque response with status 0 and `ok` false, and every branch in
`sw.js` correctly refuses to store one -- the tiles branch says so in its own comment. So
the guard that protects the tiles was quietly refusing the one script the map cannot start
without. The font *files* were cached because `@font-face` fetches them in CORS mode by
spec; the stylesheet that names them was not, for the same reason as the script.

`crossorigin="anonymous"` on the three tags fixes it -- both hosts already send
`access-control-allow-origin: *`, checked before changing anything. `sw.js` warms those
three URLs during install, because a `<script>` in the head is fetched while the worker is
still installing and has not claimed the page, so the runtime branch would only catch them
on the second launch. The warm is deliberately not part of `addAll(PRECACHE)`: that call is
atomic on purpose, and a hiccup at cdnjs must not stop the app caching its own page.

    /opt/homebrew/bin/python3 test-offline-lib.py

That runs the static guard -- the three warmed URLs have to appear in the page verbatim, or
a version bump in one and not the other leaves the app caching a library it no longer
loads -- and then measures it: `tools/offline-check.mjs` loads the app once with a signal,
**clears the browser's own HTTP cache**, cuts the network and reloads. That clear is what
makes it a test rather than a restatement; without it an offline reload can be served
entirely out of the disk cache and every assertion passes on an app that would fail on the
Metro. After the fix, one visit is enough: the whole day's listing, every price, every
poster, all 33 typefaces and the map, with the network off and the browser cache empty.

It used to assert numbers -- at least 30 cinemas, at least 100 prices -- and those were
facts about 9 September rather than about caching, so the run went red on the calendar the
moment the payload rolled to a day with 29. It takes the same reading with a signal and
without one now and requires them to be equal, which is the question it was always asking.

## How it is built

One self-contained HTML file, no framework, no build step for the page itself. MapLibre GL
for the map, OpenFreeMap's vector tiles, a service worker for offline.

`build.py` turns the original published page into this one. It does three things:

1. **Strips 7.8 MB of base64 map tiles.** They had to be baked in because the original was
   published somewhere whose content policy blocks every image host. On its own domain the
   map layer is ordinary, and the page drops from 8.1 MB to a few hundred KB, which is most of why
   it launches instantly.
2. **Gives it a real `<head>`** — the web app manifest, `apple-mobile-web-app-capable`,
   theme colours, icons. Those tags are what iOS reads when you Add to Home Screen; without
   them the icon just opens Safari.
3. **Adds the service worker**, which caches the shell on first load and each map tile the
   first time you pan over it.

### On picking a tile host

The map was Leaflet over Esri's Light Gray Canvas raster tiles until 8 September, when he
photographed it zoomed in and said it was blurry. It was. **Esri has no tile above zoom
16** — 17, 18 and 19 all return an identical 2,521-byte image reading "Map data not yet
available" — so Leaflet was stretching a zoom-16 picture across a zoom-18 view. Stretching
pixels is what blurry is.

A different raster host only moves the ceiling up a level. Vector tiles carry geometry
rather than pixels, so the renderer redraws roads and labels at whatever scale the screen
is at, and it is sharp at every zoom. That is why the map is now MapLibre GL over
OpenFreeMap — free, no key, no request limit, OpenStreetMap data.

Four hosts were looked at, and **three of the four answered HTTP 200**:

| Host | What came back | Verdict |
|---|---|---|
| OpenFreeMap vector | 333 KB of real protobuf at z14 | in use |
| CARTO `light_all` raster | 200, 24 KB, "API KEY REQUIRED" watermarked across it | refused |
| OpenStreetMap raster | 200, 7 KB, "Access blocked — not following the usage policy" | refused |
| Esri Light Gray Canvas | 200, 2,521 bytes, "Map data not yet available" above z16 | the bug |

**No status check separates any of those.** Only opening the picture does, which is why
they were opened. If the tile host is ever swapped again, look at a tile.

## Showtimes are a snapshot

They were pulled from Cinemex's public API and are stamped in the page. Every showtime chip
links to Cinemex checkout, so the price and the seat map are always live even when this
listing is a few days old.

To refresh them:

    /opt/homebrew/bin/python3 refresh-showtimes.py --dry-run   # fetch and check only
    /opt/homebrew/bin/python3 refresh-showtimes.py             # write the Cinemex half
    /opt/homebrew/bin/python3 refresh-cineteca.py              # add the three sedes
    /opt/homebrew/bin/python3 refresh-posters.py               # posters for any new films
    /opt/homebrew/bin/python3 director-truncation.py           # names Cinemex cut off
    /opt/homebrew/bin/python3 build-rooms.py                   # only if test-detail goes red
    # then bump the cache name in docs/sw.js, or an installed phone keeps the old build

`director-truncation.py` runs every time, and it runs against the page it is replacing: it
restores a director name only where the new value is a strict PREFIX of the one already
published, which is the exact signature of a fixed-width truncation and nothing else. The
two-chain merge repairs those names too, but only while both chains happen to be showing the
same film -- Cineteca showed La Odisea on 9 September and not on the 11th, and "Christopher
Nolan" silently became "Christopher Nola" again.

`build-rooms.py` is 287 calls and about seven minutes, so it is not part of every refresh.
Run it when `test-detail.py` reports a session whose room name is missing from that cinema's
room table, which happens when a film opens in an auditorium that had nothing on it last
time.

`refresh-cineteca.py` runs the film merge itself as its last step, because it is the only
point in the chain where both chains are on the page at once -- `refresh-showtimes.py`
rewrites the whole payload from the Cinemex side and drops Cineteca. `merge-films.py` can
also be run on its own against a page that is already written, and does nothing if there
is nothing to fold.

## One film, one entry

Both chains publish the same film under their own ids, so the payload carried "La Odisea"
twice -- 264 Cinemex showings under `71948` with the director recorded as "Christopher
Nola", and 12 Cineteca showings under `ct-HO00009759` with it spelled correctly. The Films
tab listed it twice and the film sheet that says "N cinemas, nearest first" left the
Cineteca screenings out of both copies. Eight titles were in that state on the 9 September
payload, one of them duplicated inside Cineteca alone, which publishes its dubbed and
subtitled runs as separate ids.

**The join key is two signals, not one, and the obvious single key is wrong in both
directions.** Keying on the original title alone misses three of the eight -- Cineteca
writes "Coyote vs Acme", "Coyote vs. Acme" and "Coyote VS Acme" for one film, and
transliterates Arabic differently from Cinemex -- and invents one that is not there,
because five films carry an empty original title and would all fold together. So a
candidate comes from either the folded original title or the folded display title, and is
then corroborated by runtime within five minutes and by director as a prefix test, because
Cinemex truncates that field. Both corroborators can only refuse a merge, never create
one.

    /opt/homebrew/bin/python3 test-merge-films.py

The controls take the live payload, pull a merged film back into the two entries the chains
published, and require every check to go red on it before requiring them to go green after
the merge. That red half is the point: it was run against the unfixed page first, where it
found 12 duplicated title keys across 8 films and not one film reachable in both chains.

## What "last day" is allowed to mean

The obvious way to find the screenings worth knowing about in advance is to count them:
everything playing once or twice in the next month. On this data that count is an
artefact and would have put a false sentence on the screen.

**Cineteca publishes two days at a time.** Cinemex carries thirty days; Cineteca carried
2026-09-09 and 2026-09-10 and nothing else. Twenty-two of the twenty-three films with
three or fewer showings are Cineteca titles, and they are rare in this data because the
board stops on Thursday rather than because the film does.

So the test is not a count, it is a question about the listing: **has a cinema published a
whole programming week that does not contain this film?** Cinema weeks here start on
Thursday, which is why a Tuesday pull sees less than a Thursday one, so a complete week is
seven consecutive published days beginning on a Thursday. A run is over only when every
cinema showing the film has published such a week after its last date. The seven is the
number of days in a week, not a threshold anybody picked.

Cineteca has never published a complete week, so nothing there is ever called a last day.
The same rule refuses PULP -- one date, eight cinemas, Thursday 24 September, and Cinemex
has published only six days past it -- and refusing that is the proof it works. It accepts
Rebelion en la Granja, which plays thirty times today at fourteen cinemas and appears in
none of the three published weeks after it.

    node test-coming-up.mjs

The controls run the real functions against the real payload with the clock stubbed, and
section 4 runs the rejected count rule beside the week rule and requires them to disagree.
A rule is only worth its complexity if the simpler one it replaced actually fails.

The free-screens list has the matching restraint. Idea 17 called it "free tonight" and it
cannot be: none of the fifteen publishes a programme this page can read, which is why they
have no showtimes anywhere else in the app either. It says so on the sheet. Several of the
audits do carry a rhythm -- "Thursdays 17:00", "Tue and Fri 16:30" -- and none of it is
lifted onto a row, because two of those are worded "e.g." and three sit beside "2026
continuation not confirmed". The sentences stay on each venue's own sheet with the tag
that says how well they are known.

    /opt/homebrew/bin/python3 test-free-rooms.py

The refresh refuses to write a payload that is materially worse than the published one --
fewer cinemas, a big drop in showtimes, fewer films, or a first day that is not today. An
empty answer from an API is a perfectly successful set of HTTP requests, and a page that
quietly lists nothing on Thursday looks exactly like a page that is fine.

**Cinema weeks in Mexico start on Thursday**, so a pull made on a Tuesday has the current
week in full and only advance sales past Wednesday. Refreshing on a Thursday or later gets
the most out of it. The 8 September pull went from 5,445 showings to 7,853 purely because
Thursday-to-Sunday had been published in between; Tuesday and Wednesday barely moved.

`CINEMEX-API.md` has the endpoints, the version-in-the-path trap, and why this runs at
build time rather than in the page.

## Attribution

Map tiles by OpenFreeMap, from OpenMapTiles and OpenStreetMap contributors. Showtimes and
posters from Cinemex's public web API. The venue audit — screen sizes, projection, sound,
which claims are verified rather than assumed — is original research.
