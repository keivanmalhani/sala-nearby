#!/opt/homebrew/bin/python3
"""Turn scraped Google Maps reviews into a temperature verdict and recurring themes.

The whole job is one classification: does this reviewer mean the ROOM was cold, or
something else? Three things get in the way and each of them is handled explicitly:

  "palomitas frias"        -- cold popcorn. The most common frio in a cinema review and
                              nothing to do with the room. Ignored.
  "sin aire acondicionado" -- the words "aire acondicionado" appear, and it is a HEAT
                              complaint, not a cold one.
  "lleven chamarra"        -- never uses the word cold at all and is the strongest cold
                              signal there is, because the reviewer is giving advice.

test_classifier() below is a control: it requires the four cases to come out as four
different verdicts. A classifier that answers the same thing to everything looks exactly
like a working one when you only read the totals.
"""
import json, re, sys, unicodedata
from collections import Counter


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# Things that are cold in a cinema and are not the room. Food and drink are the obvious
# ones; "muros frios" is a complaint about the decor and was being read as temperature.
FOOD = (r"(palomita|comida|nacho|hot ?dog|hotdog|cafe|bebida|refresco|pizza|hamburguesa|"
        r"papas|crepa|baguette|alimento|boneless|hielo|\bice\b|nieve|cerveza|agua|"
        r"chocolate|postre|sushi|dulceria|dulce|combo|snack|malteada|slush|paleta|"
        r"salchicha|queso|aderezo|mostaza|catsup|cebolla|chapata|jicama|frappe|"
        r"pastelillo|botana|comiendo|comer\b|comi\b|mcdonal|macdonal|burger|starbucks|"
        r"pedi\b|pedimos|trajeron|sirvieron|sirvio|compre\b|compramos|cambian|"
        r"chorreaba|sabor|porcion|carton|"
        r"barra|botecito|cajita|vaso|jumbo|boing)")
DECOR = r"(muro|pared|color|tono|decorac|pintura|azulejo|iluminacion|luz|luces|estetica)"

COLD_ROOM = [
    r"\b(hace|hacia|estaba|esta|muy|demasiado|bastante|un poco de|el)\s+fri[oa]",
    r"\bfri[oa]s?\b",
    r"\bhelad[oa]s?\b", r"\bcongelad", r"\bcongeland", r"\bgelid", r"\bpolar\b",
    # NOT r"\bartic": that matches "articulos", and it read a sentence about merchandise
    # being in stock as a complaint about the cold.
    r"\bartic[oa]s?\b",
    r"\bsiberia",
    # NOT r"\bnevera" or r"\brefrigerador": both are appliances. The only hit in 3,267
    # reviews was a complaint about being told to leave a drink in the foyer fridge.
    # NOT r"\bpinguin": the only hit in 1,300 reviews was the film "Lecciones con un
    # pinguino". A cute synonym is not worth a false positive on a title.
    r"aire\s+(acondicionado\s+)?(muy\s+)?(fuerte|potente|helado|frio|al maximo|a tope)",
    r"(bajen|bajar|apaguen|apagar)\s+(el\s+)?aire",
]
# "bring a jacket" -- advice, and the clearest cold signal in the corpus.
JACKET = [r"\bchamarra", r"\bsueter", r"\bsuéter", r"\babrigo", r"\bcobija", r"\bmanta\b",
          r"\bbufanda", r"\bchaqueta", r"\bsudadera", r"\bcalcetin", r"\bllevar? ?ropa (abrigadora|calientita)"]

HEAT_ROOM = [
    r"\bcalor\b", r"\bcaluros", r"\bsofocan", r"\bbochorn", r"\bsauna\b",
    # "un horno" is the room. "a horno de lena" and "al horno" are the kitchen.
    r"(?<!al )\bhorno\b(?!\s+de\s+lena)",
    r"\basfixian", r"\bhervir", r"\bsudand[oa]\b", r"\bsudor\b",
    r"\bcalient(e|ito)\s+(la\s+)?sala",
    r"(sin|no hay|no había|no habia|no sirve|no servia|no servía|no funciona|no jala|apagaron|falta|faltaba|descompuesto)"
    r"[^.!?]{0,30}\baire\b",
    r"\baire\b[^.!?]{0,30}(no (sirve|servia|servía|funciona|funcionaba|jala)|descompuesto|apagado)",
]

