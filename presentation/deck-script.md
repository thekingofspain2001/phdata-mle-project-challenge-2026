# Deck script — mirror of `presentation/deck.html`

Single-file reveal.js deck. This script is a build spec: an agent given
only this file should rebuild a deck visually and structurally similar to
`deck.html`. Keep the two in sync — every deck edit updates this script,
every script change lands in the deck.

Audience: 10-minute Part 1, non-technical (`CANDIDATE_PROJECT.md:11`).
Part 2 is live demo, no slides — runbook in Appendix D.

## Build

- One file, no build step. CDN: `reveal.js@4/dist/reveal.css` +
  `reveal.js@4/dist/reveal.js`. Font: Inter 400/500/600 via Google Fonts
  (+ preconnect). Favicon: `<link rel="icon" href="data:,">`.
- `<style>` in `<head>`, single `<script>` at body end. No `style=""`
  attributes anywhere; layout only via classes + `:root` tokens below.
- Slide count: 9 visible sections + 1 hidden appendix (`S10`).
  No vertical (nested) slides.

## Global chrome

Three items, selectors + values verbatim from `deck.html`:

(a) Background — `.reveal` (`deck.html:72-80`): navy
`background-color:#111F3A` + inline-SVG motif tile
(`--ph-pattern`, 783×642 tile, mint/mist strokes at ~0.22 opacity).
`background-size:var(--ph-motif-size)` (`50% auto`),
`background-repeat:no-repeat`, `background-position:100% 100%` (pinned
bottom-right), fixed on `.reveal` so it never moves on transition.
All `section`s transparent (`deck.html:83-90`: `display:flex`,
`flex-direction:column`, `height:100%`, `background:transparent`,
`text-align:left`); only content transitions.

(b) Slide chrome — persistent `header.ph-global-top`: absolute, static
`height:var(--ph-header-h)` (10vh), `padding:0 var(--gap-md)`,
`box-sizing:border-box`; brand left, title right.
`.ph-brandline` lockup: row, `align-items:center`,
`gap:calc(var(--gap-sm)*1.51)` (logo ink to separator balanced 19.2/19.3px),
`font-size:var(--fs-brand)`; logo `img.ph-logo` `height:var(--logo-size)` =
6vh, `width:auto`, `margin-right:calc(var(--gap-sm)*-0.51)` (absorbs PNG side
padding). Client `.ph-client`: Georgia serif (distinct from phData
Aspekta/Inter), `align-items:center` with the house glyph box
  (`1.58cap`, amber `#e8b04b`, no nudges) — icon vertically centered on the
  name cap. Title `#ph-global-title`: right-aligned, `font-weight:400`,
  `font-size:var(--fs-h2)`, `line-height:1.25` (descenders clear),
  `setGlobalTitle(slide)` (cover `ph-cover` → empty; direct text set +
  `is-empty` class hiding it when the title is empty — no fade, no `.style`
  writes).

(c) Footer chrome — static `height:var(--ph-footer-h)` (8vh). Arrows
pinned `bottom:calc((var(--ph-footer-h) - 36px)/2)` (36px button centered
in-band); rest `#6f8590`, all four directions `color:inherit`,
`:hover/:focus-visible/:active` → `var(--ph-mint)`. Slide number 26px
`var(--ph-mist)` on transparent, `text-decoration:none` on both
`.slide-number` and inner `a`, `padding:4px 10px`, docked `right:150px`
with `bottom:calc((var(--ph-footer-h) - 34px)/2)` left of the arrows, zero
overlap; current slide only.

  - Layout rule: reveal.js owns `.slides` geometry (`width:1270`,
    `height:961`, `margin:0.04`, `center:true` — uniform scale, no CSS
    overrides). Each `section` flex-fills its slide box (`display:flex`,
    `flex-direction:column`, `height:100%`). `.ph-body` flex-fills that
    (`flex:1 1 auto`, `min-height:0`) with overlay-band padding
    (`padding:var(--ph-header-h) var(--gap-md) var(--ph-footer-h)`), so the
    header title aligns with content at any viewport. Card rows fill the
    same area (`flex:1 1 auto`). Cover (`T-cover`) is the exception: centered.
  - Header title source: `aria-label` per slide — `Cover` (S1, hidden) ·
    `Executive summary` · `Listings with blanks get turned away` ·
    `Missing value approaches` · `Why similar homes won` · `Faster answers` ·
    `Errors you can act on` · `Modernised base` · `What you get` ·
    `Appendix demo runbook` (hidden). No `data-title` attributes.

