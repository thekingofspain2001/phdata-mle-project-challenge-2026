# Deck script — mirror of `presentation/deck.html`

Single-file reveal.js deck. This script is a build spec: an agent given
only this file should rebuild a deck visually and structurally similar to
`deck.html`. Keep the two in sync — every deck edit updates this script,
every script change lands in the deck.

Audience: 10-minute Part 1, non-technical (`CANDIDATE_PROJECT.md:11`).
Part 2 is live demo, no slides — runbook in the hidden appendix (S8).

**Deck shape as of this revision: 8 sections — 7 visible + 1 hidden
appendix.** Titles live in-slide (`.ph-head > h2`); there is no global
title element and no title-sync JS. S4 staging is pure CSS driven by
reveal's `.visible`; there is no staging JS.

## Build

- One file, no build step. CDN: `reveal.js@4/dist/reveal.css`,
  `reveal.js@4/dist/reveal.js`, `reveal.js@4/plugin/markdown/markdown.js`.
  Font: Inter 400/500/600 via Google Fonts (+ preconnect).
  Favicon: the phData 32×32 PNG hosted on `i0.wp.com` (`deck.html:7-8`).
- `<title>Sound Realty — Valuation API Production Hardening</title>`.
- `<style>` in `<head>`, one `<script>` at body end after the two CDN
  tags. No `style=""` attributes in the markup.
- `--ph-font` names `"Aspekta"` first, but only **Inter** is loaded from
  Google Fonts; Aspekta is a local/licensed face that falls back to Inter
  when absent. Do not "fix" this by adding a webfont link.
- Slide count: 8 sections. No vertical (nested) slides.

## Global chrome

**(a) Background** — `.reveal` (`deck.html:98-107`): navy
`background-color:#111f3a` + inline-SVG motif tile (`--ph-pattern`,
783×642, mist/mint strokes at ~0.22 opacity), `background-size:var(--ph-motif-size)`
(`50% auto`), `background-repeat:no-repeat`, `background-position:100% 100%`
(pinned bottom-right). Fixed on `.reveal` so it never moves on transition.

**(b) Section box** — `.reveal .slides section` (`deck.html:120-133`):
`height:100% !important`, `display:flex !important`,
`flex-direction:column`, `background:transparent`, `text-align:left`,
`transition-duration:var(--ph-t-slide)`. The `!important`s restore flex
over reveal's inline `display:block`. **These rules are on EVERY section,
not just `.present`** — scoping them to `.present` made S6's chart card
lose its height cap on the way out and reflow the body 961px → 1004px.

**(c) Brandline** — `header.ph-global-top` (`deck.html:137-151`):
absolute, `top/left/right:0`, `height:var(--ph-header-h)` (10vh),
`z-index:30`, flex, `align-items:center`, `gap:var(--gap-md)`,
`padding:0 var(--gap-md)`, `pointer-events:none`. It contains **only**
`.ph-brandline`.
  - `.ph-brandline` — flex, `align-items:center`,
    `gap:calc(var(--gap-sm) * 1.51)` (logo ink to separator balanced),
    `font-size:var(--fs-brand)`, `white-space:nowrap`.
  - `.ph-logo` — `height:var(--logo-size)` (6vh), `flex:0 0 auto`,
    `width:auto`, `margin-right:calc(var(--gap-sm) * -0.51)` (absorbs PNG
    side padding).
  - `.ph-sep` — the literal `|`, `color:var(--ph-ink-muted)`.
  - `.ph-client` — Georgia serif stack, `28px` / `line-height:27px`,
    `gap:var(--gap-sm)`, `color:var(--ph-ink-on-dark)`. Contains
    `.ph-client-logo` (inline house glyph, 27×27, `color:#e8b04b`,
    `translateY(-1px)`) then the text `Sound Realty`.

**(d) In-slide header** — `.ph-head` (`deck.html:199-221`):
`flex:0 0 auto`, flex column, `align-items:flex-end`, `padding:12px var(--pad-x) 0`,
`min-height:81px`. `h2` right-aligned, `font-weight:400`,
`font-size:var(--fs-h2)`, `line-height:1.25`, `color:var(--ph-accent)`,
`white-space:nowrap` + ellipsis. Its baseline meets the brandline's.

**(e) Draw area** — `.ph-body` (`deck.html:224-234`): `flex:1 1 auto`,
`min-height:0`, `width:100%`, `overflow:hidden`, flex column,
`gap:var(--sp-sm)`, `padding:var(--sp-sm) var(--pad-x) var(--pad-foot)`.
Cannot write over header or footer.

**(f) Controls + slide number** — `.reveal .controls`
(`deck.html:1388-1404`): `color:#6f8590`,
`bottom:calc((var(--ph-footer-h) - 36px)/2)`, all four directions
`color:currentColor`, `:hover/:focus-visible/:active` → `var(--ph-mint)`.
`.reveal .slide-number` (`deck.html:1407-1416`): `26px`, `var(--ph-mist)`,
transparent background, `text-decoration:none` on both the element and
its inner `a`. Placement is reveal's own default (`controlsLayout:"edges"`).

- Layout rule: reveal.js owns `.slides` geometry (`width:1270`,
    `height:961`, `margin:0.04`, `center:true` — uniform scale, no CSS
    overrides). Each `section` flex-fills its slide box; `.ph-body`
    flex-fills that. Cover (`T-cover`) is the one exception: centred,
    `padding:0`.

## Tokens (`:root`)

