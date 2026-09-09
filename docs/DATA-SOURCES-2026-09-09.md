# Data sources for the eight things he asked for, 9 September 2026

Every status in this file is one I got myself, from `/opt/homebrew/bin/python3` 3.14.7 on
OpenSSL 3.6.3. No `/usr/bin/python3`, no macOS curl, no browser. Nothing here is a price or
a menu item I did not read out of a real response.

**Score: six of the eight are obtainable outright. One is half-obtainable -- Cineteca's menus
are there and Cinemex's do not exist on any public surface. One is a genuine nothing: no CDMX
cinema publishes a dress code.**

| # | Thing | Verdict |
|---|---|---|
| 1 | Snack and drink menus with prices | OBTAINABLE for Cineteca; NOT-OBTAINABLE for Cinemex |
| 2 | Alcohol, and where | OBTAINABLE |
| 3 | Loyalty programmes and points | OBTAINABLE for Cinemex; third-party only for Cinepolis |
| 4 | Projection type per auditorium | OBTAINABLE |
| 5 | Audio format and language per auditorium | OBTAINABLE |
| 6 | Seats, recliners, wheelchair spaces | OBTAINABLE |
| 7 | Ticket price per cinema, per format, per day | OBTAINABLE |
| 8 | Dress code | NOT-OBTAINABLE, because there isn't one |

---

## The single highest-value find

    GET https://api.cinemex.com/rest/v2.38/sessions/<session id>
    x-api-consumer-key: XXQha7vz4kdvoMSdixhN
    -> 200, ~14 KB of JSON

`CINEMEX-API.md` documents `cinemas/`, `cinemas/<id>/movies` and `movies/`. It does not
document `sessions/<id>`, and that one endpoint carries **items 4, 5, 6 and 7 at once**: the
real ticket price table in centavos, the full seat map row by row with each seat's type, the
auditorium name and screen number, and whether seats are assigned. One request per showtime,
no auth beyond the key already in use.

Second-highest: `GET /rest/v2.38/landings/` returns Cinemex's **entire CMS in one 9.77 MB
response**, 176 landing pages. That is where the promo rules, the format explanations and the
Platino drinks line live.

Also worth writing down: **the live API version is `v2.38`, not the `v2.37.2` in
`CINEMEX-API.md`.** Read out of their own bundle at
`https://s3.amazonaws.com/statics3.cinemex.com/v2/static/js/main.2dc47d71.chunk.js` (200,
1,017,608 bytes), which contains `{appId:"XXQha7vz4kdvoMSdixhN", host:"https://api.cinemex.com/",
path:"rest/v2.38/"}`. Both versions answer 200 today and return identical bytes for
`candybar/catalog`; 2.38 is what their web client actually calls.

---

## 1. Snack and drink menus, with prices

### Cinemex: NOT-OBTAINABLE, and it is their end that is empty

    GET https://api.cinemex.com/rest/v2.38/candybar/catalog?cinema_id=76   -> 200
    {"catalog":[],"blocks":[{"id":999999,"name":"Todos los productos"}]}

Structured JSON, and the endpoint is real -- omitting the parameter returns
`{"errorcode":"missing-fields","error":"Either cinema_id or session_id should be specified."}`,
so it is parsing the request, not rejecting it.

**Swept all 278 Cinemex cinemas. 278 answered 200. Zero returned a non-empty catalog.**
`session_id=65513041` also returns the empty catalog. All 278 cinema records in
`cinemas/` carry `"candybar": false`, and so did all 28 session records I opened. So this is a
national switch-off, not a per-cinema gap and not a wrong parameter.

Corroborating negatives, so this is not one probe's opinion:
- `https://cinemex.com/sitemap.xml` (200, 703,815 bytes, 8,893 urls) contains **zero** urls
  matching "dulceria".
- `https://api.cinemex.com/rest/v2.38/articles/` (200, 860,459 bytes of their own news feed)
  contains "dulcer" zero times and "palomit" zero times.
- `cinemex.com/dulceria` returns the same 443,698-byte React shell as every other path; the
  page is fed by the empty endpoint above.

**What does exist** are promo combos in the CMS, which give composition and a few real prices
but never a menu:

- `Combo Cinemex Loop Peques` -- "1 boleto sala POP, Tradicional 2D y premium 2D ... unas
  palomitas medianas (85 g aprox), 1 refresco mediano (680 ml) c/u y un chocolate conejo
  turin (20g aprox). El cambio de sabor de las palomitas tiene un costo de $20 pesos."