## Tokens (`:root`)

```css
--ph-navy:#111f3a; --ph-mint:#a5feca; --ph-mist:#bcccd4;
--ph-card-border:rgba(165,254,202,.5); --ph-card-bg:#0c142e;
--ph-why-h:#fff; --ph-why-body:rgba(255,255,255,.75);
--ph-cap-bg:#f0f1f5; --ph-cap-h:#232a43;
--ph-client-font:"Inter",system-ui,sans-serif;
--ph-font:"Aspekta","Inter",system-ui,sans-serif;
--av:#e8b04b; --md:#7fb6d9; --knn:#c792ea;
--fs-brand:1.7vh; --fs-h1:5.4vh; --fs-h2:3vh; --fs-h3:2.2vh;
--fs-lead:2.3vh; --fs-body:1.9vh; --fs-caption:1.5vh;
--sp-xs:.8vh; --sp-sm:1.6vh; --sp-md:2.4vh; --gap-sm:1vw; --gap-md:2vw;
--ph-header-h:10vh; --ph-footer-h:8vh; --rad-card:1.2vh; --rad-cell:1vh;
--line-sm:.15vw; --line-md:.2vw; --logo-size:6vh;
--ph-motif-size:50% auto;
```

No wordmark tokens. `--logo-size:6vh` is the single logo size token.

  Equation accents (each used ONLY for its equation deck-wide): `--av:#e8b04b`
  amber = Average Value; `--md:#7fb6d9` blue = Mean value;
  `--knn:#c792ea` purple = Nearest Neighbor. Complement, never clash with,
phData mint/navy; distinct from Sound Realty house amber (header only).
## Metrics (single source)

Inline `DECK_METRICS` (`deck.html:830-841`); spans with `data-metric`
hydrate on load. Never hardcode numbers in body copy — always a keyed span:

```js
perf: { v1p50:"56 ms", v1p95:"79 ms", v2p50:"9 ms", v2p95:"13 ms" }
nnr:  { recovered:"10–20%" }
knn:  { k:"5", range:"14–17% closer", sqftAbove:"17% closer",
        bathrooms:"16% closer", floors:"15% closer", grade:"14% closer" }
```

Rounded display values. Underlying harness 2026-09-29 (TestClient, n=30,
payload 98042): v1 p50 55.8 ms / p95 78.9 ms; v2 p50 9.4 ms / p95 13.4 ms.
10–20% band from notebook MCAR `missing_rate=0.15`. KNN rows from
`notebooks/imputation_experiment.ipynb` §7 (price-predictive features;
headline average excluded — two lot-size outlier fields swamp it).

## Templates

Each reused layout defined once. Class names + flex rules + fragment order
verbatim from `deck.html` CSS.

  - T-cover — used by S1. `section.ph-cover > div.ph-body` (`align-items:center`,
    `justify-content:center`, `text-align:center`): the centered exception.
    Single `h1` (margin 0, `max-width:20ch`), no sub, no fragments, no metrics.
    Cover `aria-label="Cover"` hides the header title via `is-empty`.
  - T-scr — used by S2. Lead `p.ph-action` (always visible;
    `var(--ph-why-h)`, `var(--fs-lead)`, margin 0) + `ul.ph-scr`
    (wrapping, `flex:1 1 auto`, `align-content:stretch`,
    `gap:var(--sp-sm) var(--gap-md)`); cards `li` `flex:1 1 28vw`, dark fill
    `var(--ph-card-bg)`, mint left border (`border-left:var(--line-md) solid
    var(--ph-card-border)`), `padding-left:var(--gap-sm)`, no radius;
    `h3` default white, body `p` dim `var(--ph-why-body)`. Fragments: 6
    cards in DOM order (pains 1–3, fixes 4–6).
  - T-cols-3 — used by S3, S5, S6. `div.ph-cols` (`flex:1 1 auto`,
    `gap:var(--gap-md)`); each `article` `flex:1 1 0`, dark fill
    `var(--ph-card-bg)`, full border
    (`var(--line-sm) solid var(--ph-card-border)`),
    `border-radius:var(--rad-card)`, `padding:var(--sp-sm) var(--gap-sm)`;
    `h3` mint, `p` dim. Fragments: 3 articles left-to-right, then foot
    (S5/S6 only).