THEMES = {
    "sound":      r"\b(sonido|audio|bocina|volumen|se escucha|dolby|atmos|se oye|distorsion)",
    "seats":      r"\b(asiento|butaca|reclinab|comod|incomod|hundid|resorte|respaldo|silla)",
    "clean":      r"\b(limpi|sucio|sucia|mugre|basura|pegajos|cochin|olor|bano|banos|higien)",
    "crowding":   r"\b(lleno|llena|fila|cola|saturad|aglomera|gente|abarrotad|espera)",
    "safety":     r"\b(insegur|segurid|asalt|rob(o|aron|an)|peligros|vigilanc|de noche)",
    "parking":    r"\b(estacionamiento|valet|pension|parquimetro|aparcar)",
    "price":      r"\b(caro|carisim|precio|barat|costos|economic|cuesta)",
    "staff":      r"\b(personal|atencion|servicio|amable|grosero|empleado|taquilla|cajero)",
    "picture":    r"\b(pantalla|imagen|proyecc|enfoque|nitidez|3d|imax|oscura la imagen|brillo)",
    "snacks":     r"\b(dulceria|palomita|combo|nacho|comida|refresco)",
    "programming": r"\b(cartelera|pelicula|funcion|estreno|subtitul|doblad|horario)",
    "accessibility": r"\b(elevador|escalera|silla de ruedas|discapacidad|rampa)",
}
# The unfiltered word counts the brief asked for, kept beside the classified ones so
# anyone can see how much work the food and broken-air rules are doing.
RAW = {
    "frio": r"\bfri[oa]s?\b", "helado": r"\bhelad[oa]s?\b", "congelando": r"\bcongel",
    "aire_acondicionado": r"aire acondicionado", "calor": r"\bcalor\b",
    "caluroso": r"\bcaluros", "chamarra_o_sueter": r"\b(chamarra|sueter|abrigo|cobija)",
}

THEME_LABEL = {
    "sound": "sound", "seats": "seat comfort", "clean": "cleanliness / bathrooms",
    "crowding": "crowding and queues", "safety": "safety of the area",
    "parking": "parking", "price": "price", "staff": "staff and service",
    "picture": "picture and screen", "snacks": "snack bar",
    "programming": "what is showing", "accessibility": "access and lifts",
}

SENT = re.compile(r"[^.!?\n;]+")

# A sentence-level food guard is useless here: "llegamos 11:30 y palomitas frias" also
# contains "funcion", and almost every cinema review contains a room word somewhere. So
# ask which noun the cold word is actually ATTACHED to -- the three tokens either side.
COLD_TOKEN = re.compile(r"\b(fri[oa]s?|helad[oa]s?|congelad[oa]s?|nieve)\b")
ROOM = re.compile(r"\b(sala|salas|cine|aire|adentro|butaca|asiento|sitio|lugar|ambiente|"
                  r"temperatura|clima|acondicionado|pies|manos|cuerpo)\b")

# For the whole-sentence fallback only. "cine", "lugar" and "sitio" appear in almost
# every review of a cinema, so treating them as evidence that a cold word means the room
# blocks the fallback everywhere and lets "los alimentos, todos frios" through.
ROOM_STRICT = re.compile(r"\b(sala|salas|aire|adentro|butaca|asiento|temperatura|clima|"
                         r"acondicionado)\b")


