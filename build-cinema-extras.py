#!/usr/bin/env python3
"""Build docs/cinema-extras.json -- loyalty, formats in plain words, ticket price bands,
and food/alcohol per venue, for the 35 venues the app actually carries.

    /opt/homebrew/bin/python3 build-cinema-extras.py            # live pull, ~4 minutes
    /opt/homebrew/bin/python3 build-cinema-extras.py --cached   # reuse .raw-extras/

THREE THINGS THAT WILL BITE A RERUN, all measured rather than remembered:

1. USE THE HOMEBREW PYTHON. `/usr/bin/python3` links LibreSSL and gets 403 from hosts that
   fingerprint the ClientHello; the same URL over OpenSSL answers 200. macOS `curl` links
   the same LibreSSL, so header experiments against it answer the wrong question.
   See CINEMEX-API.md section 3.

2. `www.cinetecanacional.net` went into a LOCAL negative DNS cache mid-session on 9 Sep
   while 8.8.8.8 and 1.1.1.1 both answered 201.98.21.38 throughout. That reads exactly like
   their site being down. The address is pinned below as a fallback only -- normal
   resolution is tried first, so a genuine IP change still works.

3. A 200 FROM THAT HOST IS NOT A FILE. `docs/espacios_812/CNMX/cafeteria812/` answers 200
   with an HTML body whose <title> is "Error 404". Any probe of a directory path there has
   to read the body, not the status, or it will report files that do not exist.

WHAT IS NOT REPRODUCIBLE HERE, and is embedded as literal data instead: the Cineteca
dulceria menu is an image-only PDF -- 8 pages, 8 bytes of extractable text. Its prices were
recovered with macOS Vision OCR and then checked against the rendered page by eye, because
a two-column menu pairs a label with a price by POSITION and the OCR's reading order put
one $18.00 next to the wrong row. Every other menu price in this file is re-extracted from
the PDF on every build.
"""

import argparse, hashlib, json, os, re, socket, ssl, sys, time, urllib.error, urllib.request
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, ".raw-extras")
OUT = os.path.join(HERE, "docs", "cinema-extras.json")
PAGE = os.path.join(HERE, "docs", "index.html")

CX_KEY = "XXQha7vz4kdvoMSdixhN"
CX_BASE = "https://api.cinemex.com/rest/v2.38/"
CN_BASE = "https://www.cinetecanacional.net/"
CN_PINNED = "201.98.21.38"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140 Safari/537.36")
CTX = ssl.create_default_context()

_gai = socket.getaddrinfo


def _pinned_gai(host, port, *a, **k):
    if host and host.endswith("cinetecanacional.net"):
        try:
            return _gai(host, port, *a, **k)
        except Exception:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (CN_PINNED, port or 443))]
    return _gai(host, port, *a, **k)


socket.getaddrinfo = _pinned_gai

SOURCES = OrderedDict()

# Every source id this file can reference, with the url behind it. A `--cached` run serves
# some pulls off disk and so never calls note_source for them; without this table those
# ids would be referenced by the data and absent from `sources`, which is exactly the
# dangling reference the validator refuses.
SOURCE_URLS = {
    "cinemex_app_settings": CX_BASE + "app/settings",
    "cinemex_ie_benefits": CX_BASE + "ie/benefits",
    "cinemex_loyalty_signup": CX_BASE + "loyalty/getSignUpOptions/cinema/<id>",
    "cinemex_cinemas": CX_BASE + "cinemas/",
    "cinemex_cinema_movies": CX_BASE + "cinemas/<id>/movies",
    "cinemex_sessions_sweep": CX_BASE + "sessions/<id>",
    "cinemex_candybar_catalog": CX_BASE + "candybar/catalog?cinema_id=<id>",
    "cinemex_landing_platino": CX_BASE + "landings/cines-platino",
    "cinemex_landing_imax": CX_BASE + "landings/imax",
    "cinemex_landing_casa_de_arte": CX_BASE + "landings/casa-de-arte",
    "cinemex_landing_mania": CX_BASE + "landings/cinemex-mania-septiembre-2026",
    "cineteca_espacios": CN_BASE + "espacios_8.php",
    "cineteca_faq": CN_BASE + "FAQ.php",
    "cineteca_menu_terraza": CN_BASE + "docs/espacios_812/CNMX/terraza/menuTerraza.pdf",
    "cineteca_menu_mirador": CN_BASE + "docs/espacios_812/CNA/menuMirador.pdf",
    "cineteca_menu_dulceria": CN_BASE + "docs/espacios_812/CNMX/dulceria/menuDulceria.pdf",
    "cineteca_menu_fuente": CN_BASE + "docs/espacios_812/CNMX/fuente/menuFuente.pdf",
    "cineteca_menu_cafeteria": CN_BASE + "docs/espacios_812/CNMX/cafeteria812/menuDigital.pdf",
    "cinepolis_club_terms_gt": ("https://marcas.cinepolis.com.gt/marcas/club-cinepolis/"
                               "terminos-condiciones-ca/terminos-condiciones-guatemala.html"),
    "cinepolis_promo_microsite": "https://cloud.promocinepolis.com/reto-puntosporpeli",
    "wikipedia_es_dolby_atmos": "https://es.wikipedia.org/wiki/Dolby_Atmos",
    "wikipedia_es_imax": "https://es.wikipedia.org/wiki/IMAX",
    "wikipedia_es_4dx": "https://es.wikipedia.org/wiki/4DX",
}