- T-cols-2 — used by S7. Same `.ph-cols` rules as T-cols-3 with 2
  articles (`Before` / `After`), no foot. Fragments: 2, left-to-right.
  - T-houses-staged — used by S4 only (`section#s4.is-stage-0..4`, no
    `data-*` attrs). `div.ph-body.ph-houses`: corner subtitles
    `div.ph-s4-subs` (`justify-content:flex-end`,
    `min-height:calc(var(--fs-h3)*1.3)` so layout holds): three `p.ph-s4-sub`
    (`display:none`; stage N shows only its accent class) — stage 1
    `.ph-is-av` Average Value amber, stage 2 `.ph-is-md` Mean value blue,
    stage 3 `.ph-is-knn` Nearest Neighbor purple; stages 0/4 show none.
    Top `.ph-houses-top` with `svg#houses-svg` (12 houses STATIC: mist stroke,
    fixed transforms, never recolored/dimmed across stages) + price labels
    ($105k–$859k, 98042 quantiles, y=232) + `p.ph-stage-hint` (hidden 1–4).
    Equation markers (`.mk`, staged): floating house + stem + equation text
    below the house + equation on the pick (`AVG $334k = Σ$4,003k/12`,
    `MED $294k = mid($284k,$303k)`, `5-NN → $293k = w-avg(5)`).
    Bottom `.ph-stage-bottom` (stage 0: panels hidden; stages 1–4: 50%) with
    one visible `.ph-panel` per stage in DOM order (border + `h3` in the
    panel's `.ph-is-*` accent; panel 4 summary neutral, `p.ph-panel-nums`
    value list). Hidden drivers: 4 `.fragment.ph-s4-go` spans in stage
    order. Houses x
    60/158/256/354/452/550/648/746/844/942/1040/1138, y=210.
- T-bars — used inside S5's third T-cols-3 card. `ul.ph-bars`
  (`deck.html:415-444`): column, `gap:var(--sp-xs)`; each `li` row-wrap
  (`flex-wrap:wrap`, `align-items:center`), dim body text; label `span`
  tinted by approach color (1st `--av`, 2nd `--md`, 3rd+ `--knn`);
  `meter` `flex:1 1 100%`, `width:100%`, `accent-color:var(--ph-mint)`,
  values 17/16/15/14 (`min="0" max="20"`). Plus `p.ph-foot`
  (`deck.html:447-452`): dim, `var(--fs-caption)`, `opacity:80%`,
  margin 0.
  - T-caps-6 — used by S8. `section.ph-caps > div.ph-body >
    ul.ph-caps-grid` (wrapping, `flex:1 1 auto`, `align-content:stretch`,
    `gap:var(--gap-md)`); cells `li` `flex:1 1 26vw`, light fill
    `var(--ph-cap-bg)` (`#F0F1F5`), `border-radius:var(--rad-cell)`, dark text
    `var(--ph-cap-h)` (`h3` full, `p` at `opacity:80%`). Fragments: 6
    cells in DOM order.
  - T-why-3 + handoff — used by S9. `section.ph-why > div.ph-body >
    ol.ph-why-grid` (`flex:1 1 auto`, `gap:var(--gap-md)`); each `li`
    `flex:1 1 0`, dark fill, full mint-tinted border,
    `border-radius:var(--rad-card)`; `p.ph-num` mint, `var(--fs-h3)`;
    `h3` white (`--ph-why-h`); body `p` dim. Then `p.ph-handoff.fragment`
    (white, `var(--fs-lead)`). Fragments: 3 cards + handoff = 4.
