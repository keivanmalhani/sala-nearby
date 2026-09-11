#!/usr/bin/env python3
"""Which of the 42 venues actually serves a drink, read out of the audit by a local model.

    /opt/homebrew/bin/python3 bar.py --dry-run     # controls and classification, no write
    /opt/homebrew/bin/python3 bar.py               # and patch the page

Idea 18 in docs/IDEAS-2026-09-09.md, and the salvageable grain of his snacks-and-drinks
item. There is no machine-readable menu anywhere -- `candybar` is false on all 70 Cinemex
sites and cinemex.com/dulceria is a 404 -- but whether a building has a bar is a stable
fact about the building, and it is already written down in his own venue audit as prose.
Four venues say so in the write-ups; nobody has ever counted the rest.

WHY A LOCAL MODEL DOES THIS AND WHAT IT IS ALLOWED TO DECIDE.

The job is extraction, not judgement: the answer is IN the text, and the local models are
good at that and bad at anything where two labels sound equally plausible for the same
passage. So the model gets one narrow question and has to hand back a VERBATIM QUOTE with
its answer, and the quote is then checked against the source here. A model that invents
its evidence is caught mechanically rather than believed, and no row reaches the page
without a quote that survives that check.

THE CONTROLS RUN BEFORE THE BATCH, NOT AFTER. On 2026-09-04 a local model labelled 27
exception handlers and returned the same label for all 27; the control that disproved the
whole batch cost thirty seconds and was run last. Three run here first:

  1. Cine Tonala -- "a bar, a pizza kitchen and a bookstore" -- must come back yes.
  2. Cinemex Centro Telmex -- "ten plain rooms ... nothing premium" -- must come back no.
  3. The Tonala text with the bar negated in it must FLIP to no.

MEASURED, AND IT DECIDED THE MODEL. qwen3:4b fails control 1 outright. Given the Cine
Tonala write-up -- which contains "plus a bar, a pizza kitchen and a bookstore" and again
"pizza restaurant and cocktail bar" -- it answers no with an empty quote. Cut down to the
single sentence "Cine Tonala has one screen, a bookstore, a pizza restaurant and a
cocktail bar" it still answers no, so this is not a context-length problem. qwen3:8b
answers yes on the same text and quotes it back character for character. 8b costs 5.2 GB
resident against 4b's 2.5 and is loaded on demand and unloaded, per the standing rule
about this laptop's memory.

The first two prove the classifier can produce more than one label. The third is the one
that matters: it proves the answer is being read off the text in front of it rather than
off the venue's name, which the model may well recognise. If any of the three fails the
batch is thrown away and nothing is written.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
LOCALASK = os.path.expanduser("~/.local/bin/localask")
MODEL = "qwen3:8b"

QUESTION = (
    "Below is a description of a cinema. Does this cinema sell alcoholic drinks -- a bar, "
    "a cantina, beer, wine, cocktails, mezcal, or drinks brought to your seat?\n"
    'Answer "yes" only if the text says so. Answer "no" if the text does not mention '
    "alcohol at all.\n"
    "quote: copy the exact words from the text that made you answer, character for "
    'character. If you answered no, put "".'
)
SCHEMA = {
    "type": "object",
    "properties": {
        "alcohol": {"type": "string", "enum": ["yes", "no"]},
        "quote": {"type": "string"},
    },
    "required": ["alcohol", "quote"],
}


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", t.lower())


def squash(t: str) -> str:
    return re.sub(r"\s+", " ", norm(t)).strip()


def venue_texts() -> dict[str, str]:
    """Every word his audit holds about each venue: the plain-language blurb and every
    line of the spec table, joined. Read by evaluating the page's own arrays rather than
    by parsing them, because `spec` is nested arrays of prose with quotes inside it."""
    src = open(PAGE, encoding="utf-8").read()
    a = src.index("const V=[")
    b = src.index("const PLAIN={")
    c = src.index("const SHOWS=")
    js = src[a:b] + src[b:c] + "\nconsole.log(JSON.stringify(Object.fromEntries(V.map(v=>[v.name,[(PLAIN[v.name]||['',''])[1]].concat((v.spec||[]).map(r=>r[0]+': '+r[1])).concat(v.f||[]).join(' ')]))))"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def ask(text: str) -> dict:
    p = subprocess.run(
        [LOCALASK, "--model", MODEL, "--schema", json.dumps(SCHEMA),
         "--task", "sala-bar", QUESTION],
        input=text, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("localask failed: %s" % (p.stderr.strip() or p.stdout.strip()))
    try:
        return json.loads(p.stdout.strip())
    except json.JSONDecodeError:
        sys.exit("localask did not return JSON: %r" % p.stdout[:200])


def verified(ans: dict, text: str) -> bool:
    """A yes only counts when the words it quoted are genuinely in the text.

    Word boundaries rather than a raw substring, and a floor of three characters rather
    than eight. The first version of this asked for eight and threw away Cinemex Felix
    Cuevas, whose write-up ends "recliners, waiters, bar." -- the model quoted the one
    word that answers the question and the guard called it invention. A length floor is
    a proxy for "did it really read this"; the word-boundary match is the direct form of
    the same question and does not punish a text that says it in one word."""
    if ans.get("alcohol") != "yes":
        return False
    q = squash(ans.get("quote", ""))
    if len(q) < 3:
        return False
    return re.search(r"\b%s\b" % re.escape(q), squash(text)) is not None


def main() -> None:
    dry = "--dry-run" in sys.argv
    texts = venue_texts()
    print("%d venues read out of the page" % len(texts))

    # ------------------------------------------------------------------ controls, first
    tonala = texts["Cine Tonala"]
    telmex = texts["Cinemex Centro Telmex"]
    negated = re.sub(r"(?i)\bplus a bar\b", "with no bar and no alcohol of any kind",
                     tonala)
    if negated == tonala:
        sys.exit("CONTROL BROKEN: the phrase the negation control edits is not in the "
                 "Cine Tonala text any more, so control 3 would test nothing.")

    print("\ncontrols (run before the batch, not after)")
    c1, c2, c3 = ask(tonala), ask(telmex), ask(negated)
    print("  Cine Tonala          -> %s  %r" % (c1["alcohol"], c1["quote"][:60]))
    print("  Cinemex Centro Telmex-> %s  %r" % (c2["alcohol"], c2["quote"][:60]))
    print("  Cine Tonala, negated -> %s  %r" % (c3["alcohol"], c3["quote"][:60]))
    ok = []
    ok.append(("a venue with a bar reads yes", c1["alcohol"] == "yes"))
    ok.append(("its quote is really in the text", verified(c1, tonala)))
    ok.append(("a venue without one reads no", c2["alcohol"] == "no"))
    ok.append(("negating the bar flips the answer, so it is reading the text",
               c3["alcohol"] == "no"))
    for name, good in ok:
        print("  %s %s" % ("ok  " if good else "FAIL", name))
    if not all(g for _, g in ok):
        sys.exit("\nCONTROLS FAILED. The classifier cannot tell these two apart, so every "
                 "answer it gives about the other 40 venues is worthless. Nothing written.")

    # ------------------------------------------------------------------------- the batch
    print("\nclassifying %d venues" % len(texts))
    bar, rejected = {}, []
    for name, text in texts.items():
        ans = ask(text)
        if ans["alcohol"] != "yes":
            continue
        if not verified(ans, text):
            rejected.append((name, ans.get("quote", "")))
            continue
        bar[name] = re.sub(r"\s+", " ", ans["quote"]).strip(" .,;")
    print("  %d venues serve a drink" % len(bar))
    for n, q in sorted(bar.items()):
        print("    %-46s %s" % (n[:46], q[:70]))
    if rejected:
        print("  %d rejected: the model said yes and could not quote the text" % len(rejected))
        for n, q in rejected:
            print("    %-46s %r" % (n[:46], q[:60]))

    # A SECOND OPINION THAT COMPUTES IT DIFFERENTLY. The model is the only thing deciding
    # these rows, so a plain word search runs beside it and any disagreement is printed
    # rather than resolved. A word list cannot replace the model -- "waiters bringing food
    # and cocktails to your seat" is a bar and "the Bar Association" would not be -- but a
    # venue whose text says mezcal and which the model called no is exactly the miss that
    # would otherwise be invisible.
    WORDS = ("bar", "bares", "cantina", "beer", "cerveza", "wine", "vino", "cocktail",
             "cocktails", "coctel", "mezcal", "tequila", "alcohol", "alcoholic", "pulque")
    missed = []
    for name, text in texts.items():
        if name in bar:
            continue
        hit = [w for w in WORDS if re.search(r"\b%s\b" % w, squash(text))]
        if hit:
            missed.append((name, hit))
    print("  second opinion: a plain word search over the same text")
    if missed:
        print("    %d venues name a drink and the model said no -- read these by hand:" % len(missed))
        for n, h in missed:
            print("      %-46s %s" % (n[:46], ", ".join(h)))
    else:
        print("    no venue names a drink that the model missed")

    out = os.path.join(ROOT, "docs", "bar.json")
    if dry:
        print("\n--dry-run: nothing written")
        return
    json.dump(bar, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              sort_keys=True)
    print("\nwrote docs/bar.json -- run bar-page.py to put it on the page")


if __name__ == "__main__":
    main()