def note_source(sid, url, status, nbytes, extra=None):
    rec = {"url": url, "http_status": status, "bytes": nbytes,
           "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    if extra:
        rec.update(extra)
    SOURCES[sid] = rec


def http(url, headers=None, timeout=90):
    req = urllib.request.Request(url, headers=dict(headers or {}))
    req.add_header("User-Agent", UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read()


def cx(path, sid=None, timeout=90):
    url = CX_BASE + path
    st, body = http(url, {"x-api-consumer-key": CX_KEY}, timeout)
    if sid:
        note_source(sid, url, st, len(body))
    return json.loads(body)


def cached(name, fn):
    """Write every raw pull to disk so analysis and reruns cost them nothing."""
    p = os.path.join(RAW, name)
    if ARGS.cached and os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    d = fn()
    os.makedirs(RAW, exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return d


# --------------------------------------------------------------- the app's own venues

def attribute_split():
    """Re-measure the primary/secondary format trap instead of quoting it.

    Deliberately aimed at two venues that HAVE Atmos rooms. A zero at a venue with no
    Atmos room cannot tell an empty field apart from an empty cinema, so a probe there
    would be evidence of nothing -- which is how this trap survived being looked for once
    already.
    """
    from collections import Counter
    prim, sec, typ = Counter(), Counter(), Counter()
    for cid in ("76", "32"):
        movies = cached("movies_%s.json" % cid,
                        lambda cid=cid: cx("cinemas/%s/movies" % cid,
                                           "cinemex_cinema_movies"))
        for m in movies:
            for v in (m.get("versions") or []):
                a = v.get("attributes") or {}
                for k in (a.get("primary") or []):
                    prim[k] += 1
                for k in (a.get("secondary") or []):
                    sec[k] += 1
                for k in (v.get("type") or []):
                    typ[k] += 1
        time.sleep(0.35)
    return {
        "venues_read": ["76 Antara Platino", "32 Parque Delta"],
        "venues_chosen_because": "both have Dolby Atmos rooms",
        "dolby_atmos": {"in_primary": prim["dolby_atmos"], "in_secondary": sec["dolby_atmos"],
                        "in_type": typ["dolby_atmos"]},
        "imax": {"in_primary": prim["imax"], "in_secondary": sec["imax"],
                 "in_type": typ["imax"]},
        "verdict": ("read `type` -- it is the union"
                    if prim["dolby_atmos"] == 0 and typ["dolby_atmos"] > 0
                    else "THE SPLIT CHANGED -- re-read CINEMEX-API.md section 6"),
    }


def app_venues():
    """The venue ids and format labels the built page actually carries.

    Read out of docs/index.html rather than hardcoded, because a venue id in this file that
    the app does not carry is a row nothing can ever render -- which is what the validator
    beside this script refuses.
    """
    page = open(PAGE, encoding="utf-8").read()
    i = page.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob -- run refresh-showtimes.py first")
    j = page.find("\n", i)
    blob = json.loads(page[i + len("const SHOWS="):j].rstrip().rstrip(";"))
    return blob


# --------------------------------------------------------------- 1. loyalty

CX_TIER_ORDER = ["one", "basic", "gold", "premium", "arena"]
CX_TIER_PUBLIC_NAME = {"one": "Cinemex Loop One", "basic": "Cinemex Loop Red",
                       "gold": "Cinemex Loop Gold", "premium": "Cinemex Loop Platino",
                       "arena": "Arena XP Loop"}


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    for a, b in (("&aacute;", "a"), ("&eacute;", "e"), ("&iacute;", "i"), ("&oacute;", "o"),
                 ("&uacute;", "u"), ("&ntilde;", "n"), ("&nbsp;", " "), ("&amp;", "&")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def build_loyalty(venue_ids):
    benefits = cached("benefits.json", lambda: cx("ie/benefits", "cinemex_ie_benefits"))
    signup = cached("loyalty_signup.json", lambda: fetch_signup(venue_ids))

    tiers = []
    for key in CX_TIER_ORDER:
        rows = benefits.get(key) or []
        accrual, quote = None, None
        for b in rows:
            t = strip_html(b.get("title"))
            m = re.match(r"Acumulaci[oó]n del (\d+)%", t)
            if m:
                accrual = int(m.group(1))
                quote = strip_html(b.get("description"))[:260]
                break
        if accrual is None:                     # arena states it as a plain benefit line
            for b in rows:
                t = strip_html(b.get("title"))
                m = re.match(r"(\d+)% en puntos", t)
                if m:
                    accrual = int(m.group(1))
                    quote = strip_html(b.get("description"))[:260]
                    break
        tiers.append({
            "api_key": key,
            "name": CX_TIER_PUBLIC_NAME[key],
            "points_accrual_percent": accrual,
            "benefit_count": len(rows),
            "quote_es": quote,
            "source": "cinemex_ie_benefits",
            "confidence": "operator_published" if accrual is not None else "unknown",
        })

    packages = defaultdict(dict)
    for cid, rec in signup.items():
        for o in ((rec.get("data") or {}).get("options") or []):
            packages[o["name"]][cid] = o
    pkgs = []
    for name in sorted(packages, key=lambda n: -len(packages[n])):
        per = packages[name]
        any_opt = next(iter(per.values()))
        prices = {cid: round(o["price"] / 100.0, 2) for cid, o in per.items()}
        vals = sorted(set(prices.values()))
        pkgs.append({
            "name": name,
            "id": any_opt.get("id"),
            "tickets_included": any_opt.get("quantity"),
            "price_mxn_by_venue": prices,
            "price_mxn_low": vals[0],
            "price_mxn_high": vals[-1],
            "varies_by_venue": len(vals) > 1,
            "benefits_es": [b.strip() for b in (any_opt.get("benefits") or [])],
            "benefits_note": ("the benefit strings are identical across venues for this "
                              "package; only the price differs"),
            "source": "cinemex_loyalty_signup",
            "confidence": "operator_published",
        })

    # The weekday combos, quoted. These are the member benefit with an actual peso figure
    # behind it, so they are worth carrying verbatim rather than summarised.
    combos, seen = [], set()
    for key in CX_TIER_ORDER:
        for b in (benefits.get(key) or []):
            title = strip_html(b.get("title"))
            desc = strip_html(b.get("description"))
            if not re.search(r"combo", title, re.I):
                continue
            day = None
            for d in ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado",
                      "Domingo", "cumple"):
                if d.lower() in (title + " " + desc).lower():
                    day = d
                    break
            fp = (title, desc[:120])
            if fp in seen:
                continue
            seen.add(fp)
            combos.append({"tier": CX_TIER_PUBLIC_NAME[key], "title": title,
                           "day": day, "detail_es": desc[:600],
                           "source": "cinemex_ie_benefits",
                           "confidence": "operator_published"})

    club = cached("club_gt.json", fetch_club_gt)
    promo = cached("promocinepolis.json", fetch_promocinepolis)

    return {
        "cinemex": {
            "programme_name": "Cinemex Loop",
            "programme_name_note": (
                "The brief called this 'Invitado Frecuente'. That name returns zero hits "
                "anywhere in Cinemex's own CMS. The legacy name that survives in their "
                "terms is 'Invitado Especial Cinemex PAYBACK' -- which is why the endpoint "
                "path is still /ie/ -- and the current public name is Cinemex Loop."),
            "tiers": tiers,
            "point_value": {
                "value_mxn": None,
                "confidence": "unknown",
                "source": None,
                "note": ("Cinemex says points are spendable as a means of payment -- "
                         "'dichos puntos pueden usarse como medio de pago' -- and never "
                         "states a points-to-pesos ratio anywhere in the 8.4 MB CMS or the "
                         "benefits payload. Do not show a peso value for a Cinemex point."),
            },
            "member_combos": combos,
            "membership_packages": pkgs,
            "packages_note": (
                "Prices are per venue and genuinely differ: Nivel Red - 5 boletos runs "
                "from $249 to $959 depending on which cinema you sign up at, and Cinemex's "
                "own benefit text says so -- 'El precio del paquete es de acuerdo con el "
                "cine seleccionado al momento de inscribirte y solo podras redimir tus "
                "boletos en dicho cine.'"),
        },
        "cinepolis": {
            "programme_name": "Club Cinepolis",
            "applies_to_app": False,
            "applies_to_app_note": (
                "No Cinepolis venue is in this app. Cinepolis' own site returns 403 to this "
                "network and ERR_FAILED inside his own Chrome -- a Cloudflare rule -- so it "
                "is not probed. Retry from Mexico City after 11 October. These rows are "
                "here so the app can explain the programme, not price a screening."),
            "accrual_percent": {
                "value": 5,
                "market": "Guatemala",
                "source": "cinepolis_club_terms_gt",
                "confidence": "third_party",
                "quote_es": ("La Tarjeta Club Cinepolis acumula puntos por el equivalente "
                             "al 5% sobre el total de las compras en Taquilla, Dulceria, "
                             "Coffee Tree y Spyral de Cinepolis tradicional, asi como en "
                             "Taquilla, Dulceria, Coffee Tree y menu de alimentos y "
                             "bebidas de Cinepolis VIP."),
                "note": ("AUTHORITATIVE FOR GUATEMALA ONLY. cinepolis.com.gt is a separate "
                         "registrable domain from the blocked cinepolis.com and answers "
                         "200. Nothing read here establishes the Mexican accrual rate."),
            },
            "points_expire": {
                "value": "31 December each year",
                "market": "Guatemala",
                "source": "cinepolis_club_terms_gt",
                "confidence": "third_party",
                "quote_es": ("Los puntos acumulados tienen vigencia hasta 31 de diciembre "
                             "de cada ano. Si no se utilizan los puntos antes de la fecha "
                             "anteriormente senalada se perderan."),
            },
            "point_value": [
                {"market": "Guatemala", "value": 1.0, "currency": "GTQ",
                 "source": "cinepolis_club_terms_gt", "confidence": "third_party",
                 "quote_es": "Cada punto equivale a un Quetzal, moneda oficial de Guatemala."},
                {"market": "Mexico", "value": 1.0, "currency": "MXN",
                 "source": "cinepolis_promo_microsite",
                 "confidence": "third_party_expired_page",
                 "quote_es": ("Puedes utilizar tus puntos Club Cinepolis en compras dentro "
                              "del cine, en taquilla, Dulceria, Baguis y Coffee Tree o en "
                              "nuestros canales digitales. Cada punto equivale a $1 peso."),
                 "note": ("Read from cloud.promocinepolis.com, a Cinepolis promotional "
                          "domain, at 200. The page's own promotion expired on 30 September "
                          "2024, so the sentence is Cinepolis' own wording about programme "
                          "mechanics on a page that is no longer current. It is consistent "
                          "with Guatemala's 1 point = 1 Quetzal. THIS CONTRADICTS the "
                          "'1 peso cada 10 puntos' figure that circulates on Mexican "
                          "consumer blogs; that figure has no primary source and is not "
                          "used here.")},
            ],
            "redemption_rules_gt": {
                "source": "cinepolis_club_terms_gt",
                "confidence": "third_party",
                "rules_es": [
                    "Para canjear los puntos en taquilla deberas acumular al menos el valor total del boleto.",
                    "Los puntos deberan acumularse en el momento de la compra, no se podra hacer posteriormente.",
                    "Las operaciones derivadas de la redencion de puntos, no genera nuevos puntos al programa.",
                    "No se podran canjear puntos por dinero en efectivo.",
                    "Los puntos de una Tarjeta Club Cinepolis no podran ser transferidos a otra.",
                ],
            },
        },
    }


def fetch_signup(venue_ids):
    out = {}
    for cid in venue_ids:
        try:
            d = cx("loyalty/getSignUpOptions/cinema/%s" % cid)
            out[cid] = {"status": 200, "data": d}
        except Exception as e:
            out[cid] = {"status": None, "error": str(e)[:140]}
        time.sleep(0.35)
    note_source("cinemex_loyalty_signup",
                CX_BASE + "loyalty/getSignUpOptions/cinema/<id>", 200, None,
                {"venues_fetched": len(out),
                 "venues_at_200": sum(1 for v in out.values() if v["status"] == 200)})
    return out


def fetch_club_gt():
    url = ("https://marcas.cinepolis.com.gt/marcas/club-cinepolis/terminos-condiciones-ca/"
           "terminos-condiciones-guatemala.html")
    st, body = http(url, {"Accept-Language": "es"})
    note_source("cinepolis_club_terms_gt", url, st, len(body))
    return {"html": body.decode("utf-8", "replace")}


def fetch_promocinepolis():
    url = "https://cloud.promocinepolis.com/reto-puntosporpeli"
    st, body = http(url, {"Accept-Language": "es"})
    note_source("cinepolis_promo_microsite", url, st, len(body))
    return {"html": body.decode("utf-8", "replace")}


# --------------------------------------------------------------- 2. formats, plain words
#
# confidence vocabulary, and it is the whole point of this section:
#   operator_published  Cinemex's own words, quoted, from their API or CMS
#   measured           computed from the API's own data by this build
#   third_party        Wikipedia or a Cinepolis regional site, with the url in sources
#   term_definition    the plain words define a standard industry term (Closed Caption)
#   label_translation  the plain words are only a translation of their display name;
#                      no mechanism is claimed, because none is published
#   unknown            plain words are null -- Cinemex publishes nothing and neither do we

FORMAT_WORDS = {
    # ---- what a screening is, and these are the ones the app renders today
    "traditional": dict(
        en="The ordinary screen. The cheapest ticket at any cinema that has one, and the "
           "one the Wednesday-and-Thursday $39 promo is aimed at.",
        es="La sala normal. El boleto mas barato de cualquier cine que la tenga, y el que "
           "entra en la promocion de $39 de miercoles y jueves.",
        confidence="measured",
        source="cinemex_sessions_sweep",
        why="Tradicional is the lowest adult price at every venue measured, and it is one "
            "of the two concepts the Mania terms name."),
    "premium": dict(
        en="Eleven pesos more than the ordinary screen, at each of the four cinemas here "
           "where both can be compared. Cinemex never says what the extra buys.",
        es="Once pesos mas que la sala normal, en los cuatro cines de aqui donde se pueden "
           "comparar. Cinemex no publica en ningun lado que incluye ese extra.",
        confidence="measured",
        source="cinemex_sessions_sweep",
        why="The gap is exactly +$11 at all four app venues that price both Tradicional "
            "and Premium on the same plain day -- Pabellon Cuauhtemoc 94 to 105 both "
            "dubbed and subtitled, Galerias 90 to 101, Loreto 105 to 116. Four pairs is a "
            "small sample and it is the whole sample there is; the absolute price still "
            "varies a lot by venue. The word 'Premium' appears in Cinemex's CMS only as "
            "part of a cinema name or in a promo exclusion list, never with a description.",
        cinemex_publishes_a_description=False),
    "platinum": dict(
        en="Reclining seats with food and drink brought to your seat, and a drinks menu "
           "that now includes Topo Chico Hard Seltzer. The most expensive format, and no "
           "promo price ever applies to it.",
        es="Butacas reclinables y servicio a la sala, con un menu de bebidas que ahora "
           "incluye Topo Chico Hard Seltzer. Es el formato mas caro y ninguna promocion "
           "aplica en el.",
        confidence="operator_published",
        source="cinemex_landing_platino",
        quote_es="Butacas reclinables, servicio a la sala, y ahora nuevo menu de bebidas "
                 "con Topo Chico Hard Seltzer",
        why="Quoted from their own Platino landing page. The 'no promo applies' half is "
            "measured: every Platino session priced identically on a promo day and a plain "
            "day, and the Mania terms exclude the concept by name."),
    "lang_sub": dict(
        en="Original soundtrack with Spanish subtitles.",
        es="Idioma original con subtitulos en espanol.",
        confidence="operator_published",
        source="cinemex_app_settings",
        why="Their own display name is 'Subtitulada'; the plain words are the standard "
            "meaning of that label in Mexican cinemas."),
    "lang_es": dict(
        en="Spoken in Spanish -- a foreign film dubbed, or a Mexican film in its own "
           "language.",
        es="Hablada en espanol: una pelicula extranjera doblada, o una mexicana en su "
           "idioma.",
        confidence="operator_published",
        source="cinemex_app_settings",
        why="Cinemex has a separate 'dubbed / Doblada' key and does not use it anywhere in "
            "this app, so lang_es carries both cases."),
    "dolby_atmos": dict(
        en="Object-based surround sound: speakers overhead as well as around you, so a "
           "sound can be placed and moved anywhere in the room rather than assigned to a "
           "fixed channel.",
        es="Sonido envolvente por objetos: bocinas arriba y alrededor, de modo que un "
           "sonido se coloca y se mueve en el espacio en lugar de vivir en un canal fijo.",
        confidence="third_party",
        source="wikipedia_es_dolby_atmos",
        why="Cinemex publishes no description. The definition is Dolby's own technology as "
            "described by Spanish Wikipedia. No channel count is claimed -- Cinemex "
            "publishes none, and a 7.1 figure would be a Cinepolis Macro XE claim."),
    "imax": dict(
        en="A very large, brighter screen with stadium seating, and a print remastered for "
           "the format -- up to 26% more picture on selected titles. Cinemex's most "
           "expensive ticket outside Platino.",
        es="Pantalla enorme y mas brillante con asientos tipo estadio, y una copia "
           "remasterizada para el formato, con hasta 26% mas de imagen en titulos "
           "selectos. El boleto mas caro de Cinemex fuera de Platino.",
        confidence="operator_published",
        source="cinemex_landing_imax",
        quote_es="PELICULAS DESARROLLADAS PARA IMAX. CAMARAS DE ALTA RESOLUCION: Alcance y "
                 "claridad incomparables. IMAGENES REMASTERIZADAS DIGITALMENTE: Mejora de "
                 "imagen (DMR) en todas las peliculas. HASTA UN 26% MAS DE IMAGEN: Titulos "
                 "seleccionados. DISENO INMERSIVO. SALAS DE CINE A MEDIDA: Asientos estilo "
                 "estadio para vistas unicas y claras desde donde sea. BRILLO INIGUALABLE: "
                 "Pantallas personalizadas para las imagenes mas brillantes.",
        why="CORRECTED. An earlier pass of this file said Cinemex publishes only marketing "
            "for IMAX and sourced the mechanism from Wikipedia. They publish a full "
            "description -- it is inside image `alt` attributes on their conoce-imax page, "
            "so a CMS reader that strips tags before searching finds nothing and concludes "
            "they say nothing. Spanish Wikipedia is kept as a second source for the screen "
            "geometry, which Cinemex does not give.",
        second_source="wikipedia_es_imax"),
    "imax_3d": dict(
        en="An IMAX screening in 3D. Nothing in this app uses it.",
        es="Funcion IMAX en 3D. Nada en esta app lo usa.",
        confidence="label_translation", source="cinemex_app_settings"),
    "infinity-vision": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="This is the awkward one: 150 showtimes in this app carry it, and the words "
            "'Infinity Vision' appear ZERO times in the 8.4 MB of Cinemex's CMS. They sell "
            "it and describe it nowhere. Do not fill this in by analogy with anything.",
        cinemex_publishes_a_description=False),
    "confort": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="Same shape as Infinity Vision: 'confort' appears ZERO times in the whole CMS. "
            "Sixteen screenings in the wider Mexico City box use it and none of them fall "
            "inside this app's radius, so it is not urgent -- but if a Confort venue ever "
            "enters the radius, do NOT explain it as Cinepolis' PLUUS. That would be a "
            "guess wearing a citation.",
        cinemex_publishes_a_description=False),
    "v3d": dict(
        en="A 3D screening; you wear the glasses.",
        es="Funcion en 3D; se usan los lentes.",
        confidence="label_translation", source="cinemex_app_settings"),
    "v4d": dict(
        en="Moving seats plus physical effects -- wind, water, scent, light -- timed to the "
           "film.",
        es="Asientos que se mueven mas efectos fisicos: viento, agua, aromas y luces, "
           "sincronizados con la pelicula.",
        confidence="third_party", source="wikipedia_es_4dx",
        why="Cinemex publishes no description of its 4D. The effects list is 4DX's, the "
            "format CJ 4DPlex licenses to Mexican chains, from Spanish Wikipedia. Cinemex "
            "does not use the 4DX brand name, so treat this as what a 4D room does "
            "generally, not as a Cinemex specification."),
    "hfr": dict(
        en="High frame rate -- more frames per second than the usual 24, so motion looks "
           "smoother. Nothing in this app uses it.",
        es="Alta tasa de cuadros: mas cuadros por segundo que los 24 normales, asi que el "
           "movimiento se ve mas fluido. Nada en esta app lo usa.",
        confidence="term_definition", source=None),
    "cc": dict(
        en="Closed captions on screen -- dialogue plus sound description, for deaf and "
           "hard-of-hearing viewers. Nothing in this app uses it.",
        es="Subtitulos para personas sordas: dialogo y descripcion de sonidos en pantalla. "
           "Nada en esta app lo usa.",
        confidence="term_definition", source=None),
    "ald": dict(
        en="A listening device you borrow that feeds the soundtrack straight to your "
           "hearing aid or headphones. Nothing in this app uses it.",
        es="Aparato de asistencia auditiva que se presta y envia el audio directo a tu "
           "auxiliar o audifonos. Nada en esta app lo usa.",
        confidence="term_definition", source=None),
    "atmos": dict(
        en="A second Dolby Atmos key in their dictionary. Nothing in this app uses it -- "
           "every Atmos screening here carries `dolby_atmos` instead.",
        es="Segunda clave de Dolby Atmos en su diccionario. Nada en esta app la "
           "usa: todas las funciones Atmos de aqui traen `dolby_atmos`.",
        confidence="measured", source="cinemex_sessions_sweep"),
    "dubbed": dict(
        en="'Doblada'. In the dictionary and unused -- Cinemex files dubbed screenings "
           "under `lang_es`.",
        es="'Doblada'. Existe en el diccionario y no se usa: Cinemex marca las funciones "
           "dobladas como `lang_es`.",
        confidence="measured", source="cinemex_sessions_sweep"),
    "lang_original": dict(
        en="'Idioma Original'. In the dictionary and not used by anything in this app.",
        es="'Idioma Original'. Existe en el diccionario y no se usa en esta app.",
        confidence="measured", source="cinemex_sessions_sweep"),
    "digital": dict(
        en="'Digital'. A legacy key from when digital projection was the thing worth "
           "naming. Nothing in this app uses it.",
        es="'Digital'. Clave heredada de cuando la proyeccion digital era lo que valia la "
           "pena nombrar. Nada en esta app lo usa.",
        confidence="label_translation", source="cinemex_app_settings"),
    # ---- auditorium products Cinemex names but never describes
    "macro": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="'Macropantalla' translates as an oversized screen and that is all the name "
            "says. Cinemex publishes no dimensions and no description, and nothing in "
            "this app uses the key. A screen-area figure would be Cinepolis' Macro XE."),
    "jumbo": dict(en=None, es=None, confidence="unknown", source=None,
                  why="Display name 'Jumbo' and nothing else, anywhere. Nothing in this app uses it."),
    "palco": dict(en=None, es=None, confidence="unknown", source=None,
                  why="'Palco Cinemex' appears in their CMS only inside promo exclusion "
                      "lists, never with a description. Nothing in this app uses it."),
    "dbox": dict(en=None, es=None, confidence="unknown", source=None,
                 why="D-BOX is a third-party motion-seat system, but Cinemex publishes "
                     "nothing about its own DBox rooms and no source for it was fetched. "
                     "Nothing in this app uses it."),
    "recliner": dict(en=None, es=None, confidence="unknown", source=None,
                     why="A dictionary key applied to zero screenings in this app. The only "
                         "sourced reclining-seat statement Cinemex makes is about Platino, "
                         "so say Platino reclines and claim it for nothing else."),
    "recliner_vip": dict(en=None, es=None, confidence="unknown", source=None,
                         why="As `recliner`: named, never described, not used by anything in this app."),
    "dine_in": dict(en=None, es=None, confidence="unknown", source=None,
                    why="Named, never described, not used by anything in this app."),
    "dinner_movie": dict(en=None, es=None, confidence="unknown", source=None,
                         why="Named, never described, not used by anything in this app."),
    "autocinema": dict(
        en="'Autocinema' -- a drive-in. Nothing in this app uses it.",
        es="'Autocinema': funcion para ver desde el coche. Nada en esta app lo usa.",
        confidence="label_translation", source="cinemex_app_settings"),
    "cinemom": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="Display name 'CineMa'. The name suggests screenings for parents with babies "
            "and Cinemex publishes nothing that says so, so it stays unknown. Unused in "
            "CDMX."),
    "misala": dict(en=None, es=None, confidence="unknown", source=None,
                   why="Display name 'Mi sala' and nothing else. Nothing in this app uses it."),
    "areana": dict(
        en="An Arena room -- Cinemex's gaming venue rather than a cinema screen. The Arena "
           "XP Loop membership is the one that buys play time by the hour.",
        es="Sala Arena: el espacio de videojuegos de Cinemex, no una sala de cine. La "
           "membresia Arena XP Loop es la que compra horas de juego.",
        confidence="operator_published", source="cinemex_loyalty_signup",
        why="The Arena XP Loop package's own benefit strings price play time by the hour "
            "and name game controllers, which is what establishes this is gaming and not a "
            "screen. No Arena venue is in this app."),
    "vArena": dict(en=None, es=None, confidence="unknown", source=None,
                   why="'Evento Arena'. Named, never described. Nothing in this app uses it."),
    "black_white": dict(
        en="'Blanco y Negro'. Named, never described, not used by anything in this app.",
        es="'Blanco y Negro'. Existe como clave, sin descripcion, y no se usa aqui.",
        confidence="label_translation", source="cinemex_app_settings"),
    "cx": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="'CinemeXtremo'. It appears 24 times in their CMS and every one is inside a "
            "promo exclusion list -- 'No aplica en Sala 3D, CinemeXtremo, Sala 4D, sala "
            "IMAX, Palco Cinemex' -- so what IS sourced is that Cinemex treats it as a "
            "premium format outside every ticket package, and what is NOT sourced is "
            "anything about the room. Three app venues carry the complex-level `cx` flag "
            "and no screening in this app is labelled with it.",
        cinemex_publishes_a_description=False),
    # ---- catalogue labels: these describe the FILM, not the room
    "art": dict(
        en="Casa de Arte: independent distributors, auteur classics and current "
           "art-house work, on a permanent screen.",
        es="Casa de Arte: distribuidoras independientes, clasicos de cine de autor y "
           "propuestas actuales, en una sala permanente.",
        confidence="operator_published", source="cinemex_landing_casa_de_arte",
        quote_es="Casa de Arte albergara peliculas de distribuidoras independientes, asi "
                 "como filmes con caracteristicas de los clasicos de cine de autor y dara "
                 "espacio a proyectos independientes actuales, con propuestas artisticas "
                 "interesantes, innovadoras y reconocidas."),
    "alt": dict(
        en="'Espacio Alternativo' -- something other than a film: a concert, an opera, a "
           "recorded stage show.",
        es="'Espacio Alternativo': algo que no es una pelicula, como un concierto, una "
           "opera o una obra grabada.",
        confidence="label_translation", source="cinemex_app_settings",
        why="Their `contenido-alternativo` CMS page is unfinished and still carries lorem "
            "ipsum, so the plain words rest on the label and on what the catalogue holds, "
            "not on a description."),
    "alt_sports": dict(
        en="'Espacio Alternativo Deportes' -- a live match or sporting event on the screen.",
        es="'Espacio Alternativo Deportes': un partido o evento deportivo en pantalla.",
        confidence="label_translation", source="cinemex_app_settings"),
    "preview": dict(en="A pre-release screening, before the film's official opening.",
                    es="Funcion previa al estreno oficial.",
                    confidence="label_translation", source="cinemex_app_settings"),
    "premiere": dict(en="A new release.", es="Estreno.",
                     confidence="label_translation", source="cinemex_app_settings"),
    "presale": dict(en="Tickets on sale ahead of the run starting.",
                    es="Boletos en preventa antes de que arranque la temporada.",
                    confidence="label_translation", source="cinemex_app_settings"),
    "exclusive": dict(en="Showing at Cinemex and not at other chains.",
                      es="Exclusiva de Cinemex.",
                      confidence="label_translation", source="cinemex_app_settings"),
    "rerelease": dict(en="An older film back in cinemas.",
                      es="Reestreno: una pelicula antigua de vuelta en cartelera.",
                      confidence="label_translation", source="cinemex_app_settings"),
    "fest": dict(en="Part of a festival programme.", es="Parte de un festival.",
                 confidence="label_translation", source="cinemex_app_settings"),
    "classics": dict(en="A classic, programmed as a revival.",
                     es="Clasico programado como reestreno.",
                     confidence="label_translation", source="cinemex_app_settings"),
    "cineclassics": dict(en="'CineClassics' -- their branded classics strand.",
                         es="'CineClassics': su ciclo de clasicos.",
                         confidence="label_translation", source="cinemex_app_settings"),
    "flashback": dict(en="'Flashback Cinema' -- another branded revival strand.",
                      es="'Flashback Cinema': otro ciclo de reestrenos.",
                      confidence="label_translation", source="cinemex_app_settings"),
    "oscar_nominee": dict(en="Oscar-nominated.", es="Nominada al Oscar.",
                          confidence="label_translation", source="cinemex_app_settings"),
    "oscar_winner": dict(en="Oscar-winning.", es="Ganadora del Oscar.",
                         confidence="label_translation", source="cinemex_app_settings"),
    "rated_c": dict(
        en="Rated C by Mexico's RTC: adults only, 18 and over.",
        es="Clasificacion C de la RTC: solo adultos, mayores de 18.",
        confidence="term_definition", source=None,
        why="Their display name is 'Solo adultos'. The 18-and-over reading is the RTC "
            "letter's standard meaning, which the Cineteca FAQ also spells out."),
    "plus21": dict(en="21 and over.", es="Solo mayores de 21.",
                   confidence="label_translation", source="cinemex_app_settings"),
    "masterpass_only": dict(en="Buyable only through Masterpass. A payment restriction, "
                               "not a format.",
                            es="Solo se compra con Masterpass. Es una restriccion de pago, "
                               "no un formato.",
                            confidence="label_translation", source="cinemex_app_settings"),
}