```css
--ph-navy:#111f3a; --ph-mint:#a5feca; --ph-mist:#bcccd4;
--ph-accent:#38BDF8;
--ph-card-border:rgba(165,254,202,.5);
--ph-card-border-accent:rgba(56,189,248,.5);
--ph-card-bg:rgba(12,20,46,.72);
--ph-ink-on-dark:#ffffff; --ph-ink-muted:rgba(255,255,255,.75);
--ph-font:"Aspekta","Inter",system-ui,sans-serif;

/* Fill-in approaches (S4/S5) — one colour per method. */
--av:#e8b04b; --md:#7fb6d9; --knn:#c792ea;
/* Imputation COST, not a fourth approach (S6). */
--imp:#ef8354;
/* Same three method colours at 22%, for the S5 figure cells. */
--tint-av:color-mix(in srgb, var(--av) 22%, transparent);
--tint-md:color-mix(in srgb, var(--md) 22%, transparent);
--tint-knn:color-mix(in srgb, var(--knn) 22%, transparent);

/* Type scale: slide px at the 1270x961 design size. */
--fs-brand:16px; --fs-h1:52px; --fs-h2:29px; --fs-sub:26px; --fs-h3:21px;
--fs-lead:22px; --fs-body:18px; --fs-caption:14px;

/* Spacing scale (slide px); chrome bands stay viewport. */
--sp-xs:8px; --sp-sm:15px; --gap-sm:13px; --gap-md:25px;
--ph-header-h:10vh; --ph-footer-h:8vh;
--pad-x:60px; --pad-foot:72px;

/* One motion language. */
--ph-t-slide:1.2s; --ph-t-fade:.18s;
--ph-ease:cubic-bezier(.26,.86,.44,.985);
--ph-ease-soft:cubic-bezier(.4,0,.2,1);

/* Shape, line, logo. */
--rad-card:12px; --rad-cell:10px; --line-sm:2px; --line-md:3px;
--logo-size:6vh; --ph-motif-size:50% auto;
--ph-pattern:url("data:image/svg+xml,…");  /* 783×642 tile */
```

Colour roles, stated so a rebuild does not invent new ones:
- `--ph-mint` = "current answer / selected": card border, selected chip
  fill, S5 winning figure, slide-number-adjacent chrome. Never a method.
- `--ph-accent` = deck accent for headings, pair labels (`From`/`To`,
  S7 `h4`, the S5 second header row) and the S4 summary stage. It is
  **not** a method colour and carries no per-method meaning.
- `--av/--md/--knn` = the three S4/S5 approaches, reused on the S6 donut
  slices so a figure maps to a method without a legend.
- `--imp` = warm coral, cost on top of the purple calculation, so it
  never reads as a fourth fill-in method.

## Metrics (single source)

Inline `DECK_METRICS` (`deck.html:2575-2594`); every `[data-metric]`
span hydrates on load by splitting the key on `.` and walking the object.
Never hardcode a number in body copy — always a keyed span:

```js
cost: {
  dev: "9.7 ms", load: "1.2 ms", calcOrig: "4.3 ms", calcV2: "9.4 ms",
  totalOrig: "15.2 ms", totalV2: "9.4 ms",
  devDelta: "−9.7 ms", loadDelta: "−1.2 ms",
  calcDelta: "+5.2 ms", totalDelta: "−5.8 ms",
  improvement: "38% faster",
}
nnr: { recovered: "10–20%" }
```

Rounded display values. Underlying harness: median of 5 runs × 1000
calls, one at a time, over the 201 examples published on `/docs`. Each
cost is a subtraction — `dev = original − noprint`,
`load = original − cached`, `calc` is the remainder. Reproduce with
`uv run python test/benchmark/benchmake.py` (`test/benchmark/benchmake.py`).

Note: S2's Opportunity/Impact cell hardcodes "10% to 20%" as plain text
rather than a `[nnr.recovered]` span, and S3 restates the same gap as a
flat `15%`. Three copies of one business estimate. If it ever moves, move
all three together.

## Templates

Class names, flex rules and fragment order verbatim from `deck.html`.

- **T-cover** — S1. `section.ph-cover > div.ph-body` (`justify-content:center`,
    `align-items:center`, `text-align:center`, `padding:0`). Single `h1`,
    `margin:auto`, `max-width:20ch`, `line-height:1.15`. No fragments,
    no metrics.
- **T-stack** — S2, S3, S5. `div.ph-cols.ph-is-stack`
    (`flex-direction:column`) of full-width `article.fragment.custom`.
    Cards take the shared `.ph-cols article` fill (below). S3 runs two
    cards rather than three and carries a subtitle.
- **T-cols-n** — the inner rows of S2. `div.ph-cols`
    (`flex:1 1 auto`, `min-height:0`, flex row, `gap:var(--gap-md)`).
    Shared card surface for `.ph-cols article` and `.ph-panel`
    (`deck.html:312-321`): `background-color:var(--ph-card-bg)`,
    `backdrop-filter:blur(2px)`, `border:var(--line-sm) solid
    var(--ph-card-border)`, `border-radius:var(--rad-card)`,
    `padding:var(--sp-sm) var(--gap-sm)`, `flex:1 1 0`.
    `h3`/`h4` mint at `--fs-h3`.
- **T-nested** — `.ph-cols article article` takes
    `border-color:var(--ph-card-border-accent)` and its `h4` takes
    `var(--ph-accent)`: same spacing and scale, distinct colour, for the
    sub-boxes inside an S2 card.
- **T-rowgrid** — S2 Performance only (`deck.html:340-364`).
    `.ph-cols.ph-rowgrid` is a 3-column grid with
    `column-gap:var(--gap-md)`, `row-gap:var(--sp-xs)`; each `article`
    does `grid-row:span 3` with `grid-template-rows:subgrid`, and its
    `ul` spans `grid-row:2 / -1` on its own subgrid. Bullet 1 of Issues,
    Impact and Cost therefore share one line and bullet 2 the next,
    however many lines each wraps to. Keep the list in flow (indent, disc
    markers); only its tracks are borrowed.
- **T-houses-staged** — S4 only (`section[data-s4]`, `:has()` on the
    driver fragments). See §S4.
- **T-figures-grid** — S5 only. Two tables rendered as CSS grids; see §S5.
- **T-chart-costs** — S6 only. Donut SVG + cost table; see §S6.
- **T-s7-split** — S7. `div.ph-s7` grid `minmax(0,0.62fr) minmax(0,2.38fr)`,
    `ol.ph-scr.ph-s7-chips` left, `div.ph-cols.ph-s7-panes` right. See §S7.
- **T-appendix-hidden** — S8. `section[data-visibility="hidden"]`, never
    presented; plain `ol`, no `.ph-*` grid classes, 5 items.

Fragment-state conventions:
- `article.current-fragment` (`deck.html:376-379`) — mint border +
  `box-shadow:0 0 24px rgba(165,254,202,.25)`. Reveal's runtime supplies
  the class; one per click.