- Loyalty birthday combo: "$120, para formato Tradicional y Premium, para formato Platino
  adquiérelo por $149."
- Refill: "$25 Refill de palomitas y refresco (Precio por cada uno)" at the Arena tier;
  "$20 C/U" in the sign-up packages.

Those are real quotes from real 200s. They are not a dulcería price list and should not be
presented as one.

### Cineteca: OBTAINABLE, and the menus are complete

Menu PDFs, linked from `https://www.cinetecanacional.net/espacios_8.php` (200, 38,830 bytes):

| Menu | URL | Status | Text layer |
|---|---|---|---|
| La Terraza (Xoco) | `/docs/espacios_812/CNMX/terraza/menuTerraza.pdf` | **200**, 438,957 B, 10 pages | yes |
| El Mirador (de las Artes) | `/docs/espacios_812/CNA/menuMirador.pdf` | **200**, 5,820,735 B, 4 pages | yes |
| Dulcería (Xoco) | `/docs/espacios_812/CNMX/dulceria/menuDulceria.pdf` | **200**, 783,876 B, 8 pages | **no -- 8 bytes of text** |
| Fuente de sodas | `/docs/espacios_812/CNMX/fuente/menuFuente.pdf` | **200**, 783,876 B | same file, md5 `72baaaee...` |
| Cafetería 8½ | `/docs/espacios_812/CNMX/cafeteria812/menuDigital.pdf` | **404** | -- |

Two things about that table are findings rather than notes. The **cafetería menu link on
their own live page is dead** -- the page renders a Menú button that 404s. And the **dulcería
and fuente links are commented out in the HTML but the files are still served**, byte for
byte identical to each other, so the dulcería menu is reachable even though nobody links it.

Real items pulled with `pdftotext -layout`, La Terraza:

    Ensalada GINGER Y FRED   $134     Sandwich 8 1/2        $132
    Ensalada FELLINI         $196     Panini FEDERICO       $145
    Guacamole con totopos    $157.00  Helado flotante       $58.00
    Americano  $42 / $45 / $48       Capuchino  $53 / $56 / $58
    Latté      $56 / $58 / $62       Flat white $73 / $75 / $79
    Limonada   $58.00                Refresco de lata       $50.00
    Agua natural Sta Maria   $30.00  Agua mineral Perrier   $62.00

El Mirador:

    Pizza NAUFRAGIO          $218     Pizza PUERTAS DEL PARAÍSO  $269
    Crepa CHAMPIÑÓN          $103     Crepa Lechera con fresa    $97
    Tosta LA OTRA            $120     Tabla de carnes frías      $287
    Papas a la francesa      $99      Pastel de chocolate        $92
    Mineral San Pellegrino   $47      Refresco lata CC light     $43

**The one gap: the Cineteca dulcería menu is an image-only PDF.** 8 pages at 1440x810 pts,
produced by iLovePDF in April 2023, and `pdftotext` returns 8 bytes. Popcorn and cinema-snack
prices need OCR. That is the "with work" in this section, and it is one file.

Cineteca Chapultepec has **no menus at all** -- its slot on `espacios_8.php` renders
`/imagenes/espacio_8/img_proximamente.png` and every Menu button beside it is commented out.

Opening hours per outlet are on the same page and are plain text:

    Dulcería principal y plaza del cubo   L-V 13:30-21h, fines de semana 11:30-21h
    Cafetería 8 1/2 y fuente de sodas     L-J y dom 11-21h, V-S 11-22h
    Patio Cineteca                        Mar-dom 14-21:30h
    La Terraza                            J y dom 14-22h, V-S 14-23h
    (de las Artes) Fuente El Mirador      Dom-J 14-21:30h, V-S 14-22:30h

---

## 2. Alcohol: who serves it, and what

**OBTAINABLE.** Both chains, from different kinds of source.

### Cineteca -- priced, in the menu PDFs above

