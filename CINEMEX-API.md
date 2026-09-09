# Cinemex's public web API

Every showtime and every poster in this app comes from the API cinemex.com's own web
client calls. This file is here because three separate things about it are non-obvious and
each one cost real time to find.

## The endpoints

```
GET https://api.cinemex.com/rest/v2.37.2/cinemas/
GET https://api.cinemex.com/rest/v2.37.2/cinemas/<cinema id>/movies
GET https://api.cinemex.com/rest/v2.37.2/movies/
```

Required header, shipped by their own public web client:

```
x-api-consumer-key: XXQha7vz4kdvoMSdixhN
```

Without it the answer is `401 credentials-missing`.

## 1. The version is in the PATH, not in a header

This is the one that wastes an afternoon. Every header spelling of the app version —
`app-version`, `x-app-version`, `version`, `appversion` — returns:

```
400  {"error": "app-update-required"}
```

which reads exactly like a version wall you cannot get past, and is really the server
telling you the URL is wrong. `/rest/v2/movies` answers 400 rather than 404 for the same
reason. The version belongs in the path segment and nowhere else. Chrome's network panel
on cinemex.com/cartelera shows the real shape in one look.

## 2. It answers CORS for cinemex.com and nobody else

```
access-control-allow-origin: https://cinemex.com
```

So a browser on `keivanmalhani.github.io` is refused no matter what, which is why the
showtimes are baked into the page at build time and the posters are downloaded to our own
origin. That constraint is also what makes the app work with no signal, so it turned out to
be the right shape anyway.

The consequence to remember: **the listings in the page are a stamped snapshot.** Every
showtime chip links straight to Cinemex checkout, which is always live, so a few-day-old
snapshot degrades into a slightly-wrong listing rather than a wrong purchase.

## 3. Use the Homebrew Python, never `/usr/bin/python3`

Same URL, same headers, same second, two interpreters:

```
/usr/bin/python3          3.9.6    LibreSSL 2.8.3   -> 403
/opt/homebrew/bin/python3 3.14.7   OpenSSL 3.6.3    -> 200
```

Nothing differs but the TLS stack. macOS `curl` links the same LibreSSL, which is why
header experiments against it answer the wrong question. This is not specific to Cinemex —
it is a general property of hosts that fingerprint the ClientHello.

## The shape of the data

`cinemas/` returns every cinema in the country with `id`, `name`, `lat`, `lng`,
`platinum`, and an `info` object carrying address and phone.

`cinemas/<id>/movies` returns the films playing at that cinema. Each film carries an
`info` block (duration, rating, genre, director, original title, synopsis) and a `versions`
array — one entry per format-and-language combination, e.g. "Premium Subtitulada" with
`type: ["premium", "lang_sub"]`. Each version carries `sessions`, and a session is the
actual product:

```json
{ "datetime": "2026-09-08T20:30:00",
  "auditorium_name": "Sala 5",
  "availability": "high",
  "url": "https://cinemex.com/.../checkout/65502653" }
```

`movies/` returns the full film catalogue with poster URLs. Two things about those:

- **Some poster URLs are protocol-relative** (`//statics.cinemex.com/...`). A browser
  resolves those silently; `urllib` answers "unknown url type" and gives up. Two of the
  first thirty-nine failed this way and one of them was the most prominent film on the
  page, which is exactly the kind of gap a browser-only test never shows you.
- `poster_medium` is 750x1125 at about 110 KB. `poster_small` is 200 px wide and looks
  soft on a 3x phone. The build downscales medium to 520 wide, which is sharp in a
  two-column grid and costs about a third as much.

## Politeness

One request per cinema, 0.35 s between them, and only the cinemas inside the radius —
32 of the 58 in the CDMX box. A full refresh is about 35 requests and takes under a minute.
`refresh-showtimes.py --cached` re-uses the last raw pull so repeated analysis costs them
nothing.

## 4. The version in this file still works, and it is not the current one

Measured 2026-09-09, same minute, same consumer key:

```
GET /rest/v2.37.2/cinemas/   -> 200
GET /rest/v2.38/cinemas/     -> 200
```

`v2.38` is what their own web client calls today. **`v2.37.2` has not been retired**, so
nothing in this app is broken by being a version behind, and there is no urgency here.
Worth knowing rather than acting on: a version that stops answering will do it without
warning, and the failure mode is `400 app-update-required`, which section 1 explains reads
like a wall and is really a wrong URL.

## 5. One session id carries the price table, the seat map and the room

Undocumented until now, and it is the highest-value endpoint on this API:

```
GET https://api.cinemex.com/rest/v2.38/sessions/<session id>    -> 200, ~14 KB
```