- `fragment custom` (S2's three cards, S5's two cards) — reveal's opt-out
  from default fragment styling. The element stays visible from load
  while still holding one step, so those slides open showing all their
  cards.
- Hidden drivers (`.s4-drivers`) — `position:absolute`, `0×0`,
  `overflow:hidden`. Empty `span`s that exist only for `.visible`.

## Reveal config + JS

```js
Reveal.initialize({ width:1270, height:961, margin:0.04,
  minScale:0.2, maxScale:2.0, center:true, hash:true, slideNumber:true,
  controlsLayout:"edges", transition:"slide",
  plugins:[RevealMarkdown], backgroundTransition:"none" });
```

Three IIFEs run before it, in this order:

1. **`[data-metric]` hydration** (`deck.html:2596-2601`). Replaces
   `textContent` only when the key resolves; a bad key is left alone.
2. **S6 donut generator** (`deck.html:2623-2846`). Every dimension is a
   formula over the millisecond constants below, so no ring can drift
   out of step with its own numbers:
   ```js
   W = 30; CY = 160;
   REF = { ms: 15.23, r: 120 };   // radius  r = REF.r * ms / REF.ms
   LEAD = { in: 12, out: 56, label: 64 };
   GAP = 62;
   dev = 9.72; load = 1.22; calcOrig = 4.29; calc = 9.44; impute = 5.12;
   allNull = calc + impute;       // 14.56
   fromTotal = dev + load + calcOrig;  // 15.23
   ```
   - Band area `π((r+w/2)² − (r−w/2)²) = 2πrw` is linear in `r` **only
     because every ring shares one stroke width `w`**. `w` is a single
     constant here, never per-ring; vary it and the encoding quietly
     stops being proportional. Small rings only look fatter (`w/r`).
   - Arc `2πr · seg.ms / ring.ms`, painted as
     `stroke-dasharray: \`0 ${off} ${arc} ${C}\`` — leading zero, gap as
     long as everything drawn so far, the slice, then a whole
     circumference to close it. Never a negative `stroke-dashoffset`
     (that shifts the pattern forward and shortens every slice), and
     never a closing term of `C - off - arc` (zero on a ring's last
     slice, which drops its tail and leaves a hole in the track).
   - `start` rotates a whole ring once; slices are placed by cumulative
     offset inside it, so per-slice rotations would fight the offsets.
   - `viewBox` is measured off the rendered content in a
     `requestAnimationFrame` pass (padded by `W/2 + 6`, because
     `getBBox()` is geometric and a stroked ring reaches `W/2` past it).
     The number and its unit are centred on each ring as **one block**
     from real glyph boxes in that same pass — inline `getBBox()` returns
     an empty box before layout flushes, which throws the pair to the
     bottom of the slide.
3. **S7 capture zoom** (`deck.html:2854-3048`). Each `.ph-validation`
   capture owns its overlay end to end — its own `<dialog>`, caption,
   measured ratio and transition — so there is no shared "which one is
   open" state to get wrong. `<dialog>` is a native top-layer modal, so
   reveal's slide transform cannot clip it and Esc/backdrop/focus come
   from the platform. Key details, all load-bearing:
   - `MOVE = "var(--ph-t-slide) var(--ph-ease-soft)"`, duration read once
     from the token, and a single transform pair per flight. The start
     state must be on a painted frame first, or the browser snaps.
   - The picture is **moved into** the dialog while zoomed, so it is never
     under the dim and never clipped; on close it lands first and is only
     re-inserted into the slide after the flight.
   - The box **is** the picture: `fit()` writes `--ph-shot-w` (one width
     shared by both captures, so both render at one scale), `--ph-shot-gap`
     (the gap that spreads what is left into three equal margins), and
     `--ph-shot-pad` (the gap from the pane's top border to its title, read
     off the live layout, less the pane's bottom padding — reserved as the
     `figure`'s bottom padding so the capture's foot clears the bottom border
     by the same distance the title clears the top one), and each capture's
     own `--ph-shot-ar` sits on its `figure`, not on the capture — a flight
     clears the capture's inline `cssText` when it lands, which would take
     the ratio with it. All are read as layout px and are independent of
     what they write, so one pass settles the layout and no resize hook is
     needed.
   - The zoom flight still measures with `painted(box, ar)`, so a change
     to the box size moves the start position with it.
   - The dialog's own sizing runs off two custom properties JS sets per
     capture: `--ph-shot-ar` (`naturalWidth / naturalHeight`, the ratio)
     and `--ph-shot-num` (the same value as a bare number). The box takes
     `min-height:calc(min(92vw / var(--ph-shot-num), 88vh) + var(--sp-xs))`
     and the capture `width:min(92vw, calc(88vh * var(--ph-shot-num)))`,
     so the wrapper is exactly the picture — no letterbox to push the
     caption away from it, and each capture still maximises (the
     landscape From on width, the portrait To on height).
   - Keys are `stopPropagation`-ed inside the dialog, because reveal
     listens on `document`.
   - `prefers-reduced-motion` collapses the fade and shortens the flight.

## S1 — Cover (`#s1-cover`, `class="ph-cover"`)

Layout: T-cover. No fragments, no metrics, no sub-head.

| Item | Content |
|------|---------|
| H1 | Housing Price Prediction Service Analysis |

- Say: "Every listing gets a price — even when the paperwork is incomplete."

## S2 — Executive summary (`#s2-summary`)

Layout: T-stack. Fragments: 3, all `fragment custom`, so all three cards
are visible from load while each still holds one step.

Card 1 — `h3` **Opportunity**, then a nested `.ph-cols` of three sub-boxes:

| Sub-head | Content |
|----------|---------|
| Missing / Unknown Data | Predict API service only works if all fields are provided. |
| Impact | 10% to 20% of data is missing at least one field. |
| Cost | Manual lookup of listing data and non data based best guesses. |

Card 2 — `h3` **Performance**, then a `.ph-cols.ph-rowgrid` (T-rowgrid)
so the bullets align across the three boxes:

| Sub-head | Bullet 1 | Bullet 2 |
|----------|----------|----------|
| Issues | Model and Demographic reread per predict API call | Running non production code |
| Impact | Negative performance | Negative performance |
| Cost | 1.44 ms per call | 12.2 ms per call |