La Terraza, `menuTerraza.pdf`, section "VINOS Y CERVEZAS":

    Cerveza nacional 355 ml                    $62.00   (Negra Modelo, Modelo Especial,
                                                         Bohemia Clara/Obscura/Weizen/Cristal,
                                                         XX Ámbar, XX Lager)
    Cerveza artesanal 355 ml                   $94.00   (Tempus, Lagunitas IPA, Jabalí)
    Cerveza de barril Modelo 500 ml            $87.00
    Stella Artois (botella o barril) 330 ml    $90.00
    Botellín L.A. Cetto 187 ml                $148.00
    Copa L.A. Cetto o Las Moras 150 ml        $123.00
    Copa Casa Madero 3V tinto 150 ml          $205.00
    Botella Casa Madero 3V tinto 750 ml       $972.00
    Clericot                                  $134.00
    Sangría                                   $133.00
    Clamato $50.00 · Tarro michelado $17.00 · Tarro cubano $17.00

El Mirador, `menuMirador.pdf`:

    copa l.a cetto 150 ml   $118     cerveza nacional         $56
    copa 3v 150 ml          $195     cerveza artesanal 355 ml $95

### Cinemex -- Platino only, and it is a sentence rather than a menu

    GET https://api.cinemex.com/rest/v2.38/landings/cines-platino  -> 200, 22,059 bytes

    "meta_desc": "Butacas reclinables, servicio a la sala, y ahora nuevo menú de bebidas
                  con Topo Chico Hard Seltzer"

That is the whole of it, and it is worth being precise: it names one alcoholic product on
one format and gives no price and no list. Searching the full 9.77 MB CMS dump for the
obvious words returns "cerveza" 4 times and "alcoh" 4 times, and **every one of those hits
is outside a current cinema menu** -- three are sweepstakes small print, and the fourth is an
NFL combo page whose own record reads `"is_active": false`:

    "Combo individual (1 boleto + Cerveza o refresco + Palomitas grandes clásicas +
     Hot Dog) por $162. Combo equipo (2 boletos + 2 cervezas o refrescos + ...) por $273."

Real text, real prices, **retired promo**. Do not put it in the app as current.

So for Cinemex the honest, sourced statement is: **Platino sells alcohol; nothing else on
their public surface says any other format does**, and there is no price list for any of it.
The 15 Platino complexes in the CDMX box are identified structurally in item 4 below, so the
"which cinemas" half of the question is answered even though the "what does it cost" half is
not.

---

## 3. Loyalty programmes and points

### Cinemex -- OBTAINABLE, structured, and better than expected

**The programme is called Cinemex Loop.** "Invitado Frecuente" returns zero hits anywhere in
their CMS; the legacy name that survives in their own terms is "Invitado Especial Cinemex
PAYBACK", and the current one is Loop.

    GET https://api.cinemex.com/rest/v2.38/ie/benefits   -> 200, 119,205 bytes

Five tiers, each an array of benefit objects with `id`, `title`, `category`, `description`
(HTML). **Points accrual, straight out of the payload:**

| Tier | Accrual on spend at Cinemex complexes |
|---|---|
| `one` | 3% |
| `basic` (Red) | 5% |
| `gold` | 8% |
| `premium` (Platino) | 10% |
| `arena` | Red benefits plus Arena gaming perks |

Benefit counts: basic 23, gold 22, premium 23, one 21, arena 11.

What a point is worth, in their words: *"La acumulación se realiza mediante la bonificación
en Puntos Cinemex, dichos puntos pueden usarse como medio de pago."* They are spendable as
payment. **The payload never states a points-to-pesos ratio**, and I am not going to invent
one -- if the app wants to show a peso value it needs a source I do not have.

Membership prices, per cinema, also structured:

    GET https://api.cinemex.com/rest/v2.38/loyalty/getSignUpOptions/cinema/<id>  -> 200

Prices are in centavos and **differ by cinema for the same package**, which is a genuinely
nice thing for the app to show:

    "Nivel Red - 5 boletos"   Antara Platino (76)  $899.00
                              Altavista (86)       $469.00
                              Arenal (357)         $349.00
    "Nivel Red - 10 boletos"  Altavista (86)       $849.00
                              Arenal (357)         $619.00
    "Red Platino"             Antara Platino (76)  $119.00

Each option carries a `benefits` array of plain strings -- "Martes 2x1.", "Refill de palomitas
y refresco por $20.", "Combo cumpleaños gratis." -- which is directly renderable.

The weekday combos are in the benefits payload too and are specific: Combo Miércoles is
"2 boletos para sala tradicional 2D, 1 palomitas clásicas grandes (100 g aprox) y 2 refrescos
grandes (946 ml c/u)"; Combo Viernes adds a jumbo popcorn and a Snickers.