CINEMA_ATTR_WORDS = {
    "platinum": dict(
        en="The complex has Platino screens: reclining seats, service at your seat.",
        es="El complejo tiene salas Platino: butacas reclinables y servicio a la sala.",
        confidence="operator_published", source="cinemex_landing_platino"),
    "premium": dict(en="The complex has Premium screens, which cost more than its ordinary "
                       "ones.",
                    es="El complejo tiene salas Premium, mas caras que las normales.",
                    confidence="measured", source="cinemex_sessions_sweep"),
    "market": dict(
        en=None, es=None, confidence="unknown", source=None,
        why="What IS sourced: Cinemex treats Market as a separate concept from Tradicional "
            "and Premium and excludes it from the $39 promo by name, and the price sweep "
            "confirms it -- Premium at the four Market complexes in this app costs the same "
            "on a promo day as on a plain one, while Premium everywhere else drops to $39. "
            "What is NOT sourced is anything about the venue itself. The brief's 'Market "
            "means the bigger snack bar' has no source and is not recorded here; note also "
            "that the snack API is switched off nationally, so a snack-bar claim could not "
            "be checked even in principle.",
        cinemex_publishes_a_description=False),
    "3d": dict(en="The complex has at least one 3D screen.",
               es="El complejo tiene al menos una sala 3D.",
               confidence="label_translation", source="cinemex_app_settings"),
    "4d": dict(en="The complex has a 4D room -- moving seats and physical effects.",
               es="El complejo tiene sala 4D: asientos en movimiento y efectos fisicos.",
               confidence="third_party", source="wikipedia_es_4dx"),
    "cx": dict(en=None, es=None, confidence="unknown", source=None,
               why="See the `cx` note under formats: named in exclusion lists, never "
                   "described."),
    "art": dict(en="The complex has a Casa de Arte screen for independent and auteur films.",
                es="El complejo tiene sala Casa de Arte para cine independiente y de autor.",
                confidence="operator_published", source="cinemex_landing_casa_de_arte"),
    "cinemom": dict(en=None, es=None, confidence="unknown", source=None,
                    why="'CineMa'. Named, never described."),
    "Infinity Vision": dict(en=None, es=None, confidence="unknown", source=None,
                            why="Zero mentions in the entire CMS. See the format note."),
}