Card 3 — `h3` **Modernization**, then a nested `.ph-cols` of four sub-boxes:

| Sub-head | Content |
|----------|---------|
| Runtime | `ul`: Update Runtime Environment. / Update Development Framework. |
| Type hints | Upgrade code to detect errors in development vs production. |
| Validation | Leverage the FastAPI framework to validate input fields with Pydantic models. |
| Swagger | Make sure FastAPI's Swagger documentation matches the actual API behavior. |

- Say: "Three problems, three fixes — the rest of the deck walks each pair."
- Sources: per-request `load_artifacts()` in `src/api/endpoints.py` vs
  load-once in `src/api/lifespan.py`.

## S3 — Opportunity (`#s3-problem`, `data-s3`)

Layout: T-stack, two cards. Fragments: 2, both `fragment custom`, so both
cards are visible from load while each still holds one step.

The `h2` is the **chapter** and is fixed for every slide in the deck that
talks about this topic — it does not change per slide. The `p.ph-subtitle`
under it names what THIS slide covers. Reuse `.reveal .ph-subtitle` as
S4 does; it is a single static line here, not a staged `.ph-subs` stack.

| Item | Content |
|------|---------|
| h2 (chapter) | Opportunity |
| Subtitle | The approach |

Card 1 — `h3` **The case**, four labelled lines, no prose paragraph:

| Label | Line |
|-------|------|
| Problem | The service requires all fields. |
| Issue | 15% of requests fail because one or more fields is missing. |
| Impact | The cost of finding the actual data, or the inaccuracy of the service output when a made-up input is supplied. |
| Solution | Approximate the value of the missing field from the data already held. |

Card 2 — `h3` **The method**, one lead line then three named entries, each
two sentences following the same pattern (how the figure is derived, then
what it corresponds to):

Lead: The three standard ways of estimating a missing value, differing only
in how much of the rest of the record they use.

| Name | Derivation | Corresponds to |
|------|------------|---------------|
| `The average` | the values of all items in the group added together and divided by the size of the group | no item in the group; it exists only as a calculation |
| `The middle value` | the value of the item sitting in the middle of the group once it is ordered | one known item in the group, whichever that happens to be |
| `Nearest comparables` | the values of the items in the group closest to this one on the remaining fields | a small set of known items, the closest counting most |

**Content rules for this slide:**

- Missing data only. No property values, prices or valuations — the problem
  is that the service requires all fields, nothing more.
- No statistics from the research notebooks. S4 carries the arithmetic and
  S5 the results; this slide carries the argument.
- The three candidates are named, not ranked, and not shown working. S4
  stages them and picks the winner.
- No figures. The dataset profile was cut from this slide.
- The `15%` in Card 1 sits inside the `10% to 20%` already on S2, so the two
  slides do not contradict each other.

- Say: "One missing field fails the request. We fill it from what the record
  already tells us — these are the three ways, and here is how we chose."
- Sources: imputation method families per the Statistics Canada quality
  guidelines (mean, ratio/regression and nearest-neighbour deterministic
  imputation; the stated principle is to use available auxiliary
  information, choosing by strength of association between fields).

## S4 — Missing value approaches (`#s4-approaches`, `data-s4`)

Layout: T-houses-staged. Fragments: 4 hidden `.ph-s4-go` drivers.
**Staging is CSS only** — `section[data-s4]:has(.ph-s4-go:nth-of-type(N).visible)`
selects stage N. There is no `setS4Stage`, no `is-stage-N` class, no
`Reveal.slide(h,0,-1)` reset. Houses are STATIC (mist stroke, fixed
transforms); markers, dashed boxes, subtitle and panel fade per stage.

**Houses** — 12, in four groups of three sorted smallest to largest.
`svg#houses-svg`, `viewBox="15 -80 1195 340"`, `color="#BCCCD4"`.
Baseline line `y=214` from `x=35` to `x=1188`.

| Group | x | scale | sqft label (y=232) |
|-------|---|-------|--------------------|
| A | 54 / 98 / 142 | 0.76 / 0.8 / 0.84 | 1235 1300 1365 |
| B | 241 / 297 / 353 | 0.95 / 1.0 / 1.05 | 1520 1600 1680 |
| C | 551 / 619 / 687 | 1.1875 / 1.25 / 1.3125 | 2090 2200 2310 |
| D | 984 / 1066 / 1148 | 1.484 / 1.5625 / 1.6406 | 3610 3800 3990 |

All `translate(·,210)`. Intra-group gaps clear the roofs
(44/56/68/82u); inter-group gaps are staggered 1:2:3 (99/198/297u);
both edges pinned to the baseline. `.h-nn` marks the five largest
(groups C and the first two of D) — those are the nearest-neighbour set.
The `<g id="hs">` glyph strokes with `currentColor`, so `stroke` alone
leaves every house grey.

**Dashed input boxes** (`.bx`, `y=116`, `height=132`, `stroke-dasharray="8 5"`):

| Id | x | width | Colour | Shown at stage |
|----|---|-------|--------|----------------|
| `bx-avg` | 16 | 1190 | `var(--av)` | 1 |
| `bx-med` | 324 | 260 | `var(--md)` | 2 |
| `bx-knn` | 584 | 611 | `var(--knn)` | 3 |

**Markers** (`.mk`) — floating house + name above + value below + a
vertical leader with an arrowhead:

| Marker | cx | House scale | Name (y=-66, 20px) | Value (y=30, 16px) | Leader | Marker id |
|--------|----|-------------|--------------------|--------------------|--------|-----------|
| Average | 634 | 1.264 | `Avg` | `2225` | y 44→108, `url(#arr-av)` | `arr-av` |
| Medium | 452 | 1.119 | `Medium` | `1885` | y 44→108, `url(#arr-md)` | `arr-md` |
| NN | 952 | 1.465 | `NN(5)` | `3468` | y 44→116, `url(#arr-knn)` | `arr-knn` |

No extra scale or offset on the KNN marker: its base transform already
encodes 3468, and the other two carry no transform, so any override
would break both the value sizing and the shared baseline.

**Corner subtitles** — `div.ph-subs`, a one-cell grid
(`min-height:calc(var(--fs-sub) * 1.3)`) holding four stacked
`p.ph-subtitle.ph-s4-sub` at `opacity:0`; the active one fades to 1.
Stage 4 shows all three markers and the summary panel.