### Cinepolis -- third-party only, and one number is not confirmed

Their own site is closed to this network and I did not re-probe it. What I did fetch:

    GET https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1
        &format=json&titles=Cin%C3%A9polis                            -> 200, 18,964 bytes
    GET https://marcas.cinepolis.com.gt/marcas/club-cinepolis/
        terminos-condiciones-ca/terminos-condiciones-guatemala.html   -> 200, 14,796 bytes

The second is a **different registrable domain** from the blocked `cinepolis.com`, and it is
Cinepolis' own authoritative programme terms -- for Guatemala. From it, verbatim:

- *"La Tarjeta Club Cinépolis® acumula puntos por el equivalente al 5% sobre el total de las
  compras en Taquilla, Dulcería, Coffee Tree® y Spyral de Cinépolis tradicional, así como en
  Taquilla, Dulcería, Coffee Tree® y menú de alimentos y bebidas de Cinépolis VIP®."*
- *"Los puntos acumulados tienen vigencia hasta 31 de diciembre de cada año."*
- *"Para canjear los puntos en taquilla deberás acumular al menos el valor total del boleto.
  Cada punto equivale a un Quetzal."*
- Points must be earned at the moment of purchase; redemptions earn no new points; no cash-out.

Wikipedia dates the programme to 2001. **The Mexican peso value of a point is not
established.** A web search surfaces "1 peso cada 10 puntos" on a Mexican consumer blog; that
is a blog, not Cinepolis, and I did not fetch a primary source that says it. If the app is
going to state a value for Mexico, that number still needs finding.

---

## 4. Projection type per auditorium

**OBTAINABLE, and there are two layers to it: the dictionary and the assignment.**

### The dictionary

    GET https://api.cinemex.com/rest/v2.38/app/settings   -> 200, 59,481 bytes

`attributes.cinemas` -- what a whole complex is:

    3d "3D" · 4d "4D" · cx "CinemeXtremo" · platinum "Platino" · premium "Premium"
    art "Casa de Arte" · cinemom "CineMá" · market "Market" · Infinity Vision

`attributes.movies` -- what a screening is, 52 keys. The ones that matter here:

    traditional "Tradicional" · premium "Premium" · platinum "Platino" · confort "Confort"
    v3d "3D" · v4d "4D" · imax "IMAX" · imax_3d "IMAX 3D" · infinity-vision "Infinity Vision"
    macro "Macropantalla" · jumbo "Jumbo" · palco "Palco" · dbox "DBox" · hfr "HFR"
    recliner "Recliner" · recliner_vip "Recliner VIP" · dine_in "Dine in" · plus21 "21+"
    art "Casa de Arte" · alt "Espacio Alternativo" · rated_c "Sólo adultos"

This is Cinemex's own controlled vocabulary with their own Spanish display names, which is
exactly what the "what does Platino actually mean" question wants -- no guessing.

### The assignment

Every version in `cinemas/<id>/movies` carries `type` (array), `label` (human string) and
`attributes.primary` / `.secondary`. Every session under it carries `auditorium_number`.
`sessions/<id>` then gives `auditorium_name`, `screen_number`, `premium` and `extreme`.

I pulled all 70 CDMX-box cinemas (70 of 70 at 200) and counted every version. **The complete
CDMX vocabulary in use right now, measured, not assumed:**

    769  Español Tradicional            [lang_es, traditional]
    214  Premium Español                [premium, lang_es]
    188  Premium Subtitulada            [premium, lang_sub]
    162  Platino Subtitulada            [platinum, lang_sub]
    121  Platino Español                [platinum, lang_es]
    120  Subtitulada Tradicional        [lang_sub, traditional]
     24  Dolby Atmos Español            [dolby_atmos, lang_es]
     23  IMAX Subtitulada               [imax, lang_sub]
     22  Dolby Atmos Subtitulada        [dolby_atmos, lang_sub]
     13  IMAX Español                   [imax, lang_es]
      8  3D Español                     [v3d, lang_es]
      8  Premium Confort Español        [confort, premium, lang_es]
      7  Premium Dolby Atmos Subtitulada
      6  4D Español                     [v4d, lang_es]
      6  Confort Español                [confort, lang_es]
      4  Dolby Atmos Infinity Vision Subtitulada
      4  Dolby Atmos Infinity Vision Español
      3  Infinity Vision Español
      2  Premium Infinity Vision Subtitulada
      2  Platino 3D Español
      1  each: Premium Dolby Atmos Español, Premium 3D Español,
            Platino Infinity Vision Español, Platino Infinity Vision Subtitulada,
            Premium Confort Subtitulada, Confort Subtitulada, 4D Infinity Vision Español