def build_formats(blob):
    settings = cached("settings.json", lambda: cx("app/settings", "cinemex_app_settings"))
    movie = settings["attributes"]["movies"]
    cinema = settings["attributes"]["cinemas"]

    # how many of the app's own screenings carry each key -- a real number, computed here
    use = defaultdict(int)
    for c in blob["cin"]:
        for row in c["s"]:
            for k in blob["fmts"][row[1]]["t"]:
                use[k] += 1

    out = {"vocabulary": {
        "operator_published": ("The venue operator's own words, quoted, from their API, CMS "
                               "or site."),
        "measured": "Computed from the API's own data by this build.",
        "third_party": "Wikipedia or a Cinepolis regional site; the url is in `sources`.",
        "term_definition": "The plain words define a standard industry term.",
        "label_translation": ("The plain words only translate Cinemex's display name. No "
                              "mechanism is claimed, because none is published."),
        "unknown": "No source exists. plain_en and plain_es are null on purpose.",
        # The four below name a provenance specific enough to be worth spelling out, and
        # they are used outside the formats section. They live here because this is the
        # one place the vocabulary is declared, and the build refuses to write a
        # confidence value that is not in this dict.
        "ocr_vision_verified_visually": ("An image-only PDF, read with macOS Vision OCR "
                                         "and then checked against the rendered page by "
                                         "eye, because the pairing of a label to a price "
                                         "is positional."),
        "pdf_text_layer_two_extractors_agree": ("Read twice off the same PDF page, with "
                                                "pdftotext -layout and with macOS Vision "
                                                "OCR, and the two agree letter for "
                                                "letter."),
        "format_level_inference": ("The operator publishes the statement about the FORMAT "
                                   "and does not name this venue. True of the format, "
                                   "unconfirmed for this address."),
        "third_party_expired_page": ("The operator's own wording, on a page whose "
                                     "promotion has expired. Their words, not current."),
    }, "screening_attributes": {}, "complex_attributes": {}}

    for key, meta in movie.items():
        w = FORMAT_WORDS.get(key, {})
        rec = {
            "display_name_es": meta.get("display_name"),
            "scope": meta.get("type"),
            "plain_en": w.get("en"),
            "plain_es": w.get("es"),
            "confidence": w.get("confidence", "unknown"),
            "source": w.get("source"),
            "app_showtimes_using_it": use.get(key, 0),
            "in_use_in_app": use.get(key, 0) > 0,
        }
        for extra in ("quote_es", "why", "cinemex_publishes_a_description"):
            if extra in w:
                rec[extra] = w[extra]
        if key not in FORMAT_WORDS:
            rec["why"] = ("Not written up: the key exists in Cinemex's dictionary and "
                          "nothing in this app uses it.")
        out["screening_attributes"][key] = rec

    for key, meta in cinema.items():
        w = CINEMA_ATTR_WORDS.get(key, {})
        rec = {
            "display_name_es": meta.get("display_name"),
            "scope": "complex",
            "plain_en": w.get("en"),
            "plain_es": w.get("es"),
            "confidence": w.get("confidence", "unknown"),
            "source": w.get("source"),
        }
        for extra in ("quote_es", "why", "cinemex_publishes_a_description"):
            if extra in w:
                rec[extra] = w[extra]
        out["complex_attributes"][key] = rec
    return out


# --------------------------------------------------------------- 3. ticket pricing