| Stage | Subtitle | Class |
|-------|----------|-------|
| 1 | Average Value | `ph-is-av` (amber) |
| 2 | Medium value | `ph-is-md` (blue) |
| 3 | Nearest Neighbor | `ph-is-knn` (purple) |
| 4 | Summary: similar homes win | `ph-is-sum` (`--ph-accent`) |

`p.ph-stage-hint` is `position:absolute` **below** the top row
(`top:100%`), not in flow — in flow it added ~19px that the 50% flex
basis absorbed, nudging the houses down on load only. Hidden once driver
1 is visible.

| Item | Content |
|------|---------|
| Hint | Twelve homes, four groups of three. Each group runs 25% bigger than the last; labels are living area in sq ft. Click for each approach. |

**Bottom panels** — `.ph-stage-bottom` is `flex:0 0 0` until driver 1
fires, then `flex:0 0 50%`. `.ph-panels` is a flex row; every
`.ph-panel` is `display:none` and exactly one is `display:flex` per
stage. Each panel is `ph-panel-words` (50%) + `ph-panel-pick` (50%).

| Stage | Panel `h3` | Inputs | Values produced | Body |
|-------|-----------|--------|-----------------|------|
| 1 | Average Value | Every house in the data set | 1 | A single city-wide figure, so the imputed value ignores the house being valued. |
| 2 | Medium value | All houses in the data set | Up to 2 | One or two central houses set the answer, so mansions no longer skew it — but the result is still not specific to the house being valued. |
| 3 | Nearest Neighbor | The n nearest houses | Up to n | Each blank receives its own weighted answer, drawn from the comparable homes around it rather than from the whole data set. |
| 4 | Summary: which value to fill | — (`ul` instead of `dl`) | — | See bullets below. |

`dl` is a 2-column grid so the labels align into one column and the
figures into a second across all four panels; `dt` is uppercase
caption-size in `--ph-ink-muted`.

Summary panel bullets (`.ph-panel.ph-is-sum .ph-panel-words ul`, no list
markers, flex column):

- Size driven — one value for the whole data set
- n points in the data set — up to n values
- Unique calculated value per data point

**Pick SVGs** — one per panel, `max-height:240px`, `width:100%`:

| Panel | Content |
|-------|---------|
| 1 | One house + `=AVERAGE(1235,1300,1365,1520,1600,1680,` / `2090,2200,2310,3610,3800,3990)` / `= 2225` |
| 2 | One house + `=MEDIUM(1235,1300,1365,1520,1600,1680,` / `2090,2200,2310,3610,3800,3990)` / `= 1885` |
| 3 | Five houses + `=SUMPRODUCT({3800;3610;2310;2200;2090},` / `{1/190;1/380;1/1680;1/1790;1/1900})` / `/SUM({1/190;1/380;1/1680;1/1790;1/1900})` / `= 3468` |
| 4 | `p.ph-panel-nums`: `AVG 2225 · MEDIUM 1885 · NN(5) 3468` |

- Say (per click): "City average — one number for every house." →
  "Middle value — mansions stop skewing it, still one number." →
  "Five similar homes, closest count most — each blank gets its own answer." →
  "Summary: neighbours adapt, averages don't."
- Sources: `notebooks/imputation_experiment.ipynb`,
  `notebooks/six_way_imputation_comparison.ipynb`,
  `src/data/future_unseen_examples.csv`.

## S5 — What the test actually showed (`#s5-results`)

Layout: T-stack of two cards + `p.ph-foot.fragment`. Fragments: 3
(two `fragment custom` cards, then the foot).

Card 1 — `h3` **Data and analysis**:
- `p` — A sample file of 3,000 sales was used. Each nullable field in turn was hidden and refilled from the other six. Median, mean and NN(5) each refilled it, as shipped and over standardized columns. ZIP code is excluded: it is required and never imputed.
- `p.ph-muted` — Distinct values returned across the 3,000 houses, and the range they covered.
- `table.ph-table.ph-figures.ph-spread` — see below.

Card 2 — `h3` **Quality**:
- `p.ph-muted` — Normalized mean absolute error (NMAE), scaled by each field's own range. Lower is closer; the lowest figure per row is in mint.
- `table.ph-table.ph-figures.ph-quality` — see below.

**The grid-table treatment** (`deck.html:456-645`). A CSS `display:grid`
replaces table layout, because 11 nowrap min-content columns overflowed
the card and `table-layout` gave no control over which column gave way.
- `thead`, `tbody`, `tr` all `display:contents`, so the grid sees one
  flat list of cells and the cells keep their `th`/`td` elements.
- A `> table` selector on these rules would outrank the grid rule on
  specificity and collapse the table onto one line; they must hang off
  the table, not off the article.
- `colSpan`/`rowSpan` do nothing in a grid, so the header placement is
  done in CSS: `th[scope="colgroup"] { grid-column: span 3 }` and
  `th[rowspan] { grid-row: span 2 }`. The attributes stay in the markup
  as the source of truth — the CSS mirrors them.
- `display:grid` drops the table role in Chrome and Safari, so roles
  (`role="table"` / `rowgroup` / `row` / `columnheader`) are declared on
  the elements and `scope` attributes are kept.
- Shared `.ph-figures` treatment: mono figures, `tabular-nums`, right
  aligned. Body cells stay `--ph-ink-muted`; `td:nth-child(3n + 1)` (the
  `max`) takes `font-weight:600` because the colour belongs to the
  calculation's block, not to one figure inside it.
- `.ph-spread` — `grid-template-columns: max-content repeat(15, minmax(max-content, 1fr))`,
  `column-gap:9px`, `row-gap:2px`, `align-content:space-between` so the
  rows take the card's slack. A column gap, not `space-between`: that
  stranded each group title between its own sub-labels and made the
  per-group `border-bottom` read as one rule across the grid.
- `.ph-quality` — `max-content repeat(4, minmax(max-content, 1fr))`, five
  tracks, no second header row.