Note what is **absent** from CDMX: no `screenx`, no `junior`, no `dbox`, no `palco`, no
`macro`, no `4dx` under that name. Those keys exist in the dictionary but nothing in the
70 cinemas uses them -- because ScreenX and Junior are Cinepolis brands, not Cinemex ones.

### Which cinemas have which

Complex-level, from `cinemas/` `attributes` -- nationally: `3d` 174, `premium` 49, `platinum`
38, `cx` 19, `4d` 10, `market` 8, `art` 4. In the CDMX box, 15 cinemas carry `platinum`.

The IMAX list is published outright:

    GET https://api.cinemex.com/rest/v2.38/landings/imax   -> 200, 17,603 bytes

It names seven IMAX cinemas with coordinates. Filtering by the app's own CDMX box gives
exactly five: **Santa Fe (84), Parque Delta (32), Antara Platino (76), Tezontle (236),
Encuentro Oceanía (410)** -- the other two are Tijuana and Puebla. The Platino list from
`landings/cines-platino` (200, 22,059 bytes) names Park Plaza, Cuicuilco, Antara, Mundo E,
Santa Fe and Félix Cuevas among others, and adds the plain-language description of what
Platino is: *"Butacas reclinables, servicio a la sala."*

### Cinepolis format meanings -- third party, Wikipedia, 200

Their room counts as of December 2024, of 6,821 screens: IMAX 24, Macro XE 115, 4DX 63,
PLUUS 24, Sala de Arte 35, VR 3, Screen X 4, Júnior 72. And the definitions, which are what
the app actually needs in plain Spanish:

- **Macro XE** -- 170 m² screen, roughly four times a normal one, 13,000 W, Dolby Atmos 7.1.
- **Júnior** -- a children's room with slides and a ball pool, 4 to 11, A and AA ratings only,
  10 minutes of play before the film and a 15-minute interval in the middle. No adult without
  a child and no child without an adult.
- **4DX** -- moving seats plus water, air, scent, smoke, light, bubbles and taps on the seat back.
- **IMAX** -- dual projector plus DMR remastering, 2D/3D/HFR at 48 fps, wrap-around screen.
- **PLUUS** -- between VIP and traditional; wider seats and a footrest.
- **Screen X** -- projection onto both side walls as well, a 270-degree view.
- **VIP** -- electric reclining leather seats, gourmet food and candy delivered to the seat,
  usually a separate entrance beside or above a traditional complex.
- **Sala de Arte** -- a permanent art-house screen.

---

## 5. Audio format and language per auditorium

**OBTAINABLE, same payload, no extra request.** Language is not a separate field -- it is a
member of the version's `type` array, which is why it comes free with item 4.

    lang_es       "Español"          dubbed into Spanish
    lang_sub      "Subtitulada"      original audio, Spanish subtitles
    lang_original "Idioma Original"  in the dictionary; not in use in CDMX today
    dubbed        "Doblada"          in the dictionary; Cinemex uses lang_es instead

Audio format:

    dolby_atmos "Dolby Atmos"   atmos "ATMOS"
    cc "Closed Caption"         ald "Assistive Listening Device"

**There is a trap in how Atmos is filed, and it is the opposite of what you would guess.**
Across all 70 CDMX cinemas, 62 versions carry `dolby_atmos`. In **every single one**,
`dolby_atmos` is in the top-level `type` array and in `attributes.secondary` -- and it is in
`attributes.primary` **zero** times:

    {"label": "Dolby Atmos Subtitulada",
     "type": ["dolby_atmos", "lang_sub"],
     "attributes": {"primary": ["lang_sub"], "secondary": ["dolby_atmos"],
                    "primary_label": "Subtitulada", "secondary_label": "Dolby Atmos"}}

So `attributes.primary` reads as an ordinary subtitled screening and loses the sound format
completely. **Read `type`, which is the union, or read `secondary` as well.** A reader built
on `primary` would report zero Atmos rooms in Mexico City and look perfectly healthy doing it.
The 62 break down as Dolby Atmos Español 24, Subtitulada 22, Premium Subtitulada 7, Infinity
Vision Subtitulada 4, Infinity Vision Español 4, Premium Español 1.