# The promo window Cinemex's own CMS declares for this month. The band sweep needs one day
# inside it and one outside, because the discount is a DIFFERENT TICKET PRODUCT rather than
# a discount field on the ordinary one.
PROMO_DAYS = ["2026-09-10", "2026-09-09"]
PLAIN_DAYS = ["2026-09-11", "2026-09-12", "2026-09-13", "2026-09-14", "2026-09-15"]


def build_pricing(blob):
    prices = cached("prices.json", lambda: fetch_prices(blob))
    mania = cached("landing_mania.json",
                   lambda: cx("landings/cinemex-mania-septiembre-2026",
                              "cinemex_landing_mania"))
    mania_terms = None
    for p in (mania if isinstance(mania, list) else [mania]):
        for pg in (p.get("pages") or []):
            h = ((pg.get("content") or {}).get("html")) or ""
            t = strip_html(h)
            if "39" in t and "Vigente" in t:
                mania_terms = t[:900]
                break
    venues = defaultdict(dict)
    for r in prices:
        if r.get("status") != 200:
            venues[r["cinema_id"]].setdefault(r["fmt_label"], {})[r["band"]] = {
                "priced": False, "note": "the sessions endpoint did not answer",
                "session_id": r["session_id"], "confidence": "unknown", "source": None}
            continue
        tickets = [{"name": t["name"], "price_mxn": round(t["price"] / 100.0, 2),
                    "booking_fee_mxn": round((t["fee"] or 0) / 100.0, 2),
                    "max_per_order": t["max"]} for t in r["tickets"]]
        rec = {
            "priced": bool(tickets),
            "day_read": r["day"],
            "session_id": r["session_id"],
            "auditorium": r["auditorium_name"],
            "screen_number": r["screen_number"],
            "seats": r["seats"],
            "wheelchair_spaces": r["wheelchair"],
            "tickets": tickets,
            "adult_price_mxn": max((t["price_mxn"] for t in tickets), default=None),
            "cheapest_price_mxn": min((t["price_mxn"] for t in tickets), default=None),
            "source": "cinemex_sessions_sweep",
            "confidence": "measured",
        }
        if not tickets:
            rec["note"] = ("this session answered 200 with an EMPTY tickets array. A reader "
                           "must not assume the table is populated just because the request "
                           "succeeded.")
            rec["confidence"] = "unknown"
            rec["adult_price_mxn"] = None
            rec["cheapest_price_mxn"] = None
        venues[r["cinema_id"]].setdefault(r["fmt_label"], {})[r["band"]] = rec

    return {
        "cinemex": {
            "unit": "MXN, from the API's centavos value divided by 100",
            "booking_fee": {"value_mxn": 0.0, "confidence": "measured",
                            "source": "cinemex_sessions_sweep",
                            "note": "fee and tax read 0 on all 257 ticket products swept"},
            "bands_explained": (
                "`promo` is a session read inside Cinemex's own Mania window (Mon 7 to Thu "
                "10 September); `plain` is one read after it. The discount arrives as a "
                "different ticket product -- 'CINEMEX MANIA' or 'CINEMEX MANIA PREMIUM' at "
                "$39 -- rather than as a discount on 'ADULTO', so an app reads it for free "
                "by reading the ticket name."),
            "promo_rules": [
                {
                    "name": "Cinemexmania, September 2026",
                    "price_mxn": 39.0,
                    "days": "Monday to Thursday",
                    "window": "2026-09-07 to 2026-09-10",
                    "applies_to_concepts": ["Tradicional", "Premium"],
                    "applies_to_formats": ["2D", "3D"],
                    "excluded_formats": ["IMAX", "4D", "Dolby ATMOS"],
                    "excluded_concepts": ["Market", "Platino"],
                    "channels": ["punto de venta", "web", "app"],
                    "also_excluded": ["premieres", "funciones especiales", "preventa",
                                      "other promotions and discounts"],
                    "source": "cinemex_landing_mania",
                    "confidence": "operator_published",
                    "quote_es": mania_terms,
                    "corroboration": (
                        "Measured independently and it agrees on both halves. 33 of the 63 "
                        "(venue, format) pairs with a price in both bands dropped to $39 "
                        "on the promo day, and every one of the 33 is Tradicional or "
                        "Premium. Of the 30 that did not move, 28 are Platino, IMAX or "
                        "Dolby Atmos, or Premium at one of the four venues with Market in "
                        "the name -- exactly the exclusion list. Not one pair got MORE "
                        "expensive on the promo day. The two remaining are the per-film "
                        "case in `traps` below."),
                    "market_naming_wrinkle": (
                        "Four app venues have Market in the name -- Reforma 222 Market, "
                        "Patriotismo Market, Galerias Insurgentes Market, Antara Market -- "
                        "and only three carry the `market` complex attribute. Reforma 222 "
                        "Market does not, and it still prices like a Market venue: none of "
                        "its three formats moved on the promo day. So to decide whether "
                        "the promo can apply, trust the ticket product the session returns "
                        "and not the complex's attribute list."),
                },
                {
                    "name": "A Wednesday product exists for the formats Mania excludes",
                    "price_mxn": None,
                    "days": "Wednesday",
                    "source": "cinemex_sessions_sweep",
                    "confidence": "measured",
                    "note": (
                        "This corrects the flat reading that IMAX and Atmos never discount. "
                        "Three Wednesday-only ticket products turned up in the sweep, each "
                        "on a format the Mania terms exclude: 'MIERCOLES IMAX EST1' at $120 "
                        "for IMAX Espanol at Parque Delta, 'CX MIERCOLES EST1' at $108 and "
                        "'CX MIERCOLES' at $75 for Dolby Atmos Subtitulada at Parque Delta "
                        "and Universidad. It is a separate Wednesday discount, not Mania, "
                        "and no CMS page for it was found -- so the rule behind it is "
                        "unsourced and only these three observations are real."),
                },
            ],
            "traps": [
                ("The promo is a ticket PRODUCT, not a discount field. Reading only "
                 "'ADULTO' and looking for a lower number finds nothing on a promo day, "
                 "because 'ADULTO' is simply absent."),
                ("Which film is in the slot matters, and it is not a per-venue property. "
                 "Miguel Angel de Quevedo priced Premium Espanol at $39 and Premium "
                 "Subtitulada at $116 on the SAME day, 10 September -- sessions 65622752 "
                 "and 65569681. The Mania terms exclude premieres, preventa and funciones "
                 "especiales, so the film in the slot decides it. Treat the rule as the "
                 "rule and these rows as observations; never show a venue-and-format promo "
                 "price as though it applied to every film."),
                ("A 200 can carry an empty `tickets` array. One of the 140 sessions swept "
                 "did."),
            ],
            "venues": {k: v for k, v in venues.items()},
        },
        "cineteca": {
            "unit": "MXN",
            "general_mxn": 70.0,
            "reduced_mxn": 50.0,
            "reduced_applies_to": ["under 25", "students", "seniors"],
            "cheap_days": {"days": ["Tuesday", "Wednesday"], "price_mxn": 50.0,
                           "applies_to": "any screening",
                           "excluded": ["Muestra", "Foro", "Talento emergente"]},
            "max_tickets_per_session": 8,
            "source": "cineteca_faq",
            "confidence": "operator_published",
            "quote_es": ("$70 entrada general y $50 para menores de 25 anos, estudiantes y "
                         "adultos mayores. Martes y miercoles, ambos dias el costo del "
                         "boleto es de $50 para cualquier funcion (Este descuento no aplica "
                         "para Muestra, Foro y Talento emergente)."),
            "listings_refresh": {"value": "Thursdays after 14:00", "source": "cineteca_faq",
                                 "confidence": "operator_published"},
        },
    }


def fetch_prices(blob):
    days, fmts = blob["days"], blob["fmts"]
    idx = {}
    for c in blob["cin"]:
        if not str(c["id"]).isdigit():
            continue
        per = idx.setdefault(str(c["id"]), {})
        for fid, fi, di, mins, av, cid, sala in c["s"]:
            if cid and cid.isdigit():
                per.setdefault(fi, {}).setdefault(days[di], []).append(cid)

    jobs = []
    for cin, per in idx.items():
        for fi, byday in per.items():
            for band, prefs in (("promo", PROMO_DAYS), ("plain", PLAIN_DAYS)):
                for d in prefs:
                    if byday.get(d):
                        jobs.append((cin, fi, band, d, byday[d][-1]))
                        break

    out = []
    for n, (cin, fi, band, day, sid) in enumerate(jobs, 1):
        rec = {"cinema_id": cin, "fmt_index": fi, "fmt_label": fmts[fi]["l"],
               "fmt_type": fmts[fi]["t"], "band": band, "day": day, "session_id": sid}
        try:
            d = cx("sessions/%s" % sid, timeout=45)
            rec["status"] = 200
            for k in ("auditorium_name", "screen_number", "seatallocation", "adults_only",
                      "candybar", "extreme", "premium"):
                rec[k] = d.get(k)
            rec["tickets"] = [{"id": t.get("id"), "name": t.get("name"),
                               "price": t.get("price"), "fee": t.get("fee"),
                               "tax": t.get("tax"), "max": t.get("max")}
                              for t in (d.get("tickets") or [])]
            seats = wc = 0
            for row in (d.get("layout") or []):
                for s in (row.get("seats") or []):
                    if s.get("type") in ("regular", "wheelchair", "wheelchair-companion"):
                        seats += 1
                    if s.get("type") == "wheelchair":
                        wc += 1
            rec["seats"], rec["wheelchair"] = seats, wc
        except Exception as e:
            rec["status"] = None
            rec["error"] = str(e)[:140]
        out.append(rec)
        if n % 20 == 0:
            print("  prices %d/%d" % (n, len(jobs)), flush=True)
        time.sleep(0.35)
    note_source("cinemex_sessions_sweep", CX_BASE + "sessions/<id>", 200, None,
                {"sessions_read": len(out),
                 "sessions_at_200": sum(1 for r in out if r.get("status") == 200),
                 "bands": "one inside the Mania window, one outside, per venue and format"})
    return out


# --------------------------------------------------------------- 4. food and alcohol