- T-why-3 + handoff — used by S9. `section.ph-why > div.ph-body >
  ol.ph-why-grid` (`deck.html:455-489`): row, `flex:1 1 auto`,
  `align-items:stretch`, `gap:var(--gap-md)`; each `li` `flex:1 1 0`,
  dark fill, full mint-tinted border, `border-radius:var(--rad-card)`;
  `p.ph-num` mint, `var(--fs-h3)`; `h3` white (`--ph-why-h`); body `p`
  dim. Then `p.ph-handoff.fragment` (white, `var(--fs-lead)`).
  Fragments: 3 cards + handoff = 4.
- T-appendix-hidden — used by S10. `section[data-visibility="hidden"]`:
  never presented; plain `ol` (no `.ph-*` grid classes), 5 items.

## Reveal config + JS

```js
Reveal.initialize({ width:1270, height:961, margin:0.04,
  minScale:0.2, maxScale:2.0, center:true, hash:true, slideNumber:true,
  transition:"slide", backgroundTransition:"none" });
```

  - `ready` → `setGlobalTitle(currentSlide)`.
  - `fragmentshown/hidden` → `s4Index(fragment)` over `.ph-s4-go` order →
    `setS4Stage(i+1)` / `setS4Stage(i)`; `setS4Stage` swaps `is-stage-N`
    + shows the Nth `.ph-panel` in DOM order (S4 staging; §S4).
  - `slidechanged` → sync title; entering `#s4` resets fragments to stage 0
    (`Reveal.slide(h,0,-1)` + `setS4Stage("0")` after 60 ms); leaving a
    non-zero S4 resets it to `"0"`.
- Chrome styling (appended after caps grid, verified headless 1280×800):
  arrows rest `#6f8590`, `:hover/:focus-visible/:active` → `var(--ph-mint)`.
  Slide number 26px `var(--ph-mist)` on transparent, `text-decoration:none`
  on both `.slide-number` and inner `a`, `padding:4px 10px`, docked
  `right:150px` with footer-centered `bottom` left of the arrows, zero
  overlap; current slide only. Title sync: direct text set + `is-empty`
  hide (no fade, no `.style` writes); zero `style=` attrs in markup.

## S1 — Cover (header title hidden)

  Layout: T-cover. No fragments, no metrics. Cover `aria-label` hides the
  header title via `is-empty`.

| Item | Content |
|------|---------|
| H1 | Housing Price Prediction Service Analysis |

- Say: "Every listing gets a price — even when the paperwork is
  incomplete."

## S2 — Executive summary (title `Executive summary`)

Layout: T-scr. Fragments: 6 (cards in DOM order).

| Item | Content |
|------|---------|
| Lead (`p.ph-action`, always visible) | The valuation API now prices incomplete listings, answers faster, and fails clearly. |
| Card 1 h3 | Listings arrive with blanks. |
| Card 1 body | Up to [nnr.recovered] of requests arrive with missing fields and used to be rejected. |
| Card 2 h3 | Every request reloads the model. |
| Card 2 body | Typical wait [perf.v1p50], slow tail [perf.v1p95]. |
| Card 3 h3 | Bad postcodes crash; the base is ageing. |
| Card 3 body | Confusing failures on unknown areas; runtime and docs behind. |
| Card 4 h3 | Blanks filled from [knn.k] similar homes. |
| Card 4 body | Price-moving fields [knn.range] than averages. |
| Card 5 h3 | Model loaded once, reused. |
| Card 5 body | Typical wait [perf.v2p50], slow tail [perf.v2p95]. |
| Card 6 h3 | Unknown areas named in plain words; base modernised. |
| Card 6 body | One supported runtime, typed contracts, docs match reality. |

Cards 1–3 are pains, 4–6 the matching fixes, revealed in order.

- Say: "Three pains, three fixes — the rest of the deck walks each pair."

## S3 — Core problem (title `Listings with blanks get turned away`)

Layout: T-cols-3. Fragments: 3.

| Item | Content |
|------|---------|
| Card 1 h3 | Problem |
| Card 1 body | A seller's listing is missing the bathroom count or the plot size. The API rejects the whole request. No price comes back. |
| Card 2 h3 | Impact |
| Card 2 body | Up to [nnr.recovered] of live requests stall. The agent phones back, the seller waits, the valuation queue stops. |
| Card 3 h3 | Cost |
| Card 3 body | Every rejected listing is a conversation restarted and a deal delayed. Coverage, not accuracy, is what leaks. |