**Colour and tint map** (each calculation keeps one colour; the tint says
which method, the ink says it is a measurement). Row's first child is
the label, so the `n/min/max` triples sit at columns 5-7 (average),
8-10 (median), 11-13 (NN) and 14-16 (NN scaled). The sub-label row has
no label cell, so it sits one step left at 4-6, 7-9, 10-12, 13-15.

| Calculation | Group-title colour | Tint token |
|-------------|--------------------|-----------|
| Data | neutral (no colour) | none |
| Average | `--av` | `--tint-av` |
| Median | `--md` | `--tint-md` |
| NN | `--knn` | `--tint-knn` |
| NN scaled | `--knn` (shares NN's tint) | `--tint-knn` |

The second header row takes `--ph-accent` at weight 600 — two blues on
one row would say nothing, and that row's job is to label.

**Spread table data** (Field | Data n/min/max | Average | Median | NN | NN scaled):

| Field | Data | Average | Median | NN | NN scaled |
|-------|------|---------|--------|----|-----------|
| Bedrooms | 13 / 0 / 33 | 1 / 3.4 / 3.4 | 1 / 3.0 / 3.0 | 2,664 / 1.1 / 8.5 | 2,519 / 1.1 / 7.2 |
| Bathrooms | 30 / 0 / 8 | 1 / 2.1 / 2.1 | 1 / 2.2 / 2.2 | 2,749 / 0.8 / 5.2 | 2,684 / 0.7 / 5.2 |
| Living area | 1,038 / 290 / 13,540 | 1 / 2,090 / 2,090 | 1 / 1,920 / 1,920 | 3,000 / 589 / 6,176 | 2,993 / 458.3 / 7,616 |
| Plot size | 9,782 / 520 / 1.651M | 1 / 15,180 / 15,180 | 1 / 7,628 / 7,628 | 2,450 / 857 / 288.2k | 2,469 / 780.9 / 435.6k |
| Floors | 6 / 1 / 3.5 | 1 / 1.5 / 1.5 | 1 / 1.5 / 1.5 | 1,553 / 1 / 3.2 | 1,425 / 1 / 3.1 |
| Above-grade area | 946 / 290 / 9,410 | 1 / 1,795 / 1,795 | 1 / 1,570 / 1,570 | 3,000 / 589 / 5,290 | 2,992 / 457.7 / 6,439 |
| Basement area | 306 / 0 / 4,820 | 1 / 294.8 / 294.8 | 1 / 0 / 0 | 1,310 / 0 / 2,224 | 1,304 / 0 / 2,279 |

Four significant digits, with a `k`/`M` suffix once the integer part runs
past four digits.

**Quality table data** (NMAE, lowest per row in `.ph-is-best`):

| Field | Average | Median | NN | NN scaled | Best |
|-------|---------|--------|----|-----------|------|
| Bedrooms | 0.806 | 0.731 | 0.611 | 0.571 | NN scaled |
| Bathrooms | 0.799 | 0.791 | 0.488 | 0.435 | NN scaled |
| Living area | 0.768 | 0.755 | 0.073 | 0.048 | NN scaled |
| Plot size | 0.327 | **0.243** | 0.314 | 0.337 | Median |
| Floors | 0.905 | 0.905 | 0.345 | 0.318 | NN scaled |
| Above-grade area | 0.779 | 0.741 | 0.072 | 0.056 | NN scaled |
| Basement area | 0.834 | 0.659 | 0.099 | 0.078 | NN scaled |

`.ph-is-best` is marked per cell in the markup, not derived in CSS: the
winner is not always the same column, and `min()` cannot compare across
cells. Plot size is the exception — median (0.243) beats both NN variants
there, because plot size is the one field where the unscaled NN is worse
than the median and scaling does not recover it.

**Foot** (`p.ph-foot.fragment`): Median and average answer **once** —
the same number for every house, whatever else is known about it. Nearest
neighbors answer thousands of times, and the answers track the range in
the data. That is the difference between guessing and estimating.

- Say: "Neighbours answer per house; averages answer once. That is the difference between guessing and estimating."
- Source: `test/quality/imputation_accuracy.csv` and the paired/
  summary CSVs alongside it.

## S6 — Performance (`#s6-performance`)

Layout: T-chart-costs. **No fragments** — the whole slide is one frame.
Three stacked blocks in `.ph-body`: a chart `.ph-cols`, a table
`.ph-cols`, and a foot.

Cards are overridden here (`deck.html:718-722`) to
`background-color:rgba(12,20,46,0.93)` and `backdrop-filter:blur(14px)`
— at the shared 2px/0.72 the background motif reads straight through
the rings and the figures. Scoped to this slide so nothing else shifts.

**Chart** — `article.ph-chart-card > div.ph-chart > svg#s6-chart`.
The SVG ships empty and is built by the donut IIFE. `svg { height:100%;
width:auto }` and `.ph-chart { flex:1 1 auto }`: every card's chart area
is the same height on screen, so all three rings render at one scale —
the only way band area can mean anything across three rings. Each
`viewBox` is then cropped to its own outer radius plus its callouts and
nothing else, so width never feeds back into ring size.

The SVG's `aria-label` is the chart's text alternative and states every
figure, so it must be regenerated with the chart rather than left as a
placeholder:

> Three donuts at one scale. Original route: 15.2 ms per call, split
> 9.7 ms debug code at 64%, 1.2 ms artifact loading at 8%, 4.3 ms
> calculation at 28%. V2 route: complete data 9.4 ms per call, all
> calculation; all seven nullable fields null 14.6 ms per call, 65%
> calculation and 35% imputation.

Measured areas come out at 62.0% and 95.6% of `2πrw` against a measured
62.0% and 95.6%.

| Ring | Centre | Total | Slices | Start |
|------|--------|-------|--------|-------|
| From (original route) | `FROM_CX = 180` | 15.23 ms | dev 9.72 `--av` · load 1.22 `--md` · calcOrig 4.29 `--knn` | -64.13° |
| To — complete data | `smallCx = 95` | 9.44 ms | calc 9.44 `--knn` | -90° |
| To — all null | `bigCx = 440` | 14.56 ms | calc 9.44 `--knn` · imputation 5.12 `--imp` in 4 pieces | 180° |

`rotate(a)` puts the first slice's start at `(90 + a)` degrees clockwise
from 12 o'clock: `rotate(-90)` starts at the **top**, `rotate(180)` starts
at 270. Getting this wrong swapped the two v2 labels.

The To group is shifted by `FROM_CX + fromOuter + GAP − (smallCx − outer(calc))`
— From's right edge is `cx + outer`, not `outer` alone.

The imputation arc is drawn as **four pieces with transparent gaps at 10,
15 and 20 per cent** of the imputed total, same colour throughout (the
gaps separate them, not hue). The gaps consume ring length, so the four
pieces are scaled down to leave room; without that the last piece is
pushed past the end of the path and silently clipped.

Callouts: white 28% leaders at `stroke-width:4.5`. In the To group the
leaders are emitted **before** the rings so every ring paints over them,
and each aims at its ring's centre and stops `LEAD.in` beyond the outer
radius — measured from the centre, not along the leader, because the
label sits off to one side and a distance taken from there overshoots
into the hole. The shared `Calculation` label sits in the visible gap
between the two v2 rings (`gapMid`), not midway between their centres,
because those differ.

| Callout | Where | Value |
|---------|-------|-------|
| Debug code | 225° on the From ring, `--av` | `9.7 ms · 64%` |
| Load | 270° on the From ring, `--md` | `1.2 ms · 8%` |
| Calculation | 315° on the From ring, `--knn` | `4.3 ms · 28%` |
| Calculation | `gapMid`, centred, `--knn` | `9.4 ms` |
| Imputed | below the v2 pair at `IMP_Y = 322`, `--imp`, right-aligned on `impMid` | four rows below |

The Imputed block sits **below** the two v2 rings, not in the gap between
them: four mono rows are far wider than the gap, so there they would sit
on top of both. Its leader runs from the imputation arc down to the top
of the header, so it meets the block rather than crossing it. Each row
reads as what a request at that null level actually costs — the imputed
slice plus the fixed calculation:

| Row | Text |
|-----|------|
| 1 | `0.5 ms @ 10% null · 10.0 ms Avg` |
| 2 | `0.8 ms @ 15% null · 10.2 ms Avg` |
| 3 | `1.0 ms @ 20% null · 10.5 ms Avg` |
| 4 | `5.1 ms @ 100% null · 14.6 ms Avg` |

Row text is generated (`${slice} ms @ ${pct}% null · ${withCalc} ms Avg`);
the table below is the rounded view.

**Table** — `table.ph-table.ph-figures.ph-figures-lg`, columns
Stage / From / To / Delta. `ph-figures-lg` steps up to `--fs-lead` with
`padding:7px 34px 7px 0` so the four columns read as four columns
rather than a left-clumped block with Delta stranded at the far edge.

| Row class | Stage | From | To | Delta |
|-----------|-------|------|----|-------|
| `ph-kpi-av` | Debug code | [cost.dev] | `·` (`ph-na`) | [cost.devDelta] |
| `ph-kpi-md` | Artifact loading | [cost.load] | `·` (`ph-na`) | [cost.loadDelta] |
| `ph-kpi-knn` | Calculation | [cost.calcOrig] | [cost.calcV2] | [cost.calcDelta] |
| — | Total time | [cost.totalOrig] | [cost.totalV2] | [cost.totalDelta] |
| `ph-muted` | Improvement | `·` | `·` | [cost.improvement] |

Row colours map the table to the rings without a legend
(`deck.html:407-416`, `679-683`): `ph-kpi-av`/`ph-kpi-knn` take their
method colour; `ph-kpi-md` takes `--ph-accent` at weight 600 because
artifact loading is the one stage the caching fix actually removes, and
it is the smaller of the two costs. `.ph-na` is a muted dot at 0.45
opacity — an absent value reads as "not applicable here", not as a minus.

**Foot** (`p.ph-foot.ph-foot-sm`): Median of 5 runs × 1000 calls, one at
a time, over the 201 examples published on `/docs`; costs priced by
subtraction. Figures include the half of the examples v1 rejects with
422.

`ph-foot-sm` needs the `.reveal` prefix: a bare `.ph-foot` scores
0,1,0 and loses to `.reveal p` at 0,1,1, so every footer renders at
body size despite declaring caption.

- Say: "Before, every call paid for debug code and reloading artifacts. Now the service loads once — 15.2 ms to 9.4 ms."

## S7 — Modernization base (`#s7-modernization`, `class="ph-caps ph-s7"`)

Layout: T-s7-split. `div.ph-s7` is
`grid-template-columns: minmax(0,0.62fr) minmax(0,2.38fr)`;
left `ol.ph-scr.ph-s7-chips`, right `div.ph-cols.ph-s7-panes`.

**Chip 01 and pane 01 carry `ph-is-base` and no `fragment` class: they
are the slide's resting state, so the slide opens on step 1 with no
click.** Reveal exposes no attribute to start a slide mid-fragment
(upstream #2560), so the base state is expressed as the *absence* of any
step fragment — `:not(:has(.ph-s7-pane.fragment.visible))` paints the
base chip and pane, `:has(...)` retires them. Steps 2-4 are the only
fragments, `data-fragment-index` 0-2.

| Step | Chip | Pane |
|------|------|------|
| 1 (resting, no click) | `1` Runtime | `table.ph-table` — see below |
| 2 | `2` Type hints | prose + `From`/`To` code listing |
| 3 | `3` Validation | two click-to-zoom captures |
| 4 | `4` Swagger | table + response listing |

Chips: `justify-content:center` (the column is treated like the cover, so
the slide reads as a starting point rather than a list hanging from the
top), `flex-wrap:nowrap`, `align-items:baseline`. `.ph-num` is
`--fs-h1` here (digits dominate, label supports — the cover's one-large /
one-small hierarchy) against the shared `.ph-num` at `--fs-h3`. Chips
stay visible through every step (reveal's `.fragment` opacity is
overridden). Selection is carried by fill `rgba(165,254,202,0.12)` and
`border-left-color:var(--ph-mint)`, **not** by recolouring the title — a
chip that changes colour on selection reads as a different kind of item.
Past the base step chip 01 keeps its row but drops back to the resting
fill, so the column stays a stable index.

Panes: all at `grid-area:1 / 1` with `min-height:0`; only
`.current-fragment` is painted (`opacity:1;visibility:visible`), because
reveal keeps `.visible` on past fragments. The base pane also carries the
current-fragment border and glow while it rests. `min-height:0` lets a
pane shrink to the row it is given instead of being stretched by its
tallest sibling — without it chip 03's tall capture pushed the other
three past the slide.

**Runtime table** — three equal columns (`33.333%`, so the whitespace is
the same everywhere), `max-width:62ch`, `margin-inline:auto` so it sits
centred in the pane both ways. Base pane `width:100%;max-width:788px`.
The From and To column heads take `--ph-accent`.

| Library | From | To |
|---------|------|-----|
| docker image | 3.10 slim | 3.14 slim |
| fastapi | 0.85.1 | 0.141.1 |
| httpx | ~~0.24.0~~ | - |
| httpx2 | - | 2.13.1 |
| hypothesis | 6.82.0 | 6.168.3 |
| matplotlib | 6.82.0 | 3.11.2 |
| numpy | 1.23.4 | 2.5.3 |
| pandas | 1.5.1 | 3.0.6 |
| pip | ~~23.0.1~~ | - |
| uv | - | 0.12.21 |
| pydantic | 1.10.2 | 2.13.5 |
| pytest | 7.4.0 | 9.1.1 |
| pytest-cov | 4.1.0 | 7.1.0 |
| python | 3.10 | 3.14 |
| scikit-learn | 1.1.2 | 1.9.1 |
| uvicorn | 0.19 | 0.54.0 |

`httpx` and `pip` are dropped: row `ph-muted`, `th`/`td` both
`ph-strike`.

**Pane 2 — Type hints.** `h3` Type hints, then prose: A type hint is a
label that says what a piece of data should be. It is a note, not a rule,
so Python runs the code either way. A type checker reads the note and
catches a wrong value before the code runs. FastAPI reads the same note to
write the API documentation, so the docs always match what the service
actually does.

| Block | Content |
|-------|---------|
| `h4` From | `def predict(home_features):` |
| `h4` To | `class HomeFeaturesV2(BaseModel):` / `    bedrooms: int \| None = Field(default=None, ge=0)` / `    # ... six more nullable fields ...` / `    zipcode: str = Field(pattern=r"^\d{5}$")` / (blank) (blank) / `class PredictionResponse(BaseModel):` / `    predicted_price: float = Field(examples=[394708.0])` / (blank) (blank) / `def predict_v2(` / `    home_features: HomeFeaturesV2,` / `    request: Request,` / `) -> PredictionResponse:` |

The six middle fields are elided to fit the pane — the pane holds ~13
code lines and the full class is 8 fields.

**Pane 3 — Validation.** `div.ph-s7-validation > h3` plus
`div.ph-shots` of two `figure.ph-shot`: `h4` From with
`div.ph-validation.from`, `h4` To with `div.ph-validation.to`.
Both `h4`s take `--ph-accent` (`:first-child`/`:last-child`) — they
label two snapshots of the same schema, not two competing approaches the
way S4's three colours do.

The captures are `background-image` divs (data-URI PNGs in the CSS),
`aspect-ratio:419/750`, `height:100%;width:auto`,
`background-size:contain`, `background-position:center`. Both boxes share
the taller capture's ratio, so they come out the same size at one scale;
the portrait To fills the box and `center` only moves the landscape From.
Each is `cursor:zoom-in`, `tabIndex=0`, `role="button"`,
`aria-label="Enlarge {label} screenshot"`, and opens the zoom described
under Reveal config + JS. The dialog is on `<body>` outside `.reveal`, so
it names `var(--ph-font)` itself rather than falling back to the browser
default.

**Pane 4 — Swagger.** `h3` Swagger plus
`table.ph-table`, columns Response / From — `/predict` / To — `/predict/v2`:

| Response | From | To |
|----------|------|-----|
| 200 schema | unnamed object, any number of keys | named model `PredictionResponse` |
| Declared fields | none | `predicted_price`: number, required |
| Example | none | 394708.0 |
| Errors | 422 | 404, 500 → `ErrorDetail` |

Then `pre.ph-code` with `{"predicted_price": 394708.0}`.

Code listings use `pre.ph-code` with `code.language-*` (inset navy fill,
mint-tinted frame, `--fs-body`, `white-space:pre` so source line breaks
hold). `pre.ph-code` margin is `0 0 var(--sp-sm)`; the last listing in a
pane relies on that. No `data-markdown` anywhere: that attribute only
works on a `<section>`, and a nested section becomes a vertical slide,
which would break the chip/pane fragment steps.

- Say (one line each): "Locked installs. Annotated defs. Honest schema."
- Sources: `src/api/endpoints_v2.py` (`HomeFeaturesV2`, `predict_v2`)
  and `src/api/endpoints.py` (`HomeFeatures`, `predict`); `uv.lock` +
  PyPI for the To column.

## S8 — Appendix demo runbook (`#s8-appendix`, `data-visibility="hidden"`)

Layout: T-appendix-hidden. Never presented. Five plain `<li>` in a bare
`ol`, mirroring checklist items 1-5; item 6 is talk-track only, no slide.

| Step | Slide text |
|------|------------|
| 1 | Blank fields score; same payload to the old endpoint fails. |
| 2 | Bad area code returns a named plain-words reply. |
| 3 | Load-once versus per-request; cite harness numbers, offer live rerun. |
| 4 | Health check passes when ready, fails clearly when not. |
| 5 | Docs show typed responses with examples. |

1. Missing data: POST `/predict/v2` with `bathrooms: null`,
   `sqft_lot: null` → 200 + `predicted_price`; same payload to v1 fails.
2. Unknown zip: `"zipcode": "00000"` → 404 naming the zip.
   Trace: `src/api/shared.py` (404 `Unknown zipcode`); tests
   `test/unit/test_api_unit.py`.
3. Speed: lifespan load-once vs v1 per-request; cite `DECK_METRICS`
   cost block, offer a live re-run via
   `test/benchmark/benchmake.py`.
4. Readiness: `/health/v2` 200 vs 500 when artifacts missing.
5. Contracts: `/docs` shows typed responses with examples.
6. AI usage (`CANDIDATE_PROJECT.md:163-170`): tool used, context technique,
   validation via unit/integration suites + live probes.