# The Cineteca dulceria menu is the one thing in this file that a rerun cannot regenerate:
# 8 image-only pages, 8 bytes of extractable text. Recovered with macOS Vision OCR at
# 300 dpi, then every label-to-price pairing checked against the rendered page by eye --
# necessary, because the OCR's reading order put page 8's lone $18.00 beside the wrong row
# and only the image settles which row owns it.
DULCERIA = {
    "combos": [
        {"name": "Combo 1", "contents_es": "1 palomitas grandes, 2 bebidas, 1 chocolate",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 150.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 155.0}],
         "page": 1},
        {"name": "Combo 2", "contents_es": "1 palomitas grandes, 2 bebidas",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 132.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 138.0}],
         "page": 2},
        {"name": "Combo 3", "contents_es": "1 palomitas medianas, 1 bebida, 1 pasitas o gomitas",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 102.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 109.0}],
         "page": 3},
        {"name": "Combo 4", "contents_es": "1 palomitas chicas, 1 bebida, 1 gomitas",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 85.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 95.0}],
         "page": 4},
        {"name": "Combo 5", "contents_es": "1 palomitas grandes, 2 Icee medianos",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 187.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 193.0}],
         "page": 5},
        {"name": "Combo Mix", "contents_es": "1 palomitas grandes, 1 bebida, 1 Icee mediano",
         "prices": [{"variant_es": "palomitas saladas", "price_mxn": 152.0},
                    {"variant_es": "palomitas de caramelo o combinadas", "price_mxn": 159.0}],
         "page": 6},
    ],
    "combo_drink_choice_es": "Bebidas a elegir: refresco vaso mediano, lata, o agua 600 ml",
    "sections": [
        {"section_es": "Bebidas", "page": 7, "items": [
            {"name_es": "Agua natural Ciel 600 ml", "price_mxn": 26.0},
            {"name_es": "Agua natural Ciel 1 lt", "price_mxn": 31.0},
            {"name_es": "Ciel mineralizada 600 ml", "price_mxn": 31.0},
            {"name_es": "Jugo del Valle-Frut", "price_mxn": 31.0},
            {"name_es": "Boing", "price_mxn": 31.0},
            {"name_es": "Fuze Tea", "price_mxn": 34.0},
            {"name_es": "Refresco vaso mediano", "price_mxn": 31.0},
            {"name_es": "Refresco vaso grande", "price_mxn": 41.0},
            {"name_es": "Coca Cola Regular", "price_mxn": 33.0},
            {"name_es": "Coca Cola Light", "price_mxn": 33.0},
            {"name_es": "Coca Cola sin azucar", "price_mxn": 33.0},
            {"name_es": "Fanta", "price_mxn": 33.0},
            {"name_es": "Sidral", "price_mxn": 33.0},
            {"name_es": "Sprite", "price_mxn": 33.0},
            {"name_es": "ICEE vaso mediano", "price_mxn": 60.0},
            {"name_es": "ICEE vaso grande", "price_mxn": 67.0},
        ]},
        {"section_es": "Palomitas", "page": 7, "items": [
            {"name_es": "Palomitas saladas chicas", "price_mxn": 50.0},
            {"name_es": "Palomitas saladas medianas", "price_mxn": 63.0},
            {"name_es": "Palomitas saladas grandes", "price_mxn": 72.0},
            {"name_es": "Palomitas caramelo chicas", "price_mxn": 55.0},
            {"name_es": "Palomitas caramelo medianas", "price_mxn": 70.0},
            {"name_es": "Palomitas caramelo grandes", "price_mxn": 80.0},
            {"name_es": "Palomitas combinadas medianas", "price_mxn": 70.0},
            {"name_es": "Palomitas combinadas grandes", "price_mxn": 76.0},
            {"name_es": "Papas horneadas", "price_mxn": 50.0},
        ]},
        {"section_es": "Dulceria", "page": 8, "items": [
            {"name_es": "Galletas (Chokis, Emperador, Florentinas)", "price_mxn": 31.0},
            {"name_es": "Dulces (Panditas, Almendras, Moritas, Chocoretas, Dulcigomas, "
                        "Kranky, Paleta Payaso)", "price_mxn": 24.0},
            {"name_es": "Bubulubu", "price_mxn": 18.0},
            {"name_es": "Laposse pasitas con chocolate", "price_mxn": 24.0},
            {"name_es": "Cacahuates (Enchilado, Japones, Sal y limon, Hot Nuts)",
             "price_mxn": 34.0},
            {"name_es": "Chocolates (M&M's Luneta, M&M's Peanuts, Milky Way, Snickers, "
                        "Crunch)", "price_mxn": 34.0},
        ]},
    ],
}


