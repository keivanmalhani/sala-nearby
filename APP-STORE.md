# The twelve rejection reasons, against this app

Keivan sent a TikTok listing twelve reasons Apple rejects an app, with the note "fix all
this so that when we wanna publish we can". This is that list gone through one at a time,
with what was actually done rather than what could be claimed.

Nine of the twelve do not apply, and they do not apply for a real reason rather than a
convenient one: **this app takes no money, has no accounts and stores nothing about
anyone.** There is no sign-in to break, no purchase to restore, no account to delete.

Three were real. All three are fixed and each was checked in a way that could have failed.
The twelfth is structural, cannot be fixed by editing code, and is the one that decides
whether submitting is worth $99.

| # | Reason | Applies? | What was done |
|---|---|---|---|
| 1 | Stripe in-app | no | No payments. Every ticket is bought on Cinemex's own site in Safari. |
| 2 | Missing Apple sign in | no | No sign-in of any kind. Guideline 4.8 only bites if you offer a third-party login. |
| 3 | Account deletion | no | No accounts, so nothing to delete. 5.1.1(v) needs an account to exist. |
| 4 | **Website in a box** | **YES** | The real one. See below. |
| 5 | Broken demo login | no | Nothing to log into, so App Review needs no demo credentials. |
| 6 | **iPad UI broken** | **YES** | Fixed. |
| 7 | Outdated screenshots | not yet | A submission-time job: the store listing's screenshots must match the build. Nothing to do until there is a listing. |
| 8 | **"Coming soon" screens** | **YES** | Fixed — 63 dead-end states removed. |
| 9 | **Broken links** | **YES** | Checked properly, and clean. |
| 10 | "Report" feature | no | 1.2 applies to user-generated content. Nobody can post anything here. |
| 11 | Restore purchase broken | no | No purchases. |
| 12 | Paid feature screenshots | no | No paid features. |

## 6. iPad

Apple runs every submission on an iPad whether or not you built for one, and this is one of
the most common rejections for an app built phone-first.

At 1024 points wide it was a phone layout dragged wider. The venue name sat at the far left
of the screen with its walking distance pinned about nine hundred pixels away on the right,
and each row of sixty-pixel time chips floated in an ocean of empty ground. Nothing was
broken in the sense of erroring; it just read as a screen nobody had looked at.

It is a 720-point reading column now. The top bar and the tab bar keep their full-bleed
backgrounds and centre their contents with padding, so they still read as bars rather than
as cards hovering in the middle of the screen. The map is deliberately exempt — it is a
map, it should have the whole screen.

Checked at 1024x1366 portrait and 1366x1024 landscape: no horizontal overflow on any of
the four tabs, and the venue sheet still becomes a proper right-hand panel in landscape.

## 8. Dead-end screens

Sweeping all 31 days against all 6 filters, **63 of the 186 combinations rendered "Nothing
matches"** — a screen with nothing on it and no way forward.

Thirty of those were a single chip. "Starting soon" means the next four hours, so it can
never match a day that is not today, and it was offered on all thirty future days anyway.
The rest are genuine absences: no IMAX showing on a given Tuesday, no Platino on a sparse
advance-sale date in October.

A filter that cannot match the selected day is now **disabled rather than offered**, drawn
dimmed with a dashed border, and a filter that becomes impossible as the day changes falls
back to Everything rather than leaving an empty list under a chip that is still lit up. The
chips stay in place rather than disappearing so the row does not reflow under a thumb.

That is 123 reachable combinations, **zero dead ends**, and 63 chips greyed, which
reconciles to the 186.

It also turns out to be better design than the empty screen was: a greyed chip says at a
glance what is actually on that day, which is what the empty screen was making him hunt
for.

**The first sweep of this reported zero dead ends and was wrong.** It held one NodeList
across the entire loop on the assumption the rail re-rendered underneath it. It does not —
but a check whose passing depends on an assumption like that is not a check, and the
corrected version re-queries every iteration and found the 63.

## 9. Broken links

The app builds three kinds of link: a Cinemex checkout URL per showtime (7,853 of them), a
Cinemex page per cinema (32), and a Google Maps walking-directions URL per venue (built
from coordinates, so it cannot be malformed).

**The obvious check was worthless and it is worth knowing why.** Every URL — cinema pages,
checkout pages, all of them — answered HTTP 200 with byte-identical content. The control
settles it:

```
https://cinemex.com/checkout/65613956          200, 7080 words   a real booking link
https://cinemex.com/checkout/00000000          200, 7080 words   cannot exist
https://cinemex.com/thispathdoesnotexistatall  200, 7080 words   nonsense
```

cinemex.com is a single-page app. It serves one shell for every path and decides in the
browser whether that path means anything. **No status check can tell a working ticket link
from a dead one**, which is the same trap this project already hit with map tiles that
answer 200 with "API KEY REQUIRED" painted into the picture.

So they were rendered in a browser instead, one showtime sampled from each of the 31 days
so the October advance sales are covered rather than just this week:

- **31 of 31 land on a real ticket page**, each showing the film, the cinema, the date and
  the actual prices — $39 on a Cinemex Mania day, $78 adulto, $116 premium, $172 IMAX,
  $240 platino.
- **Both fabricated controls correctly land on "Ups! ... no está por aquí"**, so the check
  could have failed and did not.
- 32 of 32 cinema pages, the same.

Re-run this after any refresh. A checkout id is only as durable as the showing it belongs
to.

## 4. Website in a box, which is the one that matters

Guideline **4.2 Minimum Functionality**. Apple's wording: an app should offer "a lasting
value" and something "more than a repackaged website". This app is, honestly, a website,
and a very good one — that is what a PWA is.

**What would carry a submission**, in the order that actually persuades a reviewer:

1. **Genuine offline use.** Already true and already proved: the whole thing works with the
   network switched off, all 7,853 showings, every tab, after one visit. That is the single
   strongest argument against 4.2 and it is not a claim, it was measured.
2. **Something the browser cannot do.** A local notification twenty minutes before a
   showing you saved. A home-screen widget with tonight's nearest screening. Both are
   genuinely native, both are small, and either one converts "a website in a wrapper" into
   "an app that happens to have a web view". This is the work that would need doing, and it
   is real work rather than a checkbox.
3. **Native shell rather than a WebView.** A `WKWebView` pointing at the live site is the
   thing 4.2 is written to catch. Bundling the HTML locally and adding the two native
   features above is a different submission.

**What it costs.** $99 a year for the Apple Developer Program, which is the whole reason
this has not been started — see the standing rule about not spending his money. Nothing
here has been submitted anywhere and nothing will be without him saying so.

**The free alternative, and why it is not really an alternative.** Xcode free provisioning
installs a real native build over a cable, and **Apple deletes it after seven days**. It
also needs Xcode itself, which is not on this laptop — only the Command Line Tools — and is
about a 10 GB download against limited free space.

**The honest comparison.** The installed PWA beats free provisioning on every axis except
the words "App Store": it does not expire, it needs no cable, it updates when the page
does, and it already works offline. Against a paid App Store build it loses exactly two
things, notifications and widgets, and both are on the list above.

So the position is: **the three fixable rejection reasons are fixed and the app is in a
state where submitting is a decision about $99 and two native features, not about the code
being ready.** That was the ask.