Worked example, one request:

    GET .../sessions/65513036 -> "Dolby Atmos Subtitulada", Antara Platino, Sala 6

No 7.1-versus-5.1 channel count is published anywhere by Cinemex. The only 7.1 claim I found
is Wikipedia's on Cinepolis Macro XE. Do not put a channel count on a Cinemex room.

---

## 6. Seats, recliners, wheelchair spaces

**OBTAINABLE, and completely -- this was the biggest surprise.** `sessions/<id>` returns the
entire seat map.

    "seatallocation": true,          assigned seating, per session
    "auditorium_name": "Sala 1",
    "screen_number": 1,
    "tickets_limit": 6,
    "layout": [ {"name":"A","seats":[
        {"id":"8|8|4|54","status":"0","label":"14","type":"regular"},
        {"id":"","status":"E","label":"","type":"blank"}, ... ]}, ... ]

`type` is `regular`, `wheelchair`, `wheelchair-companion` or `blank` (aisle or gap).
`status` is `0` free, `1` taken, `E` not a seat. So seat count, wheelchair count, row count
and live availability all fall out of one response.

Measured, real auditoriums:

| Cinema | Auditorium | Format | Seats | Wheelchair |
|---|---|---|---|---|
| Antara Platino | Sala 1 | Platino Subtitulada | 67 | 2 |
| Antara Platino | Sala 4 | Platino Español | 63 | 2 |
| Antara Platino | Sala 5 | IMAX Subtitulada | 142 | 2 |
| Antara Platino | Sala 6 | Dolby Atmos Subtitulada | 136 | 2 |
| Artz Pedregal Platino | Sala 11 | Platino 3D | 36 | 0 |
| Mundo E Platino | Sala 7 | Platino Infinity Vision | 42 | 2 |
| Altavista | Sala 1 | Premium Subtitulada | 103 | 0 |
| Arenal | Sala 3 | Español Tradicional | 108 | 4 |
| Plaza Tlalnepantla | Sala 15 | Confort | 40 | 0 |
| Plaza Tlalnepantla | Sala 2 | 4D | 192 | 8 |
| Encuentro Oceanía | Sala 1 | IMAX Español | 236 | 7 |
| Mundo E | Sala 3 | Dolby Atmos Infinity Vision | 424 | 0 |
| Cd Azteca | Sala 3 | Subtitulada Tradicional | 336 | 0 |

`seat_types_override` on a session carries the labels and the per-format seat artwork:

    regular_0            "Disponible"        selectable
    wheelchair_0         "Silla de ruedas"   selectable
    wheelchair-companion_0 "Acompañante"     selectable

**Reclining seats are not a field.** The only sourced statement available is the Platino
landing page's *"Butacas reclinables, servicio a la sala"*. `recliner` and `recliner_vip`
exist as dictionary keys but are applied to zero CDMX screenings. So the app can say Platino
reclines, and must not claim it for anything else.

**Confort has a display name and no explanation.** `confort "Confort"` is in the dictionary
and 16 CDMX versions use it, but the word appears **zero times** in the entire 9.77 MB CMS.
Cinemex publishes nothing about what the format is. Do not fill that gap by analogy with
Cinepolis PLUUS -- it would be a guess wearing a citation.

Cineteca accessibility, from their FAQ (200): *"Todas nuestras salas están habilitadas para
el acceso en atención de las personas con discapacidad."* Assigned seating too -- the purchase
flow is "indica la cantidad de boletos y selecciona tus asientos", max 8 per session. Their
seat map is not exposed as an endpoint I could find; `detallePelicula.php` (200, 63,847 bytes)
carries no ajax url and links no external ticketing host, so the buy flow is JS on their own
domain and would need a browser.

**Cost of doing this exhaustively.** Across the 70 CDMX cinemas there are **635 distinct
auditoriums** named in the current showtimes and 22,821 sessions. One `sessions/<id>` call is
14.9 KB and took 1.13 s. So a full seat-map pass is 635 calls, about **16 minutes** at 0.35 s
spacing. Auditorium geometry does not change week to week, so that is a one-off build cost,
not a refresh cost.

---

## 7. Ticket prices, per cinema, per format, per day