def cold_attachment(s):
    """What each cold word in the sentence is attached to.

    Returns "room" if any cold word is about the room (or cannot be explained away),
    "food" if they are all about food or drink, "decor" if they are all about the
    walls, and None if there is no cold word at all. "helado" is ice cream far more
    often than it is a freezing sala, and "congelado" is usually the drinks fridge.
    """
    found = list(COLD_TOKEN.finditer(s))
    if not found:
        return None
    hits = [h for h in found if not NEGATED.search(s[max(0, h.start() - 22):h.start()])]
    if not hits:
        # Every cold word in the sentence was negated -- "sin frio en exceso" is praise.
        # This has to be told apart from "no cold word at all", because the caller has a
        # fallback branch for the second and it would have swallowed the first.
        return "negated"
    w = s.split()
    kinds = set()
    for m in hits:
        idx = len(s[:m.start()].split())
        # +-4 tokens, not 3: "las papas estaban duras y frias" puts the food noun four
        # words before the cold one, and a 3-token window read it as the room.
        window = " ".join(w[max(0, idx - 4): idx + 5])
        # Both a food word and a room word can sit in the same window -- "las palomitas
        # todas frias y las salas medio sucias" has both. Whichever is CLOSER to the cold
        # word is the one it belongs to; taking room first made the popcorn a cold sala.
        mr, mf = ROOM.search(window), re.search(FOOD, window)
        if mr and mf:
            kinds.add("room" if abs(mr.start() - len(window) // 2)
                      < abs(mf.start() - len(window) // 2) else "food")
        elif mr:
            kinds.add("room")
        elif mf:
            kinds.add("food")
        elif re.search(DECOR, window):
            kinds.add("decor")
        elif re.search(FOOD, s) and not ROOM_STRICT.search(s):
            # The window was inconclusive, but the sentence is plainly about food:
            # "por fuera estan calientes y por dentro frios" is a hot dog.
            kinds.add("food")
        else:
            kinds.add("room")          # unexplained cold defaults to the room
    if "room" in kinds:
        return "room"
    return "food" if "food" in kinds else "decor"


# A jacket only means "it is cold in there" when the reviewer is giving advice. Without
# this, "se llevaron mi sueter" and "traian una cobija" both read as cold complaints --
# and the verb forms have to end at a word boundary, because \blleva also matches
# "llevaron", which is how a theft became a temperature reading.
# "las salas limpias, sin frio en exceso" is praise. Counting it as a cold complaint
# gets the sign backwards on exactly the cinema that is doing it right.
NEGATED = re.compile(r"\b(sin|nada de|no hay|no hacia|no hace|no habia|no tenia|poco|nunca)\s+"
                     r"(mucho |tanto |exceso de |nada de )?$")

# A jacket named in a bag-search or theft sentence is not a temperature reading.
JACKET_NOT_TEMP = re.compile(r"\b(mochila|bolsa|revision|revisar|vigilanc|segurid|rob[aoó]|"
                             r"guardarropa|extravi|perdi\b|olvid|se llevaron)")

ADVICE = re.compile(r"\b(llev[ae]\b|lleven\b|llevar\b|traer\b|traigan\b|trae\b|ponte\b|"
                    r"pongan\b|pon\b|usen\b|usa\b|usar\b|necesit|recomiend|indispensable|"
                    r"imprescindible|obligatorio|conviene|sugiero|hay que|abrigad|"
                    r"para sobrevivir|no olvide)")


def advice_near_jacket(s):
    """True when an advice verb actually governs the jacket word -- within three words.

    Eight was too loose: "recomiendo llegar temprano, habia una senora con su chamarra"
    puts the verb six words away and has nothing to do with temperature. "deben traer
    chamarra" puts it one word away, which is what a real instruction looks like.
    """
    w = s.split()
    for i, tok in enumerate(w):
        if any(re.search(p, tok) for p in JACKET):
            if ADVICE.search(" ".join(w[max(0, i - 3): i + 4])):
                return True
    return False


def classify_sentence(s):
    """COLD / HEAT / FOOD / None for one sentence of normalised text."""
    heat = any(re.search(p, s) for p in HEAT_ROOM)
    jacket = any(re.search(p, s) for p in JACKET)
    cold = any(re.search(p, s) for p in COLD_ROOM)
    # A jacket sentence is cold even when it never says the word cold -- but only when
    # it is advice or sits beside an actual cold word.
    att = cold_attachment(s)
    if jacket and JACKET_NOT_TEMP.search(s):
        jacket = False
    # The advice verb has to be NEAR the jacket, not merely somewhere in the same
    # sentence. Two of the three "cold" reviews at one cinema were 400-character rants
    # where "recomiendo" and "chamarra" were unrelated clauses 300 characters apart,
    # and they were enough to give that cinema the only COLD verdict in the report.
    if jacket and not advice_near_jacket(s):
        jacket = False
    if jacket and not heat and (ADVICE.search(s) or att == "room"):
        return "COLD"
    if heat:
        return "HEAT"          # "encendieron el aire ... era un horno" -- the horno wins
    if att == "negated":
        return None
    if att == "room" or (cold and att is None):
        return "COLD"
    if att == "food":
        return "FOOD"          # cold popcorn, not a cold room
    return None                # decor, or no cold word at all


def classify_review(text):
    verdicts = [classify_sentence(s) for s in SENT.findall(norm(text))]
    v = [x for x in verdicts if x]
    return ("COLD" in v, "HEAT" in v, "FOOD" in v)


# Patterns that can be the reason a sentence was called COLD or HEAT, so the quote can
# show the reader the actual trigger instead of whatever the sentence happened to open
# with. Reviews here run to 400-character single sentences, and quoting the first 190
# characters of one routinely showed a complaint about the queue.
TRIGGERS = {"COLD": COLD_ROOM + JACKET + [COLD_TOKEN.pattern], "HEAT": HEAT_ROOM}


def evidence(text, kind):
    for s in SENT.findall(text):
        if classify_sentence(norm(s)) != kind:
            continue
        flat = " ".join(s.split())
        n = norm(flat)
        best = None
        for pat in TRIGGERS[kind]:
            mm = re.search(pat, n)
            if mm and (best is None or mm.start() < best):
                best = mm.start()
        if best is None:
            return flat[:190]
        a = max(0, best - 90)
        return ("..." if a else "") + flat[a:best + 110] + ("..." if best + 110 < len(flat) else "")
    return None


def test_classifier():
    """A control. Six inputs, and the verdicts must not collapse to one label."""
    cases = [
        ("Hacia mucho frio en la sala, lleven sueter", "COLD"),
        ("las palomitas estaban frias y sin sal",      "FOOD"),
        # the real sentence that defeated the first, sentence-level food guard
        ("llegamos a las 11:30 am y palomitas frias, sin queso para nachos", "FOOD"),
        ("las palomitas frias y ademas la sala helada", "COLD"),
        ("no sirve el aire acondicionado, era un horno", "HEAT"),
        ("el personal fue muy amable y rapido",        None),
        # "articulos" is not "artico". This one shipped as a cold complaint about a
        # sentence saying the shop was well stocked.
        ("puedes encontrar vasos y articulos que en otros cines ya estan agotados", None),
        ("deben traer chamarra eskimal para sobrevivir", "COLD"),
        # every false positive found by reading the first 1,018 reviews classified
        ("no tenian ice, no esta bien congelado y parece agua",           "FOOD"),
        ("se llevaron mi sueter y la bolsa de mi hija",                   None),
        ("que tengan algo verde lleno de tantos muros frios",             None),
        ("estaba super deliciosa, tenia chocolate y helado",              "FOOD"),
        ("dese un helado, cerveza hasta sushi",                           "FOOD"),
        ("hizo llorar a mis ninos porque traian una cobija",              None),
        ("la sala estaba helada, un congelador",                          "COLD"),
        # a second reading of 1,271 classified reviews found these six
        ("otros chicos que iban comiendo helados del macdonals",           "FOOD"),
        ("por fuera estan calientes y por dentro frios, la comida mala",   "FOOD"),
        ("llegaron en cajita, frios, tristes con un botecito de cebolla",  "FOOD"),
        ("las salas limpias, sin frio en exceso",                          None),
        ("los nachos con queso casi frio y el refresco aguado",           "FOOD"),
        ("recomiendo revision a las mochilas o bolsas o chamarras",        None),
        ("siempre tienen el aire muy fuerte, asi que lleven algo de tapar", "COLD"),
        ("fui a ver lecciones con un pinguino, agradable experiencia",     None),
        # a third reading, of all 3,267 reviews, found these three
        ("una vez pedi un helado y me trajeron un carton que chorreaba",   "FOOD"),
        ("las papas estaban duras y frias, y la pizza llego tarde",        "FOOD"),
        # a fourth reading, with the trigger quoted rather than the sentence opening
        ("trata de evitar este cine, se tardan 45 minutos en traer los alimentos, "
         "todos frios",                                                    "FOOD"),
        ("banos sin papel, las palomitas todas frias y las salas medio sucias", "FOOD"),
        ("te comentan guardar tu bebida en un refrigerador de dudosa higiene", None),
        ("pedi una chapata y es una groseria que me la hayan dado fria",    "FOOD"),
        ("lleva alguna cobija si tu funcion es en la noche",                "COLD"),
        ("varios platillos son a horno de lena y pase una gran experiencia", None),
        ("el cine no usa el aire acondicionado y es un horno",              "HEAT"),
        ("me parece nefasta la actitud de la encargada, no dejan pasar comida, "
         "recomiendo llegar temprano, habia una senora con su chamarra en la fila", None),
    ]
    bad = []
    for text, want in cases:
        got = next((c for c in (classify_sentence(norm(text)),) if True), None)
        if got != want:
            bad.append("%r -> %s, wanted %s" % (text, got, want))
    if bad:
        sys.exit("classifier control FAILED:\n  " + "\n  ".join(bad))
    print("classifier control: %d cases, all as expected, %d distinct verdicts"
          % (len(cases), len({w for _, w in cases})))


def main():
    test_classifier()
    raw = json.load(open(sys.argv[1]))
    out = []
    for c in raw:
        s = c.get("sampled") or []
        cold = heat = food = 0
        ev_cold, ev_heat = [], []
        themes = Counter()
        rawc = Counter()
        stars = Counter()
        for r in s:
            iscold, isheat, isfood = classify_review(r["text"])
            cold += iscold; heat += isheat; food += isfood
            if iscold and len(ev_cold) < 4:
                e = evidence(r["text"], "COLD")
                if e: ev_cold.append({"stars": r["stars"], "when": r["when"], "quote": e})
            if isheat and len(ev_heat) < 4:
                e = evidence(r["text"], "HEAT")
                if e: ev_heat.append({"stars": r["stars"], "when": r["when"], "quote": e})
            n = norm(r["text"])
            for k, pat in RAW.items():
                if re.search(pat, n): rawc[k] += 1
            for k, pat in THEMES.items():
                if re.search(pat, n): themes[k] += 1
            if r["stars"]: stars[r["stars"]] += 1
        n = len(s)
        # One mention in a hundred reviews is not a verdict, it is one person. Anything
        # under three temperature mentions is reported as thin rather than dressed up as
        # an answer.
        tot = cold + heat
        if tot == 0:
            verdict = "no signal"
        elif tot < 3:
            verdict = "thin"
        elif cold >= 2 * heat:
            verdict = "cold"
        elif heat >= 2 * cold:
            verdict = "hot"
        else:
            verdict = "mixed"
        out.append({
            "id": c["id"], "name": c.get("name") or c["sala_name"], "sala_name": c["sala_name"],
            "place_id": c["place_id"], "maps_url": c["url"], "km": c.get("km"),
            "rating": c.get("rating"), "review_count": c.get("reviews"),
            "sampled": n, "ok": c.get("ok", False), "error": c.get("error"),
            "google_summary": c.get("google_summary"),
            "map_venue": c.get("map_venue"),
            "temperature": {
                "verdict": verdict, "cold_mentions": cold, "heat_mentions": heat,
                "food_cold_excluded": food,
                "pct_of_sample_cold": round(100.0 * cold / n, 1) if n else None,
                "pct_of_sample_hot": round(100.0 * heat / n, 1) if n else None,
                "raw_token_counts": dict(rawc),
                "evidence_cold": ev_cold, "evidence_hot": ev_heat,
            },
            "star_split": {str(k): v for k, v in sorted(stars.items())},
            "themes": [{"theme": THEME_LABEL[k], "reviews_mentioning": v,
                        "pct": round(100.0 * v / n, 1) if n else None}
                       for k, v in themes.most_common()],
        })
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print("\n%-38s %-5s %-7s %-7s %s" % ("cinema", "rate", "sample", "cold", "verdict"))
    for r in out:
        t = r["temperature"]
        print("%-38s %-5s %-7s %-7s %s (hot %d, food-cold ignored %d)" % (
            r["sala_name"][:38], r["rating"], r["sampled"], t["cold_mentions"],
            t["verdict"], t["heat_mentions"], t["food_cold_excluded"]))


if __name__ == "__main__":
    main()