Verified against session `65504509` at Galerías Insurgentes Market. Top-level keys include
`auditorium_name`, `layout`, `cinema`, `movie`, `availability`, `payment_methods`,
`candybar`, `extreme`, `adults_only`, `alerts`. The response carries seat typing
(`regular`, `wheelchair` and companion spaces), the ticket price table, and the auditorium
name and screen number — four separate things this app currently has no way to show.

Session ids come from the per-cinema movies call, inside the `sessions` arrays. Those
entries are thin on purpose and carry only:

```
id · auditorium_number · availability · date · datetime · timestamp · tz_offset
```

So the room's NAME and its seat map are one extra request per session, not something the
listing call gives you. A full price sweep of Mexico City is roughly 214 calls; a full
seat-map pass is roughly 635 and is a one-off.

**The assigned-seating question is CLOSED, and `layout` was not the answer.** All 287
auditoriums were fetched on 9 September. `layout` is a list of rows, each `{name, seats}`,
each seat `{id, label, status, type}` -- geometry plus live availability and nothing else.
The string `assigned` appears in none of the 287 responses. The field that answers it is
the top-level boolean **`seatallocation`, which is `true` on all 287 rooms**, so assigned
seating is universal at Cinemex rather than a Platino or Premium feature. Do not present it
as a premium perk.

**Three traps in `layout`, each of which yields a plausible wrong number:**

- `len(layout)` is NOT the row count. Entries with an empty `name` are spacers. Antara
  Platino Sala 5 returns 15 entries for 8 lettered rows.
- A seat count must include `status: "1"`. Taken seats stay in the layout, so counting only
  the free ones turns a busy screening into a small room.
- `type: blank` and `status: "E"` are the same fact twice -- aisles and gaps. Counting cells
  rather than seats inflates every room by roughly half.

**Two numbers worth stating carefully.** 111 of the 287 rooms carry no wheelchair seat type
in the map at all; that is a fact about the seat map, not a claim that the building is
inaccessible. And companion spaces are zero in every room -- a measurement, not a missing
key, because each session's own `seat_types_override` declares
`wheelchair-companion_0/_1/_selected` and `app/settings` labels it "Acompanante", so the
type exists and is applied to no seat anywhere.

**Format belongs to the SHOWTIME, not to the room.** Parque Delta Sala 3 is the IMAX
exclusively, 75 of 75. Sala 10 is Atmos on only 72 of 76 -- the other four are plain
Espanol Tradicional -- so a hardcoded per-room format label mislabels real screenings. And
CinemeXtremo has ZERO showtimes across all 32 venues: no screening anywhere carries the
`cx` key, and the association of that name with a room comes only from the venue's building
attributes and from ticket products prefixed `CX`. That is an inference from a product code,
not a statement by the format data.

## 6. THE FORMAT TRAP: IMAX is in `primary`, Dolby Atmos is only in `secondary`

This is the one that will silently produce a wrong app. Measured across six premium CDMX
venues (Antara Market and Platino, Manacar, Parque Delta and Delta Platino, Patriotismo
Market) on 2026-09-09:

```
attributes.primary     lang_sub 87 · premium 85 · lang_es 74 · platinum 31 ·
                       traditional 20 · imax 14 · infinity-vision 4 · v3d 1
attributes.secondary   dolby_atmos 11        <- and nothing else, anywhere
type                   no format strings at this level
```

So a reader built on `attributes.primary` alone gets IMAX, Platino, Premium, 3D and the
subtitled/dubbed flag all correct, and reports **zero Dolby Atmos rooms in Mexico City**.
It looks healthy precisely because the formats it does read work. Read both arrays.

**A warning about how to check this.** A first probe of one cinema, Galerías Insurgentes
Market, found zero Atmos in every field and zero in `secondary` too — because that venue
has no Atmos room. A negative result there could not have distinguished "the field is
empty" from "this cinema has none", so it was not evidence either way. Any future check of
which field carries a format has to be run against a venue that actually has that format.

## 7. Snacks are switched off nationally, and that is a measured finding

`candybar` reads `false` on all 70 CDMX cinemas, `candybar/catalog` answers 200 for all
278 cinemas and returns an empty catalog for every one, and `cinemex.com/dulceria` is a
404. Two independent passes on 2026-09-09 reached this separately.

The API is not broken and the request is not wrong: there is no machine-readable Cinemex
menu to have. Do not spend another afternoon looking for one. Cineteca is the opposite —
its menus are real PDFs with real prices, though its dulcería PDF is image-only and needs
OCR, and the cafetería menu its own page links is a 404.