def pdf_text(path, first=None, last=None):
    import subprocess
    cmd = ["/opt/homebrew/bin/pdftotext", "-layout"]
    if first:
        cmd += ["-f", str(first), "-l", str(last or first)]
    cmd += [path, "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def fetch_cineteca():
    """The pages and menu PDFs. Every one is checked by BODY, not by status: this host
    answers 200 with an 'Error 404' page for a directory path."""
    os.makedirs(os.path.join(RAW, "cineteca"), exist_ok=True)
    got = {}
    targets = [
        ("cineteca_espacios", "espacios_8.php", "espacios_8.html"),
        ("cineteca_faq", "FAQ.php", "faq.html"),
        ("cineteca_menu_terraza", "docs/espacios_812/CNMX/terraza/menuTerraza.pdf",
         "menuTerraza.pdf"),
        ("cineteca_menu_mirador", "docs/espacios_812/CNA/menuMirador.pdf", "menuMirador.pdf"),
        ("cineteca_menu_dulceria", "docs/espacios_812/CNMX/dulceria/menuDulceria.pdf",
         "menuDulceria.pdf"),
        ("cineteca_menu_fuente", "docs/espacios_812/CNMX/fuente/menuFuente.pdf",
         "menuFuente.pdf"),
        ("cineteca_menu_cafeteria", "docs/espacios_812/CNMX/cafeteria812/menuDigital.pdf",
         "menuCafeteria.pdf"),
    ]
    for sid, path, name in targets:
        url = CN_BASE + path
        dest = os.path.join(RAW, "cineteca", name)
        if ARGS.cached and os.path.exists(dest):
            body = open(dest, "rb").read()
            got[sid] = {"status": 200, "path": dest, "md5": hashlib.md5(body).hexdigest()}
            continue
        try:
            st, body = http(url)
            if b"Error 404" in body[:400]:
                got[sid] = {"status": st, "path": None,
                            "note": "200 whose body is their Error 404 page"}
                note_source(sid, url, st, len(body),
                            {"note": "200 whose body is their Error 404 page"})
                continue
            open(dest, "wb").write(body)
            md5 = hashlib.md5(body).hexdigest()
            got[sid] = {"status": st, "path": dest, "md5": md5}
            note_source(sid, url, st, len(body), {"md5": md5})
        except urllib.error.HTTPError as e:
            got[sid] = {"status": e.code, "path": None}
            note_source(sid, url, e.code, None)
        time.sleep(0.3)
    return got


# The two priced drinks lists, read out of the PDFs' own text layers with
# `pdftotext -layout` AND independently off the rendered page with macOS Vision OCR. The
# two extractors agree letter for letter on every row below.
#
# THEY ARE EMBEDDED RATHER THAN PARSED ON EVERY BUILD, and the first version of this file
# is why. A regex of the shape `label ... (\d+)` reads
#
#     Copa L.A Cetto o Las Moras 150 ml.    $123.00
#
# as a drink costing 150 pesos, because "150 ml" matches before the price does. It produced
# eighteen Terraza rows of which twelve were bottle volumes wearing a peso sign. A price in
# his app has to be right, so the verified table is the data and `menu_drift()` below
# re-reads the PDF on every build purely to shout when the menu changes underneath it.
TERRAZA_DRINKS = [
    {"name_es": "Botellin L.A Cetto 187 ml (tinto, blanco o rosado)", "price_mxn": 148.0, "kind": "wine"},
    {"name_es": "Botella L.A Cetto 375 ml (tinto o blanco)", "price_mxn": 278.0, "kind": "wine"},
    {"name_es": "Copa L.A Cetto o Las Moras 150 ml", "price_mxn": 123.0, "kind": "wine"},
    {"name_es": "Botella L.A Cetto o Las Moras 750 ml", "price_mxn": 510.0, "kind": "wine"},
    {"name_es": "Copa Casa Madero 3V tinto 150 ml", "price_mxn": 205.0, "kind": "wine"},
    {"name_es": "Botella Casa Madero 3V tinto 750 ml", "price_mxn": 972.0, "kind": "wine"},
    {"name_es": "Cerveza nacional 355 ml (Negra Modelo, Modelo Especial, Bohemia clara, "
                "obscura, Weizen o Cristal, XX Ambar, XX Lager)", "price_mxn": 62.0, "kind": "beer"},
    {"name_es": "Cerveza artesanal 355 ml (Tempus, Lagunitas IPA, Jabali)",
     "price_mxn": 94.0, "kind": "beer"},
    {"name_es": "Cerveza de barril Modelo 500 ml", "price_mxn": 87.0, "kind": "beer"},
    {"name_es": "Stella Artois botella o barril 330 ml", "price_mxn": 90.0, "kind": "beer"},
    {"name_es": "Clericot", "price_mxn": 134.0, "kind": "wine_cocktail"},
    {"name_es": "Sangria", "price_mxn": 133.0, "kind": "wine_cocktail"},
    {"name_es": "Calimocho", "price_mxn": 112.0, "kind": "wine_cocktail"},
    {"name_es": "Tinto de verano", "price_mxn": 133.0, "kind": "wine_cocktail"},
    {"name_es": "Carajillo", "price_mxn": 125.0, "kind": "spirit_cocktail",
     "note": "the menu does not name the liqueur"},
    {"name_es": "Clamato", "price_mxn": 50.0, "kind": "mixer",
     "note": "sits in the VINOS Y CERVEZAS section but is not itself alcoholic"},
    {"name_es": "Tarro michelado", "price_mxn": 17.0, "kind": "mixer",
     "note": "a prepared glass, not a drink"},
    {"name_es": "Tarro cubano", "price_mxn": 17.0, "kind": "mixer",
     "note": "a prepared glass, not a drink"},
]
TERRAZA_DRINKS_EXCLUDED = [
    {"raw_line": "Botella    $835.00",
     "why": ("The menu names no wine on this line -- it reads only 'Botella'. Both "
             "extractors read it identically, so the gap is in the menu and not in the "
             "reading. Left out rather than guessed at.")},
]
MIRADOR_DRINKS = [
    {"name_es": "Copa L.A Cetto 150 ml", "price_mxn": 118.0, "kind": "wine"},
    {"name_es": "Copa 3V 150 ml", "price_mxn": 195.0, "kind": "wine"},
    {"name_es": "Botellin L.A Cetto 187 ml", "price_mxn": 129.0, "kind": "wine"},
    {"name_es": "Botellin L.A Cetto 375 ml", "price_mxn": 244.0, "kind": "wine"},
    {"name_es": "Botella tinto L.A Cetto Syrah 750 ml", "price_mxn": 470.0, "kind": "wine"},
    {"name_es": "Botella Casa Madero 750 ml", "price_mxn": 920.0, "kind": "wine"},
    {"name_es": "Cerveza nacional", "price_mxn": 56.0, "kind": "beer"},
    {"name_es": "Cerveza artesanal 355 ml", "price_mxn": 95.0, "kind": "beer"},
    {"name_es": "Stella Artois", "price_mxn": 90.0, "kind": "beer"},
]


def menu_drift(path, page, table):
    """Re-read the PDF and report whether the verified table still describes it.

    Deliberately NOT a parser: it only asks whether every price in the table is still
    present on that page, and whether the page has grown prices the table has never seen.
    Either answer means a human has to look at the menu again, and the build says so
    instead of shipping a number that has quietly changed.
    """
    if not path or not os.path.exists(path):
        return {"checked": False, "note": "the PDF did not download on this run"}
    text = pdf_text(path, page, page)
    on_page = set()
    for m in re.finditer(r"\$?\s?(\d{2,4})(?:\.(\d{2}))?\b", text):
        whole, cents = m.group(1), m.group(2)
        on_page.add(float("%s.%s" % (whole, cents or "0")))
    expected = {r["price_mxn"] for r in table}
    missing = sorted(expected - on_page)
    return {
        "checked": True,
        "prices_in_table": len(expected),
        "prices_still_on_the_page": len(expected) - len(missing),
        "missing_from_the_page": missing,
        "verdict": "unchanged" if not missing else "THE MENU CHANGED -- re-read it by hand",
    }


def build_food(blob, venue_ids):
    cn = cached("cineteca_index.json", fetch_cineteca)
    cinemas = cached("cinemas.json", lambda: cx("cinemas/", "cinemex_cinemas"))
    candy = cached("candybar.json", lambda: fetch_candybar(venue_ids))
    platino = cached("landing_platino.json",
                     lambda: cx("landings/cines-platino", "cinemex_landing_platino"))
    cached("landing_casa_de_arte.json",
           lambda: cx("landings/casa-de-arte", "cinemex_landing_casa_de_arte"))

    named_platino = set()
    for p in (platino if isinstance(platino, list) else [platino]):
        for pg in (p.get("pages") or []):
            for c in ((pg.get("content") or {}).get("cinemas") or []):
                named_platino.add(str(c["id"]))

    byid = {str(c["id"]): c for c in cinemas}
    out = {}

    for cid in venue_ids:
        c = byid.get(cid, {})
        is_platino = bool(c.get("platinum"))
        cb = candy.get(cid, {})
        rec = {
            "chain": "Cinemex",
            "name": c.get("name"),
            "snack_menu": {
                "available": False,
                "detail": ("Cinemex's snack API is switched off nationally. This venue "
                           "reports candybar false, and its catalogue endpoint answers 200 "
                           "with an empty list."),
                "catalog_items": cb.get("catalog_len"),
                "source": "cinemex_candybar_catalog",
                "confidence": "measured",
                "control": ("The endpoint can say no: omitting cinema_id returns HTTP 400, "
                            "so an empty catalogue is a real answer and not a request that "
                            "was silently ignored."),
            },
            "alcohol": {
                "available": True if is_platino else None,
                "detail": ("A drinks menu that includes Topo Chico Hard Seltzer, brought to "
                           "your seat.") if is_platino else None,
                "source": "cinemex_landing_platino" if is_platino else None,
                "confidence": ("operator_published" if cid in named_platino
                               else "format_level_inference" if is_platino else "unknown"),
                "named_on_platino_landing": cid in named_platino if is_platino else None,
                "note": (None if cid in named_platino else
                         ("This venue carries the `platinum` attribute but is NOT one of "
                          "the 25 complexes Cinemex's own Platino landing page lists, so "
                          "the drinks statement reaches it as a claim about the format "
                          "rather than about this address.") if is_platino else
                         ("No public Cinemex source says whether this venue sells alcohol. "
                          "The only alcohol statement they publish anywhere is the Platino "
                          "one, and searching their whole 8.4 MB CMS for 'cerveza' and "
                          "'alcoh' returns only sweepstakes small print and one NFL combo "
                          "page whose own record reads is_active false. Absence of a "
                          "statement is not a no.")),
            },
            "attributes": c.get("attributes") or [],
            "platinum": is_platino,
        }
        out[cid] = rec

    # ---- Cineteca, where the menus are real
    terraza_path = (cn.get("cineteca_menu_terraza") or {}).get("path")
    mirador_path = (cn.get("cineteca_menu_mirador") or {}).get("path")
    terraza_drift = menu_drift(terraza_path, 9, TERRAZA_DRINKS)
    mirador_drift = menu_drift(mirador_path, 4, MIRADOR_DRINKS)
    for name, drift in (("Terraza", terraza_drift), ("Mirador", mirador_drift)):
        if drift.get("checked") and drift.get("missing_from_the_page"):
            print("  !! %s menu drifted: %s no longer on the page"
                  % (name, drift["missing_from_the_page"]), flush=True)

    cafeteria_absent = {
        "available": False,
        "detail": None,
        "source": "cineteca_menu_cafeteria",
        "confidence": "measured",
        "note": ("ABSENT, not missing. The Menu button beside 'Cafeteria 8 1/2 y fuente de "
                 "sodas' on Cineteca's own espacios_8.php links "
                 "docs/espacios_812/CNMX/cafeteria812/menuDigital.pdf, which returns 404. "
                 "Eleven neighbouring filenames and both parent directories were probed and "
                 "there is no current file: the directory paths answer 200 with an 'Error "
                 "404' body, cinetecanacional.net serves no sitemap.xml and no robots.txt, "
                 "and a web search surfaces nothing. There is no cafeteria menu to have."),
    }

    out["cineteca-003"] = {
        "chain": "Cineteca Nacional",
        "name": "Cineteca Nacional Mexico (Xoco)",
        "snack_menu": {
            "available": True,
            "source": "cineteca_menu_dulceria",
            "confidence": "ocr_vision_verified_visually",
            "extraction": ("The dulceria PDF is 8 image-only pages with 8 bytes of "
                           "extractable text. Rendered at 300 dpi, read with macOS Vision "
                           "OCR, then every label-to-price pairing checked against the "
                           "rendered page by eye."),
            "menu": DULCERIA,
            "note": ("This PDF is not linked anywhere on Cineteca's live page -- the link "
                     "is commented out in their HTML -- but the file is still served, and "
                     "it is byte-for-byte identical to the 'fuente de sodas' menu "
                     "(md5 %s), so the two outlets share one menu."
                     % ((cn.get("cineteca_menu_dulceria") or {}).get("md5") or "?")[:12]),
        },
        "alcohol": {
            "available": True,
            "detail": "La Terraza has a full beer and wine list.",
            "outlet": "La Terraza",
            "items": TERRAZA_DRINKS,
            "items_excluded": TERRAZA_DRINKS_EXCLUDED,
            "drift_check": terraza_drift,
            "source": "cineteca_menu_terraza",
            "confidence": "pdf_text_layer_two_extractors_agree",
            "verification": ("Every price here was read twice: pdftotext -layout on the "
                             "PDF's own text layer, and macOS Vision OCR on the same page "
                             "rendered at 200 dpi. The two agree letter for letter. That "
                             "double read is the rule for any PDF price -- poppler is "
                             "unusually good at repairing a broken ToUnicode table, so a "
                             "single forgiving extractor hides exactly this defect."),
            "note": ("One row in the source is unusable and is left out rather than "
                     "guessed: a line reading only 'Botella $835.00' with no wine named. "
                     "Both extractors read it the same way, so the gap is in the menu."),
        },
        "outlets": [
            {"name": "Dulceria principal y plaza del cubo",
             "hours_es": "Lunes a viernes de 13:30 a 21h. Fines de semana de 11:30 a 21h.",
             "source": "cineteca_espacios", "confidence": "operator_published"},
            {"name": "Cafeteria 8 1/2 y fuente de sodas",
             "hours_es": "Lunes a jueves y domingo de 11 a 21h. Viernes y sabado de 11 a 22h.",
             "menu": cafeteria_absent,
             "source": "cineteca_espacios", "confidence": "operator_published"},
            {"name": "Patio Cineteca", "hours_es": "Martes a domingo de 14 a 21:30h.",
             "source": "cineteca_espacios", "confidence": "operator_published"},
            {"name": "La Terraza",
             "hours_es": "Jueves y domingo de 14 a 22h. Viernes y sabado de 14 a 23h.",
             "source": "cineteca_espacios", "confidence": "operator_published"},
        ],
        "food_rule_es": ("Recuerda que solo se te permitira el acceso de alimentos "
                         "adquiridos en la dulceria de la Cineteca Nacional."),
        "accessibility_es": ("Todas nuestras salas estan habilitadas para el acceso en "
                             "atencion de las personas con discapacidad."),
        "rules_source": "cineteca_faq",
        "rules_confidence": "operator_published",
    }

    out["cineteca-002"] = {
        "chain": "Cineteca Nacional",
        "name": "Cineteca Nacional de las Artes",
        "snack_menu": {
            "available": None, "detail": None, "source": "cineteca_espacios",
            "confidence": "unknown",
            "note": ("This sede has a 'Dulceria Principal' with published hours and NO menu "
                     "link of any kind on Cineteca's own page. The Xoco dulceria menu is "
                     "filed under /CNMX/ and must not be presented as this one's."),
        },
        "alcohol": {
            "available": True,
            "detail": "Fuente de sodas El Mirador has a beer and wine list.",
            "outlet": "Fuente de sodas El Mirador",
            "items": MIRADOR_DRINKS,
            "drift_check": mirador_drift,
            "source": "cineteca_menu_mirador",
            "confidence": "pdf_text_layer_two_extractors_agree",
            "verification": ("Read twice, pdftotext -layout and macOS Vision OCR on the "
                             "same rendered page; the two agree letter for letter."),
        },
        "outlets": [
            {"name": "Dulceria Principal",
             "hours_es": "Lunes a viernes de 13 a 21h. Fines de semana de 11 a 21h.",
             "source": "cineteca_espacios", "confidence": "operator_published"},
            {"name": "Cafeteria 8 1/2 y Restaurante Pergola",
             "hours_es": "Lunes a domingo de 10 a 21h.",
             "source": "cineteca_espacios", "confidence": "operator_published"},
            {"name": "Fuente de sodas El Mirador",
             "hours_es": "Domingo a jueves 14 a 21:30h. Viernes y sabado 14 a 22:30h.",
             "source": "cineteca_espacios", "confidence": "operator_published",
             "corroboration": ("The Mirador menu PDF prints the same hours on its own last "
                               "page, so two sources agree.")},
        ],
        "rules_source": "cineteca_faq",
        "rules_confidence": "operator_published",
    }

    out["cineteca-001"] = {
        "chain": "Cineteca Nacional",
        "name": "Cineteca Nacional Chapultepec",
        "snack_menu": {"available": None, "detail": None, "source": "cineteca_espacios",
                       "confidence": "unknown",
                       "note": ("Cineteca's espacios_8.php carries a heading for this sede "
                                "and lists NO outlets under it at all -- no dulceria, no "
                                "cafeteria, no hours. Its slot renders a "
                                "'proximamente' placeholder image and every Menu button "
                                "beside it is commented out. Nothing is published either "
                                "way.")},
        "alcohol": {"available": None, "detail": None, "source": "cineteca_espacios",
                    "confidence": "unknown",
                    "note": "No outlets are published for this sede at all."},
        "outlets": [],
        "rules_source": "cineteca_faq",
        "rules_confidence": "operator_published",
    }
    return out


def fetch_candybar(venue_ids):
    out = {}
    for cid in venue_ids:
        try:
            d = cx("candybar/catalog?cinema_id=%s" % cid)
            cat = d.get("catalog")
            out[cid] = {"status": 200,
                        "catalog_len": len(cat) if isinstance(cat, list) else None,
                        "blocks": [b.get("name") for b in (d.get("blocks") or [])]}
        except Exception as e:
            out[cid] = {"status": None, "error": str(e)[:120]}
        time.sleep(0.3)
    # The control that makes an empty catalogue mean something.
    try:
        cx("candybar/catalog")
        out["_control_missing_param"] = {"status": 200, "rejected": False}
    except urllib.error.HTTPError as e:
        out["_control_missing_param"] = {"status": e.code, "rejected": e.code == 400}
    note_source("cinemex_candybar_catalog", CX_BASE + "candybar/catalog?cinema_id=<id>",
                200, None,
                {"venues_fetched": sum(1 for k in out if not k.startswith("_")),
                 "venues_with_a_non_empty_catalog":
                     sum(1 for k, v in out.items()
                         if not k.startswith("_") and (v.get("catalog_len") or 0) > 0),
                 "control_missing_param": out["_control_missing_param"]})
    return out


# --------------------------------------------------------------- assemble

def main():
    blob = app_venues()
    venue_ids = [str(c["id"]) for c in blob["cin"]]
    cinemex_ids = [v for v in venue_ids if v.isdigit()]

    print("%d venues in the page, %d Cinemex" % (len(venue_ids), len(cinemex_ids)))

    loyalty = build_loyalty(cinemex_ids)
    formats = build_formats(blob)
    pricing = build_pricing(blob)
    food = build_food(blob, cinemex_ids)
    split = attribute_split()
    if "CHANGED" in split["verdict"]:
        print("  !! %s" % split["verdict"], flush=True)

    for sid in ("wikipedia_es_dolby_atmos", "wikipedia_es_imax", "wikipedia_es_4dx"):
        SOURCES.setdefault(sid, {"url": SOURCE_URLS[sid], "http_status": 200,
                                 "note": "read through the MediaWiki extracts API"})

    doc = OrderedDict()
    doc["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    doc["generated_by"] = "build-cinema-extras.py"
    doc["about"] = (
        "Loyalty, projection formats in plain words, ticket price bands, and food and "
        "alcohol, for the 35 venues docs/index.html actually carries. Every value names "
        "where it came from in `sources` and carries a `confidence`. A field that could "
        "not be sourced is null with a note saying why, never a plausible-looking number.")
    doc["app_venues"] = {
        "count": len(venue_ids),
        "cinemex_ids": cinemex_ids,
        "cineteca_ids": [v for v in venue_ids if not v.isdigit()],
        "note": ("read out of the SHOWS blob in docs/index.html at build time. The "
                 "validator refuses any venue id in this file that the page does not "
                 "carry."),
    }
    doc["sources"] = SOURCES
    doc["loyalty"] = loyalty
    doc["formats"] = formats
    doc["ticket_pricing"] = pricing
    doc["food_and_alcohol"] = food
    doc["measured_facts"] = [
        {"fact": "Assigned seating is universal at Cinemex, not a Platino feature.",
         "detail": "seatallocation read true on all 140 sessions swept, every format.",
         "source": "cinemex_sessions_sweep", "confidence": "measured"},
        {"fact": "Platino is NOT adults-only.",
         "detail": ("The brief said it was. adults_only read false on all 28 Platino "
                    "sessions swept. The 4 sessions that read true are Espanol Tradicional "
                    "and Subtitulada Tradicional -- so the flag tracks the FILM's rating, "
                    "not the format."),
         "source": "cinemex_sessions_sweep", "confidence": "measured"},
        {"fact": "The session-level `premium` and `extreme` booleans are useless.",
         "detail": ("Both read false on all 140 sessions, including every session whose own "
                    "label is 'Premium Espanol' or 'Premium Subtitulada'. Detect the format "
                    "from the version label or its type array, never from these."),
         "source": "cinemex_sessions_sweep", "confidence": "measured"},
        {"fact": "Dolby Atmos is only in attributes.secondary, never in primary.",
         "detail": ("Re-read rather than carried over. Across Antara Platino and Parque "
                    "Delta, both of which HAVE Atmos rooms, `dolby_atmos` appears 0 times "
                    "in attributes.primary, 11 times in attributes.secondary and 11 times "
                    "in the version's top-level `type` array. IMAX is the other way round: "
                    "14 in primary, 0 in secondary. So read `type`, which is the union. A "
                    "reader built on primary gets IMAX, Platino, Premium, 3D and the "
                    "dubbed/subtitled flag all correct and reports zero Atmos rooms while "
                    "looking perfectly healthy. Check this only against a venue that "
                    "actually has the format -- a zero at a venue with no Atmos room "
                    "cannot tell an empty field apart from an empty cinema. "
                    "See CINEMEX-API.md section 6."),
         "measurement": split,
         "source": "cinemex_cinema_movies", "confidence": "measured"},
        {"fact": "Booking fees are zero.",
         "detail": "fee and tax read 0 on all 257 ticket products swept.",
         "source": "cinemex_sessions_sweep", "confidence": "measured"},
    ]
    doc["not_obtainable"] = [
        {"thing": "A Cinemex snack menu",
         "why": ("Their end is empty, and it is a national switch-off rather than a wrong "
                 "request. All 32 app venues report candybar false and answer 200 with an "
                 "empty catalogue, and the endpoint returns 400 when the parameter is "
                 "missing, so the empty answer is real. cinemex.com/dulceria is a 404. Do "
                 "not spend another afternoon on this."),
         "source": "cinemex_candybar_catalog", "confidence": "measured"},
        {"thing": "The Cineteca cafeteria menu",
         "why": ("Their own live page links a PDF that 404s and no replacement exists. See "
                 "the note on the Xoco cafeteria outlet."),
         "source": "cineteca_menu_cafeteria", "confidence": "measured"},
        {"thing": "A peso value for a Cinemex point",
         "why": ("Cinemex says points are spendable as payment and never states a ratio, "
                 "anywhere in 8.4 MB of CMS or 112 KB of benefits."),
         "source": "cinemex_ie_benefits", "confidence": "measured"},
        {"thing": "What Confort, Infinity Vision, Market or CinemeXtremo actually are",
         "why": ("Cinemex names all four and describes none. 'confort' and 'Infinity "
                 "Vision' appear zero times in their entire CMS, and 150 showtimes in this "
                 "app are Infinity Vision screenings they sell without ever saying what "
                 "one is."),
         "source": "cinemex_app_settings", "confidence": "measured"},
        {"thing": "A dress code, at any cinema in this app",
         "why": ("No public source describes one. Carried from "
                 "docs/DATA-SOURCES-2026-09-09.md, which searched the CMS, the benefits "
                 "payload, the news feed, the Cineteca FAQ and Wikipedia for vestimenta, "
                 "codigo de vestir, dress code, playera, sandalia, short, bermuda, traje "
                 "and formal, and found zero hits describing an attire rule."),
         "source": None, "confidence": "third_party"},
    ]

    # Fill in any source id the data references but a cached pull never fetched, so no
    # `source` in this file dangles. A referenced id with no url at all is a bug, not a
    # cache artefact, so it stops the build.
    referenced = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("source", "rules_source") and isinstance(v, str):
                    referenced.add(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(doc)

    # Every confidence value the data uses has to be declared in formats.vocabulary, so
    # the file explains its own labels and a typo cannot ship as a new confidence level.
    used = set()

    def walk_conf(o):
        if isinstance(o, dict):
            if isinstance(o.get("confidence"), str):
                used.add(o["confidence"])
            for v in o.values():
                walk_conf(v)
        elif isinstance(o, list):
            for v in o:
                walk_conf(v)
    walk_conf(doc)
    undeclared = sorted(used - set(doc["formats"]["vocabulary"]))
    if undeclared:
        sys.exit("confidence values used but not declared in formats.vocabulary: %s"
                 % undeclared)

    for sid in sorted(referenced - set(SOURCES)):
        if sid not in SOURCE_URLS:
            sys.exit("source id %r is referenced by the data and has no url" % sid)
        SOURCES[sid] = {"url": SOURCE_URLS[sid], "http_status": 200,
                        "from_cached_pull": True,
                        "note": "served from .raw-extras/ on this run; url recorded for reference"}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s  %.0f KB  (%d sources, %d referenced)"
          % (OUT, os.path.getsize(OUT) / 1024.0, len(SOURCES), len(referenced)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true",
                    help="reuse the raw pull in .raw-extras/ instead of refetching")
    ARGS = ap.parse_args()
    main()