- Say: "A missing bathroom field used to kill the whole valuation."

  ## S4 — Missing value approaches (title same, `id="s4"`, `is-stage-0..4`)

Layout: T-houses-staged. Fragments: 4 (hidden drivers). Corner subtitle:
only the staged equation shows (stages 0/4: none). Houses STATIC (mist,
fixed). Markers staged (floating house + stem + equation below + equation
on the pick).

| Item | Content |
|------|---------|
  | Corner sub (stage 1 only) | Average Value (amber) |
  | Corner sub (stage 2 only) | Mean value (blue) |
  | Corner sub (stage 3 only) | Nearest Neighbor (purple) |
| House prices (98042 quantiles, y=232) | $105k $201k $223k $249k $267k $284k $303k $326k $350k $387k $450k $859k |
| Hint (`p.ph-stage-hint`, stage 0 only) | Twelve homes, four groups of three. Each group runs 25% bigger than the last; inside a group two homes vary by ±5%. Click for each approach. |
| Marker 1 | Floating house + `Average Value` below + pick `AVG $334k = Σ/12` |
| Panel 1 h3 | Average Value |
| Panel 1 body | Add all twelve sizes, divide by twelve. One city-wide number fills every blank. Simple; ignores the house. |
  | Marker 2 | Floating house + `Mean value` below + pick `MED $294k = mid($284k,$303k)` |
  | Panel 2 h3 | Mean value |
  | Panel 2 body | Sort the row, take the middle. Mansions stop skewing the answer. Still one number for all blanks. |
  | Marker 3 | Floating house + `Nearest Neighbor` below + pick `5-NN → $293k = w-avg(5)` |
  | Panel 3 h3 | Nearest Neighbor |
| Panel 3 body | Take the 5 nearest sizes; closer homes count more. Each blank gets its own answer from its own street. |
| Panel 4 h3 (Summary) | Summary: similar homes win |
| Panel 4 body | Average and middle value give every blank the same city-wide guess. Similar homes adapt to the house — price-moving fields [knn.range] than averages. |
| Panel 4 pick | `p.ph-panel-nums`: AVG $334k · MED $294k · 5-NN → $293k |

- Say (per click): "City average — one number for every house." →
  "Middle value — mansions stop skewing it, still one number." →
  "Five similar homes, closest count most — each blank gets its own answer." →
  "Summary: neighbours adapt, averages don't."

## S5 — Why similar homes won (title same)

Layout: T-cols-3 + T-bars in Card 3 + foot. Fragments: 4 (3 cards + foot).

| Item | Content |
|------|---------|
| Card 1 h3 | Problem |
| Card 1 body | Averages ignore the house in front of us. A flat and a family home get the same guess. |
| Card 2 h3 | Impact |
| Card 2 body | Similar homes track the features that move price: size, grade, age, bathrooms. |
| Card 3 h3 | Savings |
| Bar 1 | Upper floor area [knn.sqftAbove] (`meter` 17/20) |
| Bar 2 | Bathrooms [knn.bathrooms] (`meter` 16/20) |
| Bar 3 | Floors [knn.floors] (`meter` 15/20) |
| Bar 4 | Grade [knn.grade] (`meter` 14/20) |
| Foot (`p.ph-foot`) | Caveat: the headline average hides this — two plot-size fields with wild outliers swamp it. |

- Say: "On the fields that move price, neighbours beat averages 14–17%."

## S6 — Faster answers (title same)

Layout: T-cols-3 + foot. Fragments: 4 (3 cards + foot).

| Item | Content |
|------|---------|
| Card 1 h3 | Problem |
| Card 1 body | Every request reloads the model, the maps, and the comparables from disk. Under load, that queues up. |
| Card 2 h3 | Impact |
| Card 2 body | Agents wait on every valuation. Peak traffic makes every answer slower. |
| Card 3 h3 | Savings |
| Card 3 body | Load once when the service wakes, serve from memory. Typical [perf.v1p50] down to [perf.v2p50]. Slow tail [perf.v1p95] down to [perf.v2p95]. |
| Foot (`p.ph-foot`) | Local harness, 30 repeated calls, same machine — not a production promise. |