**OBTAINABLE and this is the item with the most usable data behind it.** Same endpoint.

    "tickets": [ {"id":"E98","name":"PLATINO ESTRENO","price":23100,"fee":0,"tax":0,
                  "max":6,"combinable":true,"loyalty_level":null} ]

`price` is centavos. `fee` was 0 on every session I read.

Measured today, one session per format:

| Format | Cinema | Prices |
|---|---|---|
| IMAX Subtitulada | Antara Platino | $303 adulto |
| Platino 3D | Artz Pedregal Platino | $270 adulto |
| Dolby Atmos Subtitulada | Antara Platino | $256 adulto |
| Platino Subtitulada / Español | Antara Platino | $231 |
| Premium Dolby Atmos | Artz Pedregal Market | $193 / menor $174 / mayor 60 $166 |
| Platino Infinity Vision | Mundo E Platino | $185 |
| 4D Infinity Vision | Santa Fe | $163 |
| Premium Infinity Vision | Antara Market | $155 / $132 / $132 |
| 4D | Plaza Tlalnepantla | $140 |
| Premium 3D | Manacar | $132 / menor $119 |
| Dolby Atmos Infinity Vision | Mundo E | $120 / menor $108 |
| IMAX Español | Encuentro Oceanía | $119 / menor $107 |
| Premium Confort | Plaza Tlalnepantla | $119 / $107 / $107 |
| Infinity Vision Español | Iztapalapa | $74 / $63 / $63 |
| Subtitulada Tradicional | Cd Azteca | $61 / $55 / $55 |

**Price varies by cinema for the same format**, which is the interesting part for an app about
what is near you: plain Tradicional adulto reads $90 at Arenal, $74 at Iztapalapa and $61 at
Cd Azteca on the same day.

### Day-of-week discounts: measured, not assumed

Same cinema, same film, same format, one session per day, seven consecutive
`sessions/<id>` calls at Arenal (357), *SPIDER-MAN: Un nuevo día*, Español Tradicional:

    2026-09-09 Wed   CINEMEX MANIA = $39
    2026-09-10 Thu   CINEMEX MANIA = $39
    2026-09-11 Fri   ADULTO $90 · MAYOR 60 $81 · MENOR $81
    2026-09-12 Sat   ADULTO $90 · MAYOR 60 $81 · MENOR $81
    2026-09-13 Sun   ADULTO $90 · MAYOR 60 $81 · MENOR $81
    2026-09-14 Mon   ADULTO $90 · MAYOR 60 $81 · MENOR $81
    2026-09-15 Tue   ADULTO $90 · MAYOR 60 $81 · MENOR $81

The promo shows as a **different ticket product**, not a discount field, so an app reads it
for free by reading the ticket name.

Thursday 9/10 and Friday 9/11 were published in the same batch and differ, so the $39 is a
real promo boundary and not the stale-week artifact it could look like. The CMS confirms it
independently:

    GET https://api.cinemex.com/rest/v2.38/landings/cinemex-mania-septiembre-2026  (200)

    "Vigente del lunes 7 de septiembre al jueves 10 de septiembre de 2026. A precio de
     $39.00 en cualquier función, para los conceptos Tradicional y Premium, formatos 2D y 3D.
     No aplican formatos IMAX, 4D ni Dolby ATMOS, ni los conceptos Market y Platino."

Monday to Thursday, and the exclusions match what I measured -- my 9/09 Confort session at
$39 is "CINEMEX MANIA PREMIUM", and the IMAX and Platino sessions on the same days were at
full price. Two independent sources agreeing is why I am willing to state this.

`landings/` also carries `visa-2x1-promociones` and `paypal-2x1`, and the loyalty payload
carries "Martes 2x1" as a member benefit.

    GET https://api.cinemex.com/rest/v2.38/promos/   -> 200, 46,325 bytes
    first record: "Cinemexmanía Septiembre 2026 - Promo Boletos Tradicional - (del 07 al 10 de ...)"

**Cost of a full price sweep:** 214 distinct (cinema, format) pairs across the 70 CDMX
cinemas, about **5 minutes**. Prices change weekly, so this is a refresh cost, and it is a
cheap one.

### Cineteca prices -- plain text, no API needed

    GET https://www.cinetecanacional.net/FAQ.php   -> 200, 64,047 bytes

    "¿Qué precio tienen los boletos? $70 entrada general y $50 para menores de 25 años,
     estudiantes y adultos mayores. Martes y miércoles, ambos días el costo del boleto es
     de $50 para cualquier función (Este descuento no aplica para Muestra, Foro y Talento
     emergente)."

