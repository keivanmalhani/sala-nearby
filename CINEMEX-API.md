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