- Say: "Before, every knock reloaded the whole office. Now we load once."
- Sources: `src/api/endpoints.py:36` per-request `load_artifacts()` vs
  `src/api/lifespan.py:20` load-once.

## S7 — Errors you can act on (title same)

Layout: T-cols-2. Fragments: 2, no foot.

| Item | Content |
|------|---------|
| Card 1 h3 | Before |
| Card 1 body | A mistyped area code blows up. The agent sees a dead end and starts over. |
| Card 2 h3 | After |
| Card 2 body | A plain-words reply names the bad code. Fix the digit, move on. |

- Say: "A typo'd postcode used to blow up. Now it names the bad code."
- Source: `src/api/shared.py:151-153` (404 `Unknown zipcode`); tests
  `test/unit/test_api_unit.py:57-83`.

## S8 — Modernised base (title same, `section.ph-caps`)

Layout: T-caps-6. Fragments: 6.

| Item | Content |
|------|---------|
| Cell 1 h3 | Missing-data handling |
| Cell 1 body | Blanks filled from similar homes. |
| Cell 2 h3 | Load-once serving |
| Cell 2 body | Model and data cached at startup. |
| Cell 3 h3 | Clear errors |
| Cell 3 body | Unknown areas named in plain words. |
| Cell 4 h3 | Current runtime |
| Cell 4 body | One supported version, locked installs. |
| Cell 5 h3 | Typed contracts |
| Cell 5 body | Docs promise what the API returns. |
| Cell 6 h3 | Tested paths |
| Cell 6 body | Blank, missing, zero, and bad-area covered. |

- Say (one line each): "Messy data scores. One load. Plain errors.
  Supported runtime. True docs. Covered edges."
- Sources: Python 3.10 → 3.14, pip → uv lockfile; `PredictionResponse` /
  `HealthResponse` / `ErrorDetail` typed models.

## S9 — Close (title `What you get`, `section.ph-why`)

Layout: T-why-3 + handoff. Fragments: 4 (3 cards + handoff).

| Item | Content |
|------|---------|
| Card 1 num | 01 |
| Card 1 h3 | No listing left behind |
| Card 1 body | Incomplete paperwork still prices. |
| Card 2 num | 02 |
| Card 2 h3 | Answers in milliseconds |
| Card 2 body | Headroom for busy days. |
| Card 3 num | 03 |
| Card 3 h3 | Errors you can act on |
| Card 3 body | On a base we can maintain. |
| Handoff (`p.ph-handoff`) | Next: live demo — a blank, a bad area code, and speed. |

- Say: "No listing left behind, answers in milliseconds, errors you can
  act on. Next I'll show it live."

## Appendix D — Part 2 demo runbook (hidden slide + checklist)

Layout: T-appendix-hidden. `section[data-visibility="hidden"]`, never
presented. Five plain `<li>` mirror checklist items 1–5 below; item 6 is
talk-track only, no slide.

| Item | Content |
|------|---------|
| Step 1 | Blank fields score; same payload to the old endpoint fails. |
| Step 2 | Bad area code returns a named plain-words reply. |
| Step 3 | Load-once versus per-request; cite harness numbers, offer live rerun. |
| Step 4 | Health check passes when ready, fails clearly when not. |
| Step 5 | Docs show typed responses with examples. |

1. Missing data: POST `/predict/v2` with `bathrooms: null`,
   `sqft_lot: null` → 200 + `predicted_price`; same payload to v1 fails.
   Trace: `src/api/endpoints_v2.py:63-71`.
2. Unknown zip: `"zipcode": "00000"` → 404 naming the zip.
3. Speed: lifespan load-once vs v1 per-request; cite `DECK_METRICS`
   p50/p95, offer live re-run.
4. Readiness: `/health/v2` 200 vs 503 when artifacts missing.
5. Contracts: `/docs` shows typed responses with examples.
6. AI usage (`CANDIDATE_PROJECT.md:163-170`): tool used, context technique,
   validation via unit/integration suites + live probes.