Same page: their listings refresh **Thursdays after 14:00**, which matches the Thursday
cinema week the README already documents for Cinemex. Also useful and quotable -- only food
bought at the Cineteca dulcería may be brought in, and the RTC rating letters A / B / B15 /
C / D are spelled out.

---

## 8. Dress code

**NOT-OBTAINABLE, because as far as any public source goes it does not exist.** This is a
finding, and I looked hard enough to be willing to say it.

Searched for `vestimenta`, `código de vestir`, `dress code`, `playera`, `sandalia`, `short`,
`bermuda`, `traje`, `formal` across:

- the full 9,771,389-byte Cinemex CMS dump (`landings/`, 176 pages, 200)
- the 119,205-byte loyalty benefits payload (200)
- the 860,459-byte Cinemex news feed (200)
- the Cineteca FAQ and its RECOMENDACIONES section (200)
- the Spanish Wikipedia article on Cinépolis (200)

**Zero hits describing an attire rule anywhere.** The words that do hit are unrelated --
"playera" is always a sweepstakes prize, "traje" is always the verb *tratarse*, "formal" is
always *formalizar*, and the one "short" is a Kentucky street address in a Fooji sweepstakes.

The nearest thing to an entry rule that does exist, and which is real:

- **Cinepolis Júnior** -- no adult without a child, no child without an adult (Wikipedia).
- **Cineteca** -- no outside food except from their own dulcería (FAQ).
- **RTC ratings** -- C is 18+, D is adults only; `rated_c "Sólo adultos"` and `plus21 "21+"`
  exist as Cinemex attribute keys.

If the app wants a "dress code" line it should say there is none, rather than leave the field
blank and let someone assume it was not checked.

---

## Reproducing any of this

The Cinemex key is unchanged and public in their bundle:

    x-api-consumer-key: XXQha7vz4kdvoMSdixhN

The version-in-the-path trap in `CINEMEX-API.md` still applies, and so does the interpreter
rule -- `/opt/homebrew/bin/python3`, never `/usr/bin/python3`, never macOS curl.

One thing that will bite a rerun: **`www.cinetecanacional.net` stopped resolving on this
machine mid-session** while `api.cinemex.com` and `example.com` resolved fine, and 8.8.8.8
and 1.1.1.1 both returned `201.98.21.38` throughout. It was a local negative cache, not their
outage. Pinning the address in `socket.getaddrinfo` got the remaining fetches through; a
rerun that suddenly cannot resolve them should check a public resolver before concluding the
site is down.

Endpoint summary, every one verified at 200 today:

    api.cinemex.com/rest/v2.38/
      app/settings                          59 KB   format + seat dictionary
      cinemas/                             228 KB   278 cinemas, attributes, platinum flag
      cinemas/<id>/movies                  ~100 KB  versions, labels, type arrays, sessions
      sessions/<id>                        ~15 KB   PRICES + SEAT MAP + auditorium
      movies/                              159 KB   catalogue and posters
      movies/coming                         96 KB   coming soon
      landings/                           9.77 MB   the entire CMS, 176 pages
      landings/<slug>                      varies   one page (cines-platino, imax, ...)
      ie/benefits                          119 KB   loyalty tiers and accrual rates
      loyalty/getSignUpOptions/cinema/<id>  ~4 KB   membership prices, per cinema
      promos/                               46 KB   active promotions
      articles/                            860 KB   news feed
      states/                                6 KB   states and areas
      modals/                              3.4 KB   home-page modals
      candybar/catalog?cinema_id=<id>        68 B   EMPTY for all 278

    cinetecanacional.net
      FAQ.php                               64 KB   ticket prices, rules, accessibility
      espacios_8.php                        39 KB   outlets, hours, menu links
      docs/espacios_812/CNMX/terraza/menuTerraza.pdf     439 KB, 10 pp, text layer
      docs/espacios_812/CNA/menuMirador.pdf            5.8 MB,  4 pp, text layer
      docs/espacios_812/CNMX/dulceria/menuDulceria.pdf  784 KB,  8 pp, NO text layer
      docs/espacios_812/CNMX/cafeteria812/menuDigital.pdf              404, dead link
