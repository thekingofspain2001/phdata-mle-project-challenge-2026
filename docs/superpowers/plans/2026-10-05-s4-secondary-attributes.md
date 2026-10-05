# S4 Secondary Attributes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `presentation/deck.html`'s S4 houses diagram so the four staged calculations show *which* attribute each step reads — one column for Average and Medium, three columns to find and one to fill for Nearest Neighbor and Scaled Nearest Neighbor.

**Architecture:** One inline SVG (`#houses-svg`) grows from a single row of square-footage labels to a four-row attribute grid, one row per attribute, twelve values per row, keyed to the same twelve house x-positions. The four rows are four of the seven columns the service actually ships (`src/api/shared.py:52`): `sqft_living` is the one that came back blank, and `sqft_lot` / `bedrooms` / `bathrooms` are the three that choose the neighbours. Per-stage CSS on the existing `section[data-s4]:has(.ph-s4-go:nth-of-type(N).visible):not(:has(.ph-s4-go:nth-of-type(N+1).visible))` range selectors drives everything: which attribute rows light, which house values inside those rows light, which dashed box is drawn, which marker floats. No new JavaScript, no new files, no slide other than S4 changes.

**Tech Stack:** Static HTML, one `<style>` block, inline SVG, reveal.js 4 fragments, CSS `:has()`. No build step.

**Spec:** This document. It is self-contained; the executing agent needs nothing but `presentation/deck.html`, `presentation/deck-script.md` and this file.

## Global Constraints

- Only two files are touched: `presentation/deck.html` and `presentation/deck-script.md`. Nothing under `src/` is read or written.
- No new `<script>` block, no new global, no new dependency. S4 staging stays pure CSS driven by reveal's `.visible` class.
- **Reveal only ever ADDS `.visible`; it never removes it while the slide is showing.** At stage N, drivers 1..N are all visible. Every stage-scoped rule therefore carries the range guard `:has(go N .visible):not(:has(go N+1 .visible))`, exactly as the current deck does. Stage 7 is the one exception and uses bare `:has(go7 .visible)`, which is unique to stage 7 because driver 7 exists nowhere else. Dropping the `:not()` guard makes every rule from every earlier stage fire at once: the seven subtitles stack on top of each other in the one `.ph-subs` grid cell and the boxes and markers accumulate.
- Because the guards make stages mutually exclusive, **each stage's rule block states that stage's complete state** — every row lit, every row dimmed. Do not write "light these rows" and rely on a later stage to undo it. Stage exclusivity plus a complete state per stage means no specificity contest and no leftover state.
- Colour comes from `var(--av)` / `var(--md)` / `var(--knn)` / `var(--snn)` only. No new hex colours. The unlit rest state is `#BCCCD4` (which is `--ph-mist`).
- Every house glyph, `translate(x,210)` and `scale(s)` in the S4 SVG stays byte-identical. The twelve `x` and twelve `scale` values are load-bearing: the intra-group and inter-group gap arithmetic in the source comments is expressed against them.
- `#hs` in `<defs>` (`deck.html:1968-1972`) is unchanged, as are the four `arr-*` arrow markers (`deck.html:1973-1993`), the baseline `<line>` (`deck.html:2031`), and `color="#BCCCD4"` on `#houses-svg` — `#hs` strokes with `currentColor`, so `stroke` alone would leave every house grey. Do not "tidy" any of these.
- Marker geometry is pinned: the base `transform` encodes the marker's own value, and the name/value/leader coordinates (`y=-66`, `y=30`, `y=44`) are shared across all four. Changing any of them breaks value sizing and the shared baseline. See the CSS comment at `deck.html:1352-1355`.
- Four result numbers exist on this slide. Three do not change: 2225, 1885, 2802. One does: **3468 → 3470**. Every occurrence changes, including ones in CSS comments and in `deck-script.md` prose. The complete list is in Task 1 Step 5.
- CI (`.github/workflows/ci.yml`) runs pytest, ruff and pyright over Python only. There is no HTML, CSS or markdown formatter or linter in this repo, so there is nothing to run after editing these two files. Verification is Task 7.
- `deck-script.md` §S4 is at lines 442-585. Its fragment, box and marker **counts are currently accurate** (5 fragments, four boxes, four markers). What is stale: the `3468` occurrences, the c-calc SVG geometry prose at 554-557 and the panel table at 563-568, the stage tables at 493-534, the summary bullets at 549-552 and the speaker notes at 577-581. Task 8 rewrites exactly those.

## Review Focus

Five ways a person using this slide can reasonably expect behaviour that no static check will catch:

1. **A stage where the wrong thing is lit** — Average lighting the `sqft_lot` row, or a neighbour stage lighting all twelve houses instead of five, or stage 7 still showing twenty lit values from stage 5. Pinned by Task 5 Step 3.
2. **A value column that collides with its neighbour.** Group A's houses are 44u apart and a four-digit `sqft_lot` at 13px is ~31u wide, so rows are tight but must not touch. Pinned by Task 3 Step 4.
3. **A row label clipped by the viewBox edge, or lit at a fraction of a lit value.** The labels live in a new left gutter that does not exist today. Group opacity multiplies with child opacity in SVG, so a rest opacity on both the `<g>` and the `<text>` silently halves every label. Pinned by Task 3 Step 4 and Task 6 Step 1.
4. **A dashed box that does not enclose exactly the houses it claims.** The `#hs` glyph has half-width 25, so the box bounds are not the house centre positions. The existing `bx-knn` is off by one house in each direction — see Task 4 Step 1. Pinned by Task 4 Step 1's assertion.
5. **The layout overflowing the slide.** The SVG grows from a 340-unit to a 380-unit viewBox, and `#houses-svg` is capped at `max-height:380px`, so the growth is close to the cap. Pinned by Task 2 Step 4.

---

## Design Decisions

These were chosen deliberately. Do not "improve" them without re-deriving the numbers.

**D1 — Seven stages, not five.** Average and Medium each take one stage, because each is a single step. Nearest Neighbor and Scaled Nearest Neighbor each take **two**, because the slide's own panels already claim `Steps → 2 steps` (`deck.html:2233-2234` and `2274-2275`) and nothing on screen shows those two steps. Stage order:

| Stage | driver N | Subtitle | Box | Marker | Attribute rows lit |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | Average Value | `bx-avg` | `mk-avg` | `sqft_living` only, 12 houses |
| 2 | 2 | Medium value | `bx-med` | `mk-med` | `sqft_living` only, houses 6-7 |
| 3 | 3 | Nearest Neighbor — find the 5 closest | `bx-knn-pick` | none | `sqft_lot`, `bedrooms`, `bathrooms`, 5 houses |
| 4 | 4 | Nearest Neighbor — read their size | `bx-knn` | `mk-knn` | `sqft_living` only, 5 houses |
| 5 | 5 | Scaled Nearest Neighbor — find the 5 closest | `bx-snn-pick` | none | `sqft_lot`, `bedrooms`, `bathrooms`, 5 houses |
| 6 | 6 | Scaled Nearest Neighbor — read and weight | `bx-snn` | `mk-snn` | `sqft_living` only, 5 houses |
| 7 | 7 | Summary: similar homes win | none | all four | none |

**D2 — Six dashed boxes, not four.** The vertical extent of the box is the second half of the new encoding: a box that stops above the `sqft_lot` row says "this method reads one attribute", a box that reaches past the `bathrooms` row says "this method reads three". Boxes are never animated — each stage switches between two static rectangles, matching how `.mk` already switches.

| Id | x | y | width | height | right edge | bottom | Colour | Stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `bx-avg` | 32 | 116 | 1164 | 122 | 1196 | 238 | `var(--av)` | 1 |
| `bx-med` | 324 | 116 | 260 | 122 | 584 | 238 | `var(--md)` | 2 |
| `bx-knn-pick` | 510 | 116 | 596 | 180 | 1106 | 296 | `var(--knn)` | 3 |
| `bx-knn` | 510 | 116 | 596 | 122 | 1106 | 238 | `var(--knn)` | 4 |
| `bx-snn-pick` | 510 | 116 | 596 | 180 | 1106 | 296 | `var(--snn)` | 5 |
| `bx-snn` | 510 | 116 | 596 | 122 | 1106 | 238 | `var(--snn)` | 6 |

All at `y=116`, `stroke-dasharray="8 5"`, `stroke-width="2"`.

**Why the box bounds are not the house centres.** `#hs` is drawn from `x=-25` to `x=25` (`deck.html:1969-1971`), so a house at `x` with `scale s` spans `x - 25s` to `x + 25s`. Twelve houses, and their spans:

| House | centre | scale | left | right |
| --- | --- | --- | --- | --- |
| 1 | 54 | 0.76 | 35.0 | 73.0 |
| 2 | 98 | 0.80 | 78.0 | 118.0 |
| 3 | 142 | 0.84 | 121.0 | 163.0 |
| 4 | 241 | 0.95 | 217.2 | 264.8 |
| 5 | 297 | 1.00 | 272.0 | 322.0 |
| 6 | 353 | 1.05 | 326.8 | 379.2 |
| 7 | 551 | 1.1875 | 521.3 | 580.7 |
| 8 | 619 | 1.25 | 587.8 | 650.2 |
| 9 | 687 | 1.3125 | 654.2 | 719.8 |
| 10 | 984 | 1.484 | 946.9 | 1021.1 |
| 11 | 1066 | 1.5625 | 1026.9 | 1105.1 |
| 12 | 1148 | 1.6406 | 1107.0 | 1189.0 |

Each box above was chosen so it encloses exactly the houses D1 assigns to its stage. `bx-med` (324-584) encloses 6 and 7. `bx-avg` (32-1196) encloses all twelve: its left edge at 32 clears the row labels, which end at x=30, and clears house 1's left tip at 35; its right edge at 1196 clears house 12's right tip at 1189.

**The existing `bx-knn` is wrong and this plan fixes it.** `deck.html:2074` declares `x="584" width="611"`, i.e. 584-1195. That encloses houses 8, 9, 10, 11 and **12** — it includes the largest house on the slide, which is the one this design deliberately makes *not* a neighbour, and it excludes house 7, which is a neighbour. The plan's replacement (510-1106) encloses exactly 7, 8, 9, 10, 11.

**A tight spot to know about, not to fight.** House 11's right tip is 1105.1 and house 12's left tip is 1107.0 — a gap of 1.9 units, the tightest in the layout. `bx-knn`'s right edge at 1106 sits inside that gap, so its dashed stroke visually touches house 12's roof outline. That is inherent to the existing spacing, which is a load-bearing constraint. It is acceptable because the **attribute lighting, not the box, is what says which houses are read**: house 12's `sqft_lot` / `bedrooms` / `bathrooms` values never light at any stage — its distance of 55 puts it sixth. Do not move the houses to widen the gap.

**D3 — Two channels, never mixed.** Horizontal box extent answers *which houses*. Lit attribute values answer *which attributes*. No other visual carries either meaning. The house glyphs themselves stay static mist — `deck-script.md:450-452` records that as deliberate.

**D4 — Values are constructed so the arithmetic holds.** The twelve houses are given `sqft_lot`, `bedrooms` and `bathrooms` values chosen so the five houses nearest to a notional subject on all three attributes are exactly the five the deck already uses (`.h-nn`: houses 7-11). Full derivation in Task 1. The column names are the ones the service ships (`src/api/shared.py:52`) — the slide must not show fields the API does not have. The values themselves are constructed, not sampled from the dataset; they need to be true *on the slide*, and Task 8 records the construction.

**Why these three of the seven.** The shipped columns are `bedrooms`, `bathrooms`, `sqft_living`, `sqft_lot`, `floors`, `sqft_above`, `sqft_basement`. Three are ruled out: `sqft_living` is the column that comes *out*, `sqft_above` and `sqft_basement` are derived from it (a one-storey house has `sqft_above == sqft_living` and often `sqft_basement == 0`), so using them to find neighbours would contradict the diagram, which dims that row during the find. Of the rest, `bedrooms` + `bathrooms` + `floors` are all small discrete counts: with twelve houses and three coarse columns the ranking forces ties, and the closest house scores **0**, which makes the `1/d` weight undefined. `sqft_lot` supplies the resolution and is genuinely independent of living area, so the find set is `sqft_lot`, `bedrooms`, `bathrooms`.

---

### Reference data (Tasks 3, 6 and 8 copy this table verbatim)

The subject — the listing being priced, its living area blank — is **5 bedrooms, 3 bathrooms, a 9000 sq ft lot**.

| House | x | scale | sqft_living | sqft_lot | bedrooms | bathrooms | distance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 54 | 0.76 | 1235 | 4600 | 2 | 1 | 95 |
| 2 | 98 | 0.80 | 1300 | 4900 | 2 | 1.5 | 88 |
| 3 | 142 | 0.84 | 1365 | 5300 | 2 | 1.5 | 80 |
| 4 | 241 | 0.95 | 1520 | 5600 | 3 | 1.5 | 73 |
| 5 | 297 | 1.00 | 1600 | 6200 | 3 | 1.5 | 61 |
| 6 | 353 | 1.05 | 1680 | 5900 | 3 | 2 | 66 |
| 7 | 551 | 1.1875 | 2090 | 7600 | 4 | 2.5 | 30 |
| 8 | 619 | 1.25 | 2200 | 8000 | 4 | 2.5 | 22 |
| 9 | 687 | 1.3125 | 2310 | 8400 | 5 | 3 | 12 |
| 10 | 984 | 1.484 | 3610 | 8800 | 5 | 3 | 4 |
| 11 | 1066 | 1.5625 | 3800 | 9100 | 5 | 3 | 2 |
| 12 | 1148 | 1.6406 | 3990 | 6400 | 6 | 4 | 55 |

`distance = |sqft_lot - 9000| / 50 + |bedrooms - 5| + 2 × |bathrooms - 3|`

The `/50` normalises a four-digit lot into the same range as the two counts. The `2 ×` on bathrooms is because bathrooms move in half-steps, so one full mismatch is worth two bedroom mismatches.

Five nearest, ascending: house 11 (2), house 10 (4), house 9 (12), house 8 (22), house 7 (30) — the same five `.h-nn` already marks and the same five the panel strips light. Distance is monotonic in size, so the slide can honestly say the bigger house is the closer one. Sixth is house 12 (55): **the largest house on the slide is deliberately not a neighbour**, and the gap from fifth to sixth is 83%, so the cut is not marginal. House 12 is the largest house but sits on a 6400 sq ft lot with 6 bedrooms and 4 bathrooms — a different kind of house, not a closer one.

Distances are already integers as written: **2, 4, 12, 22, 30**. Weights `1/2, 1/4, 1/12, 1/22, 1/30`.

Marker positions move so both neighbour markers sit inside the corrected box. `mk-knn` moves 952 → **760**, `mk-snn` moves 1150 → **940**; both stay within 510-1106, and both clear the other three markers when all four show at stage 7.

---

## File Structure

| File | Change |
| --- | --- |
| `presentation/deck.html` | CSS block (`:has()` stage selectors, attribute-row rules), S4 `<svg>` markup, S4 `<dl>` copy, S4 pick-SVG copy, driver spans |
| `presentation/deck-script.md` | §S4 (lines 442-585) rewritten to match the new slide |

---

### Task 1: Lock the numbers before touching markup

**Files:**

- Modify: none

**Interfaces:**

- Consumes: nothing
- Produces: the verified value table and verified weighted result that Tasks 3, 6 and 8 copy from.

No code here. This task exists so the arithmetic is proven before it is typed into markup, and so a later task that "fixes" a number has to answer for it.

- [ ] **Step 1: Verify the distances and the ranking**

For each house compute `|sqft_lot - 9000| / 50 + |bedrooms - 5| + 2 × |bathrooms - 3|`. The first term is written as its `lot/50` contribution:

``` text
house  1: 88 + 3 + 4 = 95      house  7: 28 + 1 + 1 = 30
house  2: 82 + 3 + 3 = 88      house  8: 20 + 1 + 1 = 22
house  3: 74 + 3 + 3 = 80      house  9: 12 + 0 + 0 = 12
house  4: 68 + 2 + 3 = 73      house 10:  4 + 0 + 0 =  4
house  5: 56 + 2 + 3 = 61      house 11:  2 + 0 + 0 =  2
house  6: 62 + 2 + 2 = 66      house 12: 52 + 1 + 2 = 55
```

Ascending: 11 (2), 10 (4), 9 (12), 8 (22), 7 (30), 12 (55), 5 (61), 6 (66), 4 (73), 3 (80), 2 (88), 1 (95).

The five nearest are houses **7-11**, matching the existing `.h-nn` set. The gap between fifth (30) and sixth (55) is 83%, so the cut is not marginal. Two properties the slide leans on and that must survive any re-derivation: the five distances are **distinct** (no tie to break) and **monotonic in size** (2, 4, 12, 22, 30 against 3800, 3610, 2310, 2200, 2090), so "the bigger house is the closer one" is literally true here.

- [ ] **Step 2: Verify the three unchanged results**

``` text
average of all 12 = 26700 / 12 = 2225
median of 12      = (1680 + 2090) / 2 = 1885
plain mean of the five = (3800 + 3610 + 2310 + 2200 + 2090) / 5 = 14010 / 5 = 2802
```

- [ ] **Step 3: Verify the one changed result**

Weights over the five, in the order the panel prints them (3800, 3610, 2310, 2200, 2090) with weights `1/2, 1/4, 1/12, 1/22, 1/30`. Common denominator 660:

``` text
numerator   = 3800/2 + 3610/4 + 2310/12 + 2200/22 + 2090/30
denominator = 1/2 + 1/4 + 1/12 + 1/22 + 1/30

3800/2    = 1254000 / 660
3610/4    =  595650 / 660
2310/12   =  127050 / 660
2200/22   =   66000 / 660
2090/30   =   45940 / 660
          = 2088640 / 660          (1254000 + 595650 + 127050 + 66000 + 45940)

1/2 = 330/660,  1/4 = 165/660,  1/12 = 55/660,
1/22 = 30/660, 1/30 = 22/660   ->  602/660

value = 2088640 / 602 = 3469.57  ->  3470
```

The sum is **2088640**, not 2086840 — check your digit transposition before trusting the line. 3470 is greater than the plain average 2802 (the closest house dominates) and less than 3800 (it is a weighted mean, not a copy of the nearest).

- [ ] **Step 4: Verify the claim the new marker comments will make**

Of the five neighbour sizes, how many exceed the city average of 2225?

``` text
3800 > 2225, 3610 > 2225, 2310 > 2225   -> three above
2200 < 2225, 2090 < 2225               -> two below
```

**Three of the five.** The existing comment at `deck.html:2106-2108` says "four of the five are smaller than the mean", which is wrong, and the deck's 2802 is *above* 2225, not below. The replacement comment in Task 6 Step 2 says "three of the five are larger than 2225" — correct. Do not reintroduce a count you have not just checked.

- [ ] **Step 5: Enumerate every `3468` before changing any of them**

Run: `grep -n 3468 presentation/deck.html presentation/deck-script.md`

Expected — these ten lines (eleven occurrences: line 571 carries two) and no others. Count grep lines against the ten rows below, not against the occurrence total.

| File | Line | What it is | Task that changes it |
| --- | --- | --- | --- |
| `deck.html` | 1353 | CSS comment above the KNN marker rules | 6 Step 2 |
| `deck.html` | 2132 | `#mk-snn` value text | 6 |
| `deck.html` | 2288 | `ph-is-snn` pick-SVG `aria-label` | 6 |
| `deck.html` | 2291 | `ph-is-snn` pick-SVG `= 3468` result | 6 |
| `deck.html` | 2323 | `.ph-panel-nums` summary line | 6 |
| `deck-script.md` | 485 | marker table, `NN weighted` row | 8 |
| `deck-script.md` | 488 | marker prose, "2802 equal-weight, 3468 weighted" | 8 |
| `deck-script.md` | 568 | c-calc panel table, `Scaled NN` result | 8 |
| `deck-script.md` | 571 | prose, "weighted 1/d = **3468**" | 8 |
| `deck-script.md` | 575 | summary line | 8 |

If your grep returns a hit not in this table, stop and report it before editing.

---

### Task 2: Grow the SVG viewBox and open the left label gutter

**Files:**

- Modify: `presentation/deck.html` (the `#houses-svg` opening tag, line 1965)

**Interfaces:**

- Consumes: the twelve `x` values from the reference table.
- Produces: a viewBox with left edge `-30` and bottom `300`, giving room for four row labels and four attribute rows. Every later task assumes it.

- [ ] **Step 1: Replace the `viewBox` and `aria-label` on `#houses-svg`**

Find:

```html
<svg id="houses-svg" class="houses-svg" viewBox="15 -80 1195 340" fill="none" color="#BCCCD4" role="img"
  aria-label="Twelve houses in four groups of three, sorted smallest to largest">
```

Replace with:

```html
<svg id="houses-svg" class="houses-svg" viewBox="-30 -80 1240 380" fill="none" color="#BCCCD4" role="img"
  aria-label="Twelve houses in four groups of three, sorted smallest to largest. Under each house, four attribute values in four rows: square feet of living area, square feet of lot, bedrooms, and bathrooms.">
```

The left edge moves 15 → −30 to open a gutter between −30 and 35 (house 1's left tip). The width moves 1195 → 1240 so the right edge stays at 1210, unchanged. The height moves 340 → 380 so the bottom edge is at 300, below the `bathrooms` row.

Do not change `fill`, `color`, `class` or `role`.

- [ ] **Step 2: Confirm the diagram still fits**

The slide is 1270 wide with `--pad-x: 60px`, so the SVG element box is 1150 × 380 (`#houses-svg` is `width:100%; height:100%; max-height:380px`, `deck.html:1222-1227`). `1240 / 380 = 3.26` is wider than `1150 / 380 = 3.03`, so width binds: rendered content height is `380 × (1150 / 1240) = 352px`, inside the 380px cap. The drawing shrinks from a 0.962 scale to 0.927 — about 3.6% — which is the intended cost of the label gutter.

- [ ] **Step 3: Look at it**

Open `presentation/deck.html`, jump to slide 4 (`Reveal.slide(3, 0)`). Confirm: the twelve houses are unchanged in size and position; the baseline still starts at the first house; nothing is clipped at any edge.

- [ ] **Step 4: Assert the fit without measuring the wrong box**

`getBoundingClientRect()` on an `<svg>` returns its **CSS box**, not the letterboxed content inside it, so it reads 380 — that is correct and expected, not a failure. Assert the fitted content scale instead:

```js
(() => {
  const svg = document.getElementById('houses-svg');
  const r = svg.getBoundingClientRect();
  const sec = document.getElementById('s4-approaches').getBoundingClientRect();
  const scale = Math.min(r.width / 1240, r.height / 380);
  return {
    boxH: r.height,
    boxW: r.width,
    scale: +scale.toFixed(3),
    contentH: Math.round(380 * scale),
    withinSlide: r.bottom <= sec.bottom + 0.5,
  };
})()
```

Expected: `boxH: 380`, `scale: 0.927`, `contentH: 352`, `withinSlide: true`.

---

### Task 3: Replace the square-footage label row with a four-row attribute grid

**Files:**

- Modify: `presentation/deck.html` (S4 SVG markup — the block of twelve `<text x=".." y="232">` elements, lines 2032-2068)

**Interfaces:**

- Consumes: the viewBox from Task 2.
- Produces: the class vocabulary every later CSS rule keys off —
  - `.ar-lab` on the label group; one `.al` per row, carrying `.al-living` / `.al-lot` / `.al-bed` / `.al-bath`.
  - `.ar-row` on each row group; one per attribute, carrying `.ar-living` / `.ar-lot` / `.ar-bed` / `.ar-bath`.
  - `.v` on each of the 48 value `<text>` elements, plus `.h-mid` on houses 6 and 7 (x 353 and x 551) and `.h-nn` on houses 7-11 (x 551, 619, 687, 984, 1066).

**House 7 (x=551) carries both `.h-mid` and `.h-nn`.** That is correct: it is the upper of the two middle houses and also the smallest of the five neighbours. Every other house carries at most one of the two.

- [ ] **Step 1: Delete the existing twelve-label block**

Remove exactly this block — the comment `<!-- House size data (sqft, proportional to scale) -->` through the closing `</text>` of the `3990` label — and nothing else. The baseline `<line>` above it stays.

- [ ] **Step 2: Add the row-label group**

Insert immediately after that baseline `<line>`, before the dashed-box block. **There is no `opacity` attribute on the `<g>`** — SVG group opacity multiplies with child opacity, so a rest opacity here would silently halve every label and cap a lit label at half brightness. Task 5 owns the rest state.

```html
<!-- Attribute rows: one line per attribute, one value per house, twelve values
     per row. Which rows light, and which values inside them, is stage-driven
     CSS - see the .ar-living / .ar-lot / .ar-bed / .ar-bath rules. -->
<g class="ar-lab" font-size="11" fill="#BCCCD4" text-anchor="end">
  <text class="al al-living" x="30" y="235">sqft_living</text>
  <text class="al al-lot" x="30" y="254">sqft_lot</text>
  <text class="al al-bed" x="30" y="273">bedrooms</text>
  <text class="al al-bath" x="30" y="292">bathrooms</text>
</g>
```

Labels sit 3 units below their row's value baseline so an 11px label optically centres against a 14px value. All four fit in the −30..35 gutter right-anchored at x=30, which gives 60u of width. Measured at 11px: `sqft_living` 52.6u (starts at −22.6), `bathrooms` 55.6u (starts at −25.6), `bedrooms` 52.4u, `sqft_lot` 38.7u. The widest is `bathrooms` at 55.6u, leaving 4.4u of margin — the real column names are longer than the invented ones were, so this is the number to re-measure if a label is ever shortened.

- [ ] **Step 3: Add the four value rows**

Insert after the label group, before the dashed-box block. Note the `h-mid` / `h-nn` assignment — this is the step where an error lights the wrong values at stage 2.

```html
<g class="ar-row ar-living" font-size="14" fill="#BCCCD4" text-anchor="middle">
  <text class="v" x="54" y="232">1235</text>
  <text class="v" x="98" y="232">1300</text>
  <text class="v" x="142" y="232">1365</text>
  <text class="v" x="241" y="232">1520</text>
  <text class="v" x="297" y="232">1600</text>
  <text class="v h-mid" x="353" y="232">1680</text>
  <text class="v h-mid h-nn" x="551" y="232">2090</text>
  <text class="v h-nn" x="619" y="232">2200</text>
  <text class="v h-nn" x="687" y="232">2310</text>
  <text class="v h-nn" x="984" y="232">3610</text>
  <text class="v h-nn" x="1066" y="232">3800</text>
  <text class="v" x="1148" y="232">3990</text>
</g>
<g class="ar-row ar-lot" font-size="13" fill="#BCCCD4" text-anchor="middle">
  <text class="v" x="54" y="251">4600</text>
  <text class="v" x="98" y="251">4900</text>
  <text class="v" x="142" y="251">5300</text>
  <text class="v" x="241" y="251">5600</text>
  <text class="v" x="297" y="251">6200</text>
  <text class="v" x="353" y="251">5900</text>
  <text class="v h-nn" x="551" y="251">7600</text>
  <text class="v h-nn" x="619" y="251">8000</text>
  <text class="v h-nn" x="687" y="251">8400</text>
  <text class="v h-nn" x="984" y="251">8800</text>
  <text class="v h-nn" x="1066" y="251">9100</text>
  <text class="v" x="1148" y="251">6400</text>
</g>
<g class="ar-row ar-bed" font-size="13" fill="#BCCCD4" text-anchor="middle">
  <text class="v" x="54" y="270">2</text>
  <text class="v" x="98" y="270">2</text>
  <text class="v" x="142" y="270">2</text>
  <text class="v" x="241" y="270">3</text>
  <text class="v" x="297" y="270">3</text>
  <text class="v" x="353" y="270">3</text>
  <text class="v h-nn" x="551" y="270">4</text>
  <text class="v h-nn" x="619" y="270">4</text>
  <text class="v h-nn" x="687" y="270">5</text>
  <text class="v h-nn" x="984" y="270">5</text>
  <text class="v h-nn" x="1066" y="270">5</text>
  <text class="v" x="1148" y="270">6</text>
</g>
<g class="ar-row ar-bath" font-size="13" fill="#BCCCD4" text-anchor="middle">
  <text class="v" x="54" y="289">1</text>
  <text class="v" x="98" y="289">1.5</text>
  <text class="v" x="142" y="289">1.5</text>
  <text class="v" x="241" y="289">1.5</text>
  <text class="v" x="297" y="289">1.5</text>
  <text class="v" x="353" y="289">2</text>
  <text class="v h-nn" x="551" y="289">2.5</text>
  <text class="v h-nn" x="619" y="289">2.5</text>
  <text class="v h-nn" x="687" y="289">3</text>
  <text class="v h-nn" x="984" y="289">3</text>
  <text class="v h-nn" x="1066" y="289">3</text>
  <text class="v" x="1148" y="289">4</text>
</g>
```

`sqft_living` is 14px because it is the primary attribute; the other three are 13px. Row pitch is 19 units (232 / 251 / 270 / 289). `sqft_lot` is four digits at 13px — ~31u wide against Group A's 44u spacing — which is tight but clear, and is why the collision assertion below matters more here than for the original single-digit rows. The `bathrooms` row is the only one carrying a decimal point.

- [ ] **Step 4: Assert no collision, no clipping, and the right classes**

```js
(() => {
  const svg = document.getElementById('houses-svg');
  const vals = [...svg.querySelectorAll('.ar-row .v')];
  const boxes = vals.map(t => t.getBoundingClientRect());
  let collisions = 0;
  for (let i = 0; i < boxes.length; i++)
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) collisions++;
    }
  const labelsInside = [...svg.querySelectorAll('.ar-lab .al')]
    .every(t => { const b = t.getBBox(); return b.x >= -30 && b.x + b.width <= 35; });
  const hnnCount = s => vals.filter(t => t.closest('.ar-row').classList.contains(s) && t.classList.contains('h-nn')).length;
  return {
    values: vals.length,
    collisions,
    labelsInside,
    hnnPerRow: { living: hnnCount('ar-living'), lot: hnnCount('ar-lot'), bed: hnnCount('ar-bed'), bath: hnnCount('ar-bath') },
    hnnOnLiving: [...svg.querySelectorAll('.ar-living .v.h-nn')].map(t => t.getAttribute('x')),
    hmidOnLiving: [...svg.querySelectorAll('.ar-living .v.h-mid')].map(t => t.getAttribute('x')),
    labels: [...svg.querySelectorAll('.ar-lab .al')].map(t => [t.textContent, Math.round(t.getBBox().x * 10) / 10]),
  };
})()
```

Expected: `values: 48`, `collisions: 0`, `labelsInside: true`, `hnnPerRow: { living: 5, lot: 5, bed: 5, bath: 5 }`, `hnnOnLiving: ["551","619","687","984","1066"]`, `hmidOnLiving: ["353","551"]`, and the four label `x` starts all `>= -30` — measured −22.6 / −8.7 / −22.4 / −25.6 for `sqft_living`, `sqft_lot`, `bedrooms`, `bathrooms`.

If `collisions` is non-zero it is a row-pitch problem, not a width problem — 19 units against 13px text is generous. Fix the baseline pitch; do not shrink the text.

- [ ] **Step 5: Look at it**

Confirm the four rows read as four attributes of the same twelve houses, the left labels sit clear of the baseline's left end, and the picture is otherwise unchanged.

---

### Task 4: Correct the dashed boxes, move the two neighbour markers, and restage to seven stages

**Files:**

- Modify: `presentation/deck.html` — the dashed-box block (lines 2069-2077), the `#mk-knn` and `#mk-snn` groups (lines 2109-2135), the `s4-drivers` block (lines 2329-2335), the `.ph-subs` subtitle stack (lines 1955-1961), and the four stage-selector rule groups in `<style>` (`.ph-s4-sub` opacity at ~1287, `#mk-*` at ~1334, `#bx-*` at ~1345, `.ph-panel` at ~1385)

**Interfaces:**

- Consumes: Task 3's class vocabulary.
- Produces: seven drivers, seven subtitles, six boxes, four markers, five panels, each mapped to exactly one stage by D1.

- [ ] **Step 1: Replace the dashed-box block with the six boxes from D2**

The existing block is three rects plus a fourth; `bx-med`, `bx-knn` and `bx-snn` keep their ids but change geometry, `bx-avg` changes geometry, and two pick boxes are new.

```html
<!-- Input boxes: dashed. Horizontal extent = which houses the method reads.
     Vertical extent = which attributes it reads: height 122 stops between the
     sq ft row and the built row, height 180 reaches past the beds row. -->
<rect id="bx-avg" class="bx" x="32" y="116" width="1164" height="122" fill="none" stroke="var(--av)"
  stroke-width="2" stroke-dasharray="8 5" />
<rect id="bx-med" class="bx" x="324" y="116" width="260" height="122" fill="none" stroke="var(--md)"
  stroke-width="2" stroke-dasharray="8 5" />
<rect id="bx-knn-pick" class="bx" x="510" y="116" width="596" height="180" fill="none" stroke="var(--knn)"
  stroke-width="2" stroke-dasharray="8 5" />
<rect id="bx-knn" class="bx" x="510" y="116" width="596" height="122" fill="none" stroke="var(--knn)"
  stroke-width="2" stroke-dasharray="8 5" />
<rect id="bx-snn-pick" class="bx" x="510" y="116" width="596" height="180" fill="none" stroke="var(--snn)"
  stroke-width="2" stroke-dasharray="8 5" />
<rect id="bx-snn" class="bx" x="510" y="116" width="596" height="122" fill="none" stroke="var(--snn)"
  stroke-width="2" stroke-dasharray="8 5" />
```

Then assert each box encloses exactly the houses D1 claims, using the glyph half-width of 25:

```js
(() => {
  const svg = document.getElementById('houses-svg');
  const H = [...svg.querySelectorAll('.h')].map(g => {
    const t = g.getAttribute('transform').match(/translate\(([\d.]+),[\d.]+\) scale\(([\d.]+)\)/);
    const x = parseFloat(t[1]), s = parseFloat(t[2]);
    return { x, left: x - 25 * s, right: x + 25 * s };
  });
  const enclosed = id => {
    const b = svg.getElementById(id);
    const x0 = +b.getAttribute('x'), w = +b.getAttribute('width');
    return H.filter(h => h.left >= x0 && h.right <= x0 + w).map(h => h.x);
  };
  return {
    avg: enclosed('bx-avg'), med: enclosed('bx-med'),
    knn: enclosed('bx-knn'), knnPick: enclosed('bx-knn-pick'),
  };
})()
```

Expected: `avg: [54,98,142,241,297,353,551,619,687,984,1066,1148]`, `med: [353,551]`, `knn: [551,619,687,984,1066]`, `knnPick: [551,619,687,984,1066]`.

Note the corrected `bx-knn` no longer matches `deck-script.md`'s current claim, and does not enclose house 12 — which is the point.

- [ ] **Step 2: Move the two neighbour markers inside the corrected box**

In `#mk-knn`, change **952 → 760** in four places: the inner `translate(952,10)`, the name `<text x="952">`, the value `<text x="952">`, and the leader `<line x1="952" x2="952">`.

In `#mk-snn`, change **1150 → 940** in the same four places.

Change nothing else about either marker — the `scale`, the `y=-66` / `y=30` / `y=44` coordinates and the leader's y range all stay, per the Global Constraints.

Both new centres sit inside the corrected box (510-1106) and clear the other markers at stage 7: 452, 634, 760, 940.

- [ ] **Step 3: Add the two extra driver spans**

Replace the five-span `s4-drivers` block with seven identical spans:

```html
<div class="s4-drivers" aria-hidden="true">
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
  <span class="fragment ph-s4-go"></span>
</div>
```

- [ ] **Step 4: Replace the subtitle stack with seven**

```html
<div class="ph-subs" aria-live="off">
  <p class="ph-subtitle ph-s4-sub ph-is-av">Average Value</p>
  <p class="ph-subtitle ph-s4-sub ph-is-md">Medium value</p>
  <p class="ph-subtitle ph-s4-sub ph-is-knn">Nearest Neighbor &#8212; find the 5 closest</p>
  <p class="ph-subtitle ph-s4-sub ph-is-knn">Nearest Neighbor &#8212; read their size</p>
  <p class="ph-subtitle ph-s4-sub ph-is-snn">Scaled Nearest Neighbor &#8212; find the 5 closest</p>
  <p class="ph-subtitle ph-s4-sub ph-is-snn">Scaled Nearest Neighbor &#8212; read and weight</p>
  <p class="ph-subtitle ph-s4-sub ph-is-sum">Summary: similar homes win</p>
</div>
```

Two subtitles now share `ph-is-knn` and two share `ph-is-snn`, which is why Step 5 addresses them by `:nth-of-type` while colour stays on `.ph-is-*`.

Use the full names. `.reveal .ph-subtitle` is `white-space:nowrap; text-overflow:ellipsis` (`deck.html:1234-1241`) but the longest line is roughly 500px inside a 1150px header, so it will not ellipsise. Task 7 Step 3 asserts that.

- [ ] **Step 5: Replace the subtitle opacity rule — keep the range guard**

Find the rule that currently reads:

```css
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ph-s4-sub.ph-is-av,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ph-s4-sub.ph-is-md,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ph-s4-sub.ph-is-knn,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ph-s4-sub.ph-is-snn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible) .ph-s4-sub.ph-is-sum {
  opacity: 1;
}
```

Replace with:

```css
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ph-s4-sub:nth-of-type(1),
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ph-s4-sub:nth-of-type(2),
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ph-s4-sub:nth-of-type(3),
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ph-s4-sub:nth-of-type(4),
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ph-s4-sub:nth-of-type(5),
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ph-s4-sub:nth-of-type(6),
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) .ph-s4-sub:nth-of-type(7) {
  opacity: 1;
}
```

The `:not()` guard is load-bearing. Reveal only adds `.visible`, so at stage 4 drivers 1-4 are all visible; without the guard all four subtitle rules fire and the seven subtitles stack on top of each other in the one `.ph-subs` grid cell (`deck.html:1253-1255`). Stage 7 is the only unguarded rule, and is safe because driver 7 exists nowhere else.

- [ ] **Step 6: Replace the marker rule — keep the range guard**

Find the `#mk-avg … #mk-snn { opacity: 1 }` rule and replace it with:

```css
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) #mk-avg,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) #mk-med,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) #mk-knn,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) #mk-snn,
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) #mk-avg,
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) #mk-med,
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) #mk-knn,
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) #mk-snn {
  opacity: 1;
}
```

Stages 3 and 5 have no marker, which is the point: nothing has been computed yet.

- [ ] **Step 7: Replace the box rule — keep the range guard**

Find the `#bx-avg … #bx-snn { opacity: 1 }` rule and replace it with:

```css
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) #bx-avg,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) #bx-med,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) #bx-knn-pick,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) #bx-knn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) #bx-snn-pick,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) #bx-snn {
  opacity: 1;
}
```

No box at stage 7.

- [ ] **Step 8: Replace the panel rule — note the widened guard on `ph-is-snn`**

Panels map to *methods*, not stages: Nearest Neighbor's spans stages 3 and 4, Scaled NN's spans 5 and 6. A panel's guard therefore has to stop at the stage *after its last stage*, not the stage after its first.

Replace the `.ph-panel { display: flex }` rule with:

```css
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ph-panel.ph-is-av,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ph-panel.ph-is-md,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ph-panel.ph-is-knn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ph-panel.ph-is-snn,
section[data-s4]:has(.ph-s4-go:nth-of-type(7).visible) .ph-panel.ph-is-sum {
  display: flex;
}
```

`ph-is-snn` guards on driver **7**, not 6. Guarding on 6 would leave stage 6 with no panel at all — the earlier `ph-is-*` guards have all closed by then and `ph-is-sum` needs driver 7 — so the bottom half of the slide would render empty.

- [ ] **Step 9: Verify the stage map**

From a fresh load of slide 4, click once per stage and run:

```js
(() => {
  const sec = document.getElementById('s4-approaches');
  const vis = s => [...sec.querySelectorAll(s)].filter(e => {
    const cs = getComputedStyle(e);
    return cs.display !== 'none' && cs.opacity !== '0' && e.getBoundingClientRect().width > 0;
  });
  return {
    subs: vis('.ph-s4-sub').map(e => e.textContent.trim()),
    panel: vis('.ph-panel').map(e => (e.className.match(/ph-is-\w+/) || [])[0]),
    boxes: vis('.bx').map(e => e.id),
    markers: vis('.mk').map(e => e.id),
  };
})()
```

| clicks | subtitle | panel | boxes | markers |
| --- | --- | --- | --- | --- |
| 0 | — | — | — | — |
| 1 | Average Value | ph-is-av | bx-avg | mk-avg |
| 2 | Medium value | ph-is-md | bx-med | mk-med |
| 3 | Nearest Neighbor — find the 5 closest | ph-is-knn | bx-knn-pick | — |
| 4 | Nearest Neighbor — read their size | ph-is-knn | bx-knn | mk-knn |
| 5 | Scaled Nearest Neighbor — find the 5 closest | ph-is-snn | bx-snn-pick | — |
| 6 | Scaled Nearest Neighbor — read and weight | ph-is-snn | bx-snn | mk-snn |
| 7 | Summary: similar homes win | ph-is-sum | — | mk-avg, mk-med, mk-knn, mk-snn |

Exactly one subtitle, one panel and one box per stage; at most one marker. More than one anywhere means a guard is missing **— but only if you sample after the transition has settled.** `.mk`, `.bx` and `.ph-s4-sub` all fade over `--ph-t-slide` (1.2s), so reading computed style immediately after a click catches the outgoing and incoming element together and reports two of each. Wait 1.4s, or test `+cs.opacity > 0.5` rather than `cs.opacity !== '0'`.

---

### Task 5: Add the attribute-row lighting rules

**Files:**

- Modify: `presentation/deck.html` — `<style>`, immediately after the `.houses-svg .bx { opacity: 0 … }` rule

**Interfaces:**

- Consumes: Task 3's classes and Task 4's seven-stage guards.
- Produces: the rest state plus seven complete per-stage states. This is the whole visual encoding of "which attribute does this step read".

**Every stage block states the complete state** — every row explicitly lit or dimmed — rather than lighting some rows and relying on a later stage to undo it. The range guards make exactly one stage's rules match at any moment, so there is nothing to inherit and nothing to undo.

- [ ] **Step 1: Add the rest state and transition**

```css
/* Attribute rows: the rest state is the whole data set, everything present and
   legible, nothing claimed. The per-stage rules are the only things that light a
   value - a value that is not lit is a value the method did not read.

   The rest opacity lives here and nowhere else. Do not put opacity on the
   .ar-lab group: SVG group opacity multiplies with child opacity, which would
   halve every label and cap a lit label at half brightness. */
.houses-svg .v,
.houses-svg .al {
  transition:
    opacity var(--ph-t-fade) var(--ph-ease),
    fill var(--ph-t-fade) var(--ph-ease);
}

.houses-svg .v,
.houses-svg .al {
  opacity: 0.55;
}
```

`--ph-t-fade` is 0.18s, matching `.houses-svg .h`; markers and boxes fade on `--ph-t-slide` (1.2s). If the values visibly light before the box that frames them, drop `.v` / `.al` to `--ph-t-slide` too rather than introducing a second timing token.

- [ ] **Step 2: Add the seven complete stage states**

```css
/* Stage 1 - Average: one column, every house. */
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ar-living .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .al-living {
  fill: var(--av);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ar-lot .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ar-bed .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .ar-bath .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(1).visible):not(:has(.ph-s4-go:nth-of-type(2).visible)) .al-bath {
  opacity: 0.22;
}

/* Stage 2 - Medium: the same one column, only the two middle houses. */
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ar-living .v.h-mid,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .al-living {
  fill: var(--md);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ar-living .v:not(.h-mid),
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ar-lot .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ar-bed .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .ar-bath .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(2).visible):not(:has(.ph-s4-go:nth-of-type(3).visible)) .al-bath {
  opacity: 0.22;
}

/* Stage 3 - Nearest Neighbor, step 1: three columns decide which houses are
   close. All twelve are compared; the five that win are the only ones lit. */
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-lot .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-bed .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-bath .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .al-bath {
  fill: var(--knn);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-living .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-lot .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-bed .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .ar-bath .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(3).visible):not(:has(.ph-s4-go:nth-of-type(4).visible)) .al-living {
  opacity: 0.22;
}

/* Stage 4 - Nearest Neighbor, step 2: the three comparison columns go quiet and
   the one column that gets averaged comes up. */
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ar-living .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .al-living {
  fill: var(--knn);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ar-living .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ar-lot .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ar-bed .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .ar-bath .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(4).visible):not(:has(.ph-s4-go:nth-of-type(5).visible)) .al-bath {
  opacity: 0.22;
}

/* Stage 5 - Scaled NN, step 1: stage 3 again, in the scaled colour. */
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-lot .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-bed .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-bath .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .al-bath {
  fill: var(--snn);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-living .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-lot .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-bed .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .ar-bath .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(5).visible):not(:has(.ph-s4-go:nth-of-type(6).visible)) .al-living {
  opacity: 0.22;
}

/* Stage 6 - Scaled NN, step 2: stage 4 again, in the scaled colour. */
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ar-living .v.h-nn,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .al-living {
  fill: var(--snn);
  opacity: 1;
}

section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ar-living .v:not(.h-nn),
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ar-lot .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ar-bed .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .ar-bath .v,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .al-lot,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .al-bed,
section[data-s4]:has(.ph-s4-go:nth-of-type(6).visible):not(:has(.ph-s4-go:nth-of-type(7).visible)) .al-bath {
  opacity: 0.22;
}
```

**Stage 7 has no attribute rules at all.** With every other stage guarded, no stage rule matches at stage 7 and all 48 values fall back to the 0.55 rest opacity. Do not add a stage-7 rule for the rows.

**Dim groups must close every selector.** A selector left as `.ar-bed .v:not(.h-nn,` is silently invalid and drops the whole rule. Read each selector back before saving; the browser will not report the omission.

- [ ] **Step 3: Verify per stage that exactly the intended values are lit**

The three opacity states are 1 (lit), 0.22 (dimmed) and 0.55 (rest). Read the **three counts**, not just the lit list, so a value stranded at the rest opacity cannot masquerade as either. The lit threshold is 0.8: it separates 1 from both 0.55 and 0.22 with room to spare, so the check does not silently depend on where the rest opacity happens to sit.

```js
(() => {
  const svg = document.getElementById('houses-svg');
  const buckets = { lit: 0, rest: 0, dim: 0 };
  const lit = [];
  for (const t of svg.querySelectorAll('.v')) {
    const o = Number(getComputedStyle(t).opacity);
    if (o > 0.8) { buckets.lit++; lit.push(`${(t.closest('.ar-row').className.match(/ar-\w+/) || [])[0]}:${t.textContent.trim()}`); }
    else if (o > 0.4) buckets.rest++;
    else buckets.dim++;
  }
  const labelOps = [...svg.querySelectorAll('.al')].map(t => +getComputedStyle(t).opacity);
  return { ...buckets, total: buckets.lit + buckets.rest + buckets.dim, lit, labels: labelOps };
})()
```

| stage | lit | dim | rest | lit values |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 48 | — |
| 1 | 12 | 36 | 0 | all 12 `sqft_living` |
| 2 | 2 | 46 | 0 | `living:1680`, `living:2090` |
| 3 | 15 | 33 | 0 | 5 each of `sqft_lot`, `bedrooms`, `bathrooms` |
| 4 | 5 | 43 | 0 | 5 `sqft_living` |
| 5 | 15 | 33 | 0 | 5 each of `sqft_lot`, `bedrooms`, `bathrooms` |
| 6 | 5 | 43 | 0 | 5 `sqft_living` |
| 7 | 0 | 0 | 48 | — |

Every stage except 0 and 7 must report `rest: 0`. A non-zero `rest` means a value or label was left for no rule to cover — the failure the per-stage complete-state rule exists to prevent.

At stages 3 and 5 the lit values must be the five houses at x 551, 619, 687, 984, 1066: `sqft_lot` 7600 / 8000 / 8400 / 8800 / 9100, `bedrooms` 4 / 4 / 5 / 5 / 5, `bathrooms` 2.5 / 2.5 / 3 / 3 / 3.

The `labels` opacities differ by stage, because a stage lights the label of every row it lights:

| stage | `labels` opacities (order: sqft_living, sqft_lot, bedrooms, bathrooms) |
| --- | --- |
| 0 | four 0.55 |
| 1 | 1, 0.22, 0.22, 0.22 |
| 2 | 1, 0.22, 0.22, 0.22 |
| 3 | 0.22, 1, 1, 1 |
| 4 | 1, 0.22, 0.22, 0.22 |
| 5 | 0.22, 1, 1, 1 |
| 6 | 1, 0.22, 0.22, 0.22 |
| 7 | four 0.55 |

At stages 3 and 5 three labels are lit, not one: those are the stages that light three rows. The value counts are unaffected — 15 lit and 33 dimmed at those two stages, as the table above already states.

Diagnosis: `lit: 6` at stage 4 means `.h-mid` was left on a value that is not also `.h-nn`. `rest: 20` at stage 7 means a stage-7 rule was added where none belongs. `lit: 32` at stage 3 means a `:not(.h-nn)` dim selector lost its closing parenthesis and silently dropped.

---

### Task 6: Update the panel copy and the one changed number

**Files:**

- Modify: `presentation/deck.html` — the `#mk-knn` and `#mk-snn` comments, the `#mk-snn` value text, the four pick SVGs, the four panels' `<dl>`, the summary `<ul>` and `.ph-panel-nums`, the stage hint, and the CSS comment at `deck.html:1352-1355`

**Interfaces:**

- Consumes: Task 1's verified numbers.
- Produces: slide copy matching what the diagram now shows. No number changes except 3468 → 3470.

- [ ] **Step 1: Confirm the label rest opacity lives only in CSS**

Check that the `.ar-lab` group you wrote in Task 3 Step 2 has no `opacity` attribute, and that `.houses-svg .v, .houses-svg .al { opacity: 0.55 }` from Task 5 Step 1 is the only rest opacity. A lit label that renders dimmer than a lit value means one of the two is doubled up.

- [ ] **Step 2: Update the CSS comment above the KNN marker rules**

At `deck.html:1352-1355` the comment reads "2802 unweighted, 3468 weighted". Change `3468` to `3470`.

- [ ] **Step 3: Correct the two marker comments**

The existing `#mk-knn` comment (`deck.html:2106-2108`) says the equal-weight result "lands below the city average, because four of the five are smaller than the mean". Both halves are wrong: 2802 is *above* 2225, and per Task 1 Step 4 it is three of the five that are larger. Replace with:

```html
<!-- KNN marker: the five closest houses averaged with EQUAL weight. That lands
     above the city average of 2225, because three of the five are larger than
     it - but it is still one number for every house. -->
```

The existing `#mk-snn` comment is correct in direction and stays, but its value reference moves:

```html
<!-- Scaled KNN marker: the same five houses, each weighted 1 over its distance
     across sqft_lot, bedrooms and bathrooms. The two closest dominate, so the
     answer lands well above the equal-weight average of the identical five. -->
```

- [ ] **Step 4: Change the weighted marker value**

In `#mk-snn`, change the `<text>` body from `3468` to `3470`. `mk-avg` keeps `2225`, `mk-med` keeps `1885`, `mk-knn` keeps `2802`.

- [ ] **Step 5: Rewrite the four pick SVGs to one template**

All four become `viewBox="0 0 300 128"` so they render at one scale. **Every line inside moves, not just the two named below**: the context and formula lines to y = 10 / 26 / 38, the result to 62, the `n` line to 78, the strip's twelve `<use>` translations to y=100, and the caption to 120. The current `= 3468` at `deck.html:2291` also carries `y="48"`, which becomes `y="62"` — a partial hand-edit driven only by the two named lines would leave the result at the old height. **Replace each `<svg class="ph-calc">` block whole** using the markup below; do not hand-edit individual `<text>` y values inside the existing ones. The KNN panel also **loses** `each house counts the same`, replaced by `12 compared on 3 columns, 5 kept` and `then one column is read`.

**Why 128.** `.ph-panel-pick svg` is `width:100%; max-height:240px` (`deck.html:1454-1457`) in a `flex: 1 1 50%` cell about 562.5px wide, so the scale is 1.875. At viewBox height 128 the rendered height is exactly 240px — at the cap, not over it. At 132 it would be 247px and the SVG would become height-capped instead of width-capped, shrinking its text for no reason. Keep 128.

Average (`ph-is-av`):

```html
<svg class="ph-calc" viewBox="0 0 300 128" fill="none" role="img"
  aria-label="Average of all 12 houses: 2225 square feet. One column is read, living area, across all 12 houses.">
  <text class="ph-calc-f" x="150" y="10" text-anchor="middle">one column, every house</text>
  <text class="ph-calc-f" x="150" y="26" text-anchor="middle">=AVERAGE(1235,1300,1365,1520,1600,1680,</text>
  <text class="ph-calc-f" x="150" y="38" text-anchor="middle">2090,2200,2310,3610,3800,3990)</text>
  <text class="ph-calc-r" x="150" y="62" text-anchor="middle">= 2225</text>
  <text class="ph-calc-n" x="150" y="78" text-anchor="middle">n = 12 houses</text>
  <g class="ph-calc-strip">
    <use href="#hs" transform="translate(22,100) scale(0.3)" />
    <use href="#hs" transform="translate(44,100) scale(0.3)" />
    <use href="#hs" transform="translate(66,100) scale(0.3)" />
    <use href="#hs" transform="translate(88,100) scale(0.3)" />
    <use href="#hs" transform="translate(110,100) scale(0.3)" />
    <use href="#hs" transform="translate(132,100) scale(0.3)" />
    <use href="#hs" transform="translate(154,100) scale(0.3)" />
    <use href="#hs" transform="translate(176,100) scale(0.3)" />
    <use href="#hs" transform="translate(198,100) scale(0.3)" />
    <use href="#hs" transform="translate(220,100) scale(0.3)" />
    <use href="#hs" transform="translate(242,100) scale(0.3)" />
    <use href="#hs" transform="translate(264,100) scale(0.3)" />
  </g>
  <text class="ph-calc-c" x="150" y="120" text-anchor="middle">12 of 12 read</text>
</svg>
```

Medium (`ph-is-md`): identical geometry and strip; these four lines change.

```html
<svg class="ph-calc" viewBox="0 0 300 128" fill="none" role="img"
  aria-label="Median of all 12 houses: 1885 square feet, the average of the two middle houses. One column is read, living area, and only houses 6 and 7 of it.">
  <text class="ph-calc-f" x="150" y="10" text-anchor="middle">one column, the middle of it</text>
  <text class="ph-calc-f" x="150" y="26" text-anchor="middle">=MEDIUM(1235,1300,1365,1520,1600,1680,</text>
  <text class="ph-calc-f" x="150" y="38" text-anchor="middle">2090,2200,2310,3610,3800,3990)</text>
  <text class="ph-calc-r" x="150" y="62" text-anchor="middle">= 1885</text>
  <text class="ph-calc-n" x="150" y="78" text-anchor="middle">n = 12 houses</text>
  <g class="ph-calc-strip">
    <use href="#hs" transform="translate(22,100) scale(0.3)" />
    <use href="#hs" transform="translate(44,100) scale(0.3)" />
    <use href="#hs" transform="translate(66,100) scale(0.3)" />
    <use href="#hs" transform="translate(88,100) scale(0.3)" />
    <use href="#hs" transform="translate(110,100) scale(0.3)" />
    <use href="#hs" transform="translate(132,100) scale(0.3)" />
    <use href="#hs" transform="translate(154,100) scale(0.3)" />
    <use href="#hs" transform="translate(176,100) scale(0.3)" />
    <use href="#hs" transform="translate(198,100) scale(0.3)" />
    <use href="#hs" transform="translate(220,100) scale(0.3)" />
    <use href="#hs" transform="translate(242,100) scale(0.3)" />
    <use href="#hs" transform="translate(264,100) scale(0.3)" />
  </g>
  <text class="ph-calc-c" x="150" y="120" text-anchor="middle">2 of 12 read &#8212; the two middle</text>
</svg>
```

Nearest Neighbor (`ph-is-knn`):

```html
<svg class="ph-calc" viewBox="0 0 300 128" fill="none" role="img"
  aria-label="Nearest Neighbor in two steps. Step one compares every house on lot size, bedrooms and bathrooms and keeps the five closest. Step two averages their living area: 2802.">
  <text class="ph-calc-f" x="150" y="10" text-anchor="middle">this listing: 5 bed, 3 bath, 9000 sqft lot</text>
  <text class="ph-calc-f" x="150" y="26" text-anchor="middle">12 compared on 3 columns, 5 kept</text>
  <text class="ph-calc-f" x="150" y="38" text-anchor="middle">=AVERAGE(3800,3610,2310,2200,2090)</text>
  <text class="ph-calc-r" x="150" y="62" text-anchor="middle">= 2802</text>
  <text class="ph-calc-n" x="150" y="78" text-anchor="middle">then one column is read</text>
  <g class="ph-calc-strip">
    <use href="#hs" transform="translate(22,100) scale(0.3)" />
    <use href="#hs" transform="translate(44,100) scale(0.3)" />
    <use href="#hs" transform="translate(66,100) scale(0.3)" />
    <use href="#hs" transform="translate(88,100) scale(0.3)" />
    <use href="#hs" transform="translate(110,100) scale(0.3)" />
    <use href="#hs" transform="translate(132,100) scale(0.3)" />
    <use href="#hs" transform="translate(154,100) scale(0.3)" />
    <use href="#hs" transform="translate(176,100) scale(0.3)" />
    <use href="#hs" transform="translate(198,100) scale(0.3)" />
    <use href="#hs" transform="translate(220,100) scale(0.3)" />
    <use href="#hs" transform="translate(242,100) scale(0.3)" />
    <use href="#hs" transform="translate(264,100) scale(0.3)" />
  </g>
  <text class="ph-calc-c" x="150" y="120" text-anchor="middle">5 of 12 read &#8212; closest on all three</text>
</svg>
```

Scaled Nearest Neighbor (`ph-is-snn`):

```html
<svg class="ph-calc" viewBox="0 0 300 128" fill="none" role="img"
  aria-label="Scaled Nearest Neighbor in two steps. Step one keeps the same five houses by the same three columns. Step two weights their living area by closeness: 3470.">
  <text class="ph-calc-f" x="150" y="10" text-anchor="middle">this listing: 5 bed, 3 bath, 9000 sqft lot</text>
  <text class="ph-calc-f" x="150" y="26" text-anchor="middle">=SUMPRODUCT({3800;3610;2310;2200;2090},</text>
  <text class="ph-calc-f" x="150" y="38" text-anchor="middle">{1/2;1/4;1/12;1/22;1/30}) &#247; SUM(w)</text>
  <text class="ph-calc-r" x="150" y="62" text-anchor="middle">= 3470</text>
  <text class="ph-calc-n" x="150" y="78" text-anchor="middle">n = 12 houses</text>
  <g class="ph-calc-strip">
    <use href="#hs" transform="translate(22,100) scale(0.3)" />
    <use href="#hs" transform="translate(44,100) scale(0.3)" />
    <use href="#hs" transform="translate(66,100) scale(0.3)" />
    <use href="#hs" transform="translate(88,100) scale(0.3)" />
    <use href="#hs" transform="translate(110,100) scale(0.3)" />
    <use href="#hs" transform="translate(132,100) scale(0.3)" />
    <use href="#hs" transform="translate(154,100) scale(0.3)" />
    <use href="#hs" transform="translate(176,100) scale(0.3)" />
    <use href="#hs" transform="translate(198,100) scale(0.3)" />
    <use href="#hs" transform="translate(220,100) scale(0.3)" />
    <use href="#hs" transform="translate(242,100) scale(0.3)" />
    <use href="#hs" transform="translate(264,100) scale(0.3)" />
  </g>
  <text class="ph-calc-c" x="150" y="120" text-anchor="middle">same 5, closest counting most</text>
</svg>
```

The weight list `{1/2;1/4;1/12;1/22;1/30}` is the distance list 2, 4, 12, 22, 30 from the reference table, reciprocated, in the same order as the size list (3800, 3610, 2310, 2200, 2090). If you change a distance, change its weight and re-derive 3470 (Task 1 Step 3) in the same edit.

- [ ] **Step 6: Update the four panels' `<dl>`**

| Panel | `Steps` | `Reads` | `Chooses` | `Computes` | `Per house` |
| --- | --- | --- | --- | --- | --- |
| `ph-is-av` | `1 step` | `1 column &#8212; square feet` | `Nothing &#8212; all 12 houses` | `1 number: the average of all 12` | `Same answer for every blank` |
| `ph-is-md` | `1 step, or 2 on an even count` | `1 column &#8212; square feet` | `The 1 middle house, or the 2 middle ones` | `1 number: its value, or the average of 2` | `Same answer for every blank` |
| `ph-is-knn` | `2 steps: find, then fill` | `3 columns to find, 1 to fill` | `The 5 closest on lot size, bedrooms and bathrooms` | `1 number: plain average of their 5 sizes` | `The answer changes with the house` |
| `ph-is-snn` | `2 steps: find, then fill` | `3 columns to find, 1 to fill` | `The 5 closest on lot size, bedrooms and bathrooms` | `1 number: weighted average of their 5 sizes` | `The answer changes with the house` |

Leave the first three rows of `ph-is-av` and `ph-is-md` exactly as they are — they already say the right thing. Only the `knn` and `snn` rows change.

`Reads` counts the columns that decide **which houses** — the same three the row beneath it enumerates in `Chooses`, the same three the pick SVG names and the diagram lights. It is 3, not 4: counting square feet as a fourth "find" column would contradict the diagram, which dims that row during the find because square feet is what comes *out* of it. Every other string on the slide says three; the dl must not be the lone outlier. The idea worth making — several attributes to choose, one to fill — is carried by the diagram's three-rows-then-one-row gesture and needs no larger number.

- [ ] **Step 7: Update the summary panel**

Replace the `<ul>` bullets:

```html
<li>Average &#8212; one value for the whole column</li>
<li>Medium &#8212; the middle of that column</li>
<li>Nearest Neighbor &#8212; 5 closest on 3 columns, then their sizes</li>
<li>Scaled NN &#8212; the same 5, closest counting most</li>
```

And the `.ph-panel-nums` body:

```html
<p class="ph-panel-nums">
  AVG 2225 &#183; MEDIUM 1885 &#183; NN(5) 2802 &#183; NN(5)w 3470
</p>
```

- [ ] **Step 8: Rewrite the stage hint**

Replace the `p.ph-stage-hint` body:

```html
<p class="ph-stage-hint">
  The diagram above is 12 houses. Each carries four of the columns this API
  imputes &#8212; living area, lot size, bedrooms, bathrooms &#8212; and any one of
  them can be the one that came back blank.
</p>
```

`.ph-stage-hint` is `position:absolute` below the top row (`deck.html:1305-1312`), so a second line costs nothing and does not move the flex basis. Task 7 Step 3 checks it clears the slide.

- [ ] **Step 9: Confirm every `deck.html` occurrence changed**

Run: `grep -n 3468 presentation/deck.html`
Expected: no output. The five sites are `deck.html:1353` (Step 2), `2132` (Step 4), `2288` and `2291` (Step 5), `2323` (Step 7).

---

### Task 7: Visual verification of the whole slide

**Files:**

- Modify: none

**Interfaces:**

- Consumes: everything above.
- Produces: a slide confirmed to render, fit and read correctly at all eight states.

This task is the verification. It is not optional and it is not replaced by "the selectors look right".

- [ ] **Step 1: Open the deck**

`presentation/deck.html` loads reveal.js and two webfonts from CDNs, so it needs network access; offline, the slide still lays out but fonts fall back. Jump with `Reveal.slide(3, 0, N)`, where N is the fragment index (see Step 2).

- [ ] **Step 2: Capture all eight states**

For N in 0..7, `Reveal.slide(3, 0, N)` — the third argument is the *fragment* index; the sections are all top-level, so there is no vertical stack and `Reveal.slide(3, N)` would set a vertical index that does not exist — and screenshot. Confirm each:

1. **Base** — four rows of values, four labels in the left gutter, nothing lit but everything legible, hint visible, no marker, no box, no panel.
2. **Stage 1** — amber `sqft_living` row across all twelve; the other three rows clearly receded; amber box bottom edge sits *between* the `sqft_living` and `sqft_lot` rows, not through the lot sizes; `Avg 2225` above.
3. **Stage 2** — blue `sqft_living` lit on two values only (1680, 2090); blue box around houses 6 and 7.
4. **Stage 3** — purple `sqft_lot`, `bedrooms`, `bathrooms` lit on five houses each; `sqft_living` fully receded; purple box reaching past the `bathrooms` row; **no marker and no number**, because nothing has been computed.
5. **Stage 4** — the three comparison rows recede; purple `sqft_living` lights on five values; box shortens to stop between `sqft_living` and `sqft_lot`; `NN(5) 2802` appears, centred over the box.
6. **Stage 5** — stage 3's picture in pink, again with no marker.
7. **Stage 6** — stage 4's picture in pink; `NN(5)w 3470` appears, clear of the `NN(5)` marker.
8. **Stage 7** — summary panel, all four markers, no box, the attribute grid back at rest.

If stages 3 or 5 show a number, a marker guard is missing. If stage 6 shows no panel, the `ph-is-snn` guard points at driver 6 instead of 7.

- [ ] **Step 3: Assert the two things that most often break**

Vertical fit — the two-line hint must clear the slide:

```js
(() => {
  const h = document.querySelector('#s4-approaches .ph-stage-hint');
  const s = document.getElementById('s4-approaches').getBoundingClientRect();
  const r = h.getBoundingClientRect();
  return { inside: r.bottom <= s.bottom, hintBottom: Math.round(r.bottom), slideBottom: Math.round(s.bottom) };
})()
```

Run at stage 0. Expected `inside: true`. Irrelevant from stage 1 on — the hint is `display:none` once driver 1 is visible.

Subtitle width — no ellipsis on any of the seven:

```js
(() => [...document.querySelectorAll('#s4-approaches .ph-s4-sub')]
  .map(e => ({ t: e.textContent.trim(), clipped: e.scrollWidth > e.clientWidth + 1 })))()
```

Expected: every `clipped` is `false`.

- [ ] **Step 4: Check nothing leaked to the other slides**

Step through slides 1-3 and 5-7. S8 carries `data-visibility="hidden"` and is not reachable by stepping.

Every rule added in Tasks 4 and 5 is prefixed `section[data-s4]`, and the only two rules not stage-scoped are the rest-state `.v` / `.al` pair in Task 5 Step 1, which are scoped to `.houses-svg` — an id that exists only on S4.

---

### Task 8: Bring `deck-script.md` §S4 in line

**Files:**

- Modify: `presentation/deck-script.md` (lines 442-585)

**Interfaces:**

- Consumes: every number, class name and coordinate fixed by Tasks 2-6.
- Produces: the section that documents the slide as it now is.

Its fragment, box and marker counts are already correct; Task 1 Step 5 lists exactly which lines are stale.

- [ ] **Step 1: Update the staging paragraph**

Current text at `deck-script.md:444-448`:

``` text
Layout: T-houses-staged. Fragments: 5 hidden `.ph-s4-go` drivers.
**Staging is CSS only** — `section[data-s4]:has(.ph-s4-go:nth-of-type(N).visible)`
selects stage N. There is no `setS4Stage`, no `is-stage-N` class, no
`Reveal.slide(h,0,-1)` reset. Houses are STATIC (mist stroke, fixed
transforms); markers, dashed boxes, subtitle and panel fade per stage.
```

Replace with:

``` text
Layout: T-houses-staged. Fragments: 7 hidden `.ph-s4-go` drivers.
**Staging is CSS only** — stage N is
`:has(.ph-s4-go:nth-of-type(N).visible):not(:has(.ph-s4-go:nth-of-type(N+1).visible))`,
because reveal only ever ADDS `.visible`: at stage N drivers 1..N are all
visible, so a rule without the `:not()` guard fires for every stage at or after
its own. Stage 7 is the one bare `:has(...7...)` rule, unique because driver 7
exists nowhere else. House glyphs are STATIC (mist stroke, fixed transforms);
markers, dashed boxes, subtitle, panel and attribute values change per stage.
```

- [ ] **Step 2: Update the houses paragraph and add the attribute rows**

`deck-script.md:451` still reads `viewBox="15 -80 1195 340"`. Change it to `viewBox="-30 -80 1240 380"`, then insert after the houses table:

``` text
**Attribute rows** — four rows below the baseline, twelve values each, keyed to
the same twelve house `x` values. Row baselines 232 / 251 / 270 / 289; pitch
19u. `sqft_living` at 14px, the other three at 13px. The left gutter (viewBox
x = -30 to 35, house 1's left tip) carries one label per row, right-anchored
at `x = 30`, `y = row + 3`, 11px. Labels carry NO opacity attribute - SVG group
opacity would multiply with the CSS rest opacity.

| Row | Class | Label | Values (houses 1-12) |
|-----|-------|-------|-----------------------|
| `sqft_living` | `.ar-row.ar-living` | `sqft_living` | 1235 1300 1365 1520 1600 1680 2090 2200 2310 3610 3800 3990 |
| `sqft_lot` | `.ar-row.ar-lot` | `sqft_lot` | 4600 4900 5300 5600 6200 5900 7600 8000 8400 8800 9100 6400 |
| `bedrooms` | `.ar-row.ar-bed` | `bedrooms` | 2 2 2 3 3 3 4 4 5 5 5 6 |
| `bathrooms` | `.ar-row.ar-bath` | `bathrooms` | 1 1.5 1.5 1.5 1.5 2 2.5 2.5 3 3 3 4 |

The four row labels are column names from `src/api/shared.py` `REQUEST_COLUMNS`
(`bedrooms`, `bathrooms`, `sqft_living`, `sqft_lot`, `floors`, `sqft_above`,
`sqft_basement`) - the slide must not show a field the service does not carry.
`sqft_living` is the one that came back blank; the other three choose the
neighbours. `floors`, `sqft_above` and `sqft_basement` are not shown because
`sqft_above` and `sqft_basement` are derived from `sqft_living`, and using them
to find neighbours would contradict the diagram dimming that row during the
find. The VALUES are constructed for this example, not sampled from the
dataset; only the column names are taken from the schema.

The diagram describes one listing whose living area came back blank (5
bedrooms, 3 bathrooms, a 9000 sq ft lot). Neighbour distance is
`|sqft_lot-9000|/50 + |bedrooms-5| + 2*|bathrooms-3|`, which ranks houses 11, 10,
9, 8, 7 as the five closest - the same five `.h-nn` already marks. Distance is
monotonic in size (2, 4, 12, 22, 30), so the bigger house is the closer one.
House 12, the largest on the slide, ranks sixth at 55 and is deliberately not a
neighbour: it is a big house on a small lot with 6 bedrooms and 4 bathrooms, a
different kind of house rather than a closer one.

Every value carries `.v`; houses 6 and 7 also carry `.h-mid`; houses 7-11 also
carry `.h-nn`; house 7 carries both. A value that is not lit is a value the
method did not read. Rest opacity 0.55, lit 1 at the method's colour, unused
rows 0.22. Each stage's rule block states that stage's COMPLETE state, since the
range guards mean only one stage's rules match at a time.
```

- [ ] **Step 3: Replace the dashed-input-boxes table**

| Id | x | width | height | right | bottom | Colour | Stage |
| ---- | --- | ------- | -------- | ------- | -------- | -------- | ------- |
| `bx-avg` | 32 | 1164 | 122 | 1196 | 238 | `var(--av)` | 1 |
| `bx-med` | 324 | 260 | 122 | 584 | 238 | `var(--md)` | 2 |
| `bx-knn-pick` | 510 | 596 | 180 | 1106 | 296 | `var(--knn)` | 3 |
| `bx-knn` | 510 | 596 | 122 | 1106 | 238 | `var(--knn)` | 4 |
| `bx-snn-pick` | 510 | 596 | 180 | 1106 | 296 | `var(--snn)` | 5 |
| `bx-snn` | 510 | 596 | 122 | 1106 | 238 | `var(--snn)` | 6 |

All at `y = 116`, `stroke-dasharray="8 5"`. Horizontal extent answers *which
houses*, height answers *which attributes*: 122 stops between the `sq ft` row
and the `built` row, 180 reaches past `beds`. No box at stage 7.

Add after the table:

``` text
Box bounds are not house centres. `#hs` spans `x - 25` to `x + 25`, so a house
at `x` with `scale s` occupies `x - 25s` to `x + 25s`. The box table was derived
from those spans so each box encloses exactly its stage's houses. House 11's
right tip is 1105.1 and house 12's left tip is 1107.0 - a 1.9u gap - so
`bx-knn`'s right edge at 1106 sits inside it and its dash touches house 12's roof.
That is inherent to the load-bearing house spacing and is acceptable because the
ATTRIBUTE LIGHTING, not the box, says which houses are read: house 12's values
never light.

The previous `bx-knn` was `x=584 width=611` and enclosed houses 8-12: it
included house 12, the house this design deliberately excludes, and dropped
house 7. Corrected to 510-1106.
```

- [ ] **Step 4: Update the marker table and prose**

The table at `deck-script.md:480-485` already lists all four markers, including `NN weighted`. Change its `3468` cell to `3470`. Change `mk-knn` and `mk-snn`'s `cx` to 760 and 940.

The prose at `deck-script.md:487-491` needs two edits: `3468 weighted` → `3470 weighted`, and "The two live side by side at stage 5; 1150 puts the weighted house clear of the plain one at 952." → "The two live side by side at stage 7; 940 puts the weighted house clear of the plain one at 760, and both sit inside the `bx-knn` box's 510-1106 span."

- [ ] **Step 5: Replace the stage and subtitle tables**

`deck-script.md:493-504` says "holding five stacked" and "Stage 5 shows all four markers". Replace both tables with:

| Stage | Subtitle | Class | Box | Marker | Rows lit |
| --- | --- | --- | --- | --- | --- |
| 1 | Average Value | `ph-is-av` | `bx-avg` | `mk-avg` | `sqft_living`, 12 houses |
| 2 | Medium value | `ph-is-md` | `bx-med` | `mk-med` | `sqft_living`, houses 6-7 |
| 3 | Nearest Neighbor — find the 5 closest | `ph-is-knn` | `bx-knn-pick` | — | `sqft_lot`/`bedrooms`/`bathrooms`, 5 houses |
| 4 | Nearest Neighbor — read their size | `ph-is-knn` | `bx-knn` | `mk-knn` | `sqft_living`, 5 houses |
| 5 | Scaled Nearest Neighbor — find the 5 closest | `ph-is-snn` | `bx-snn-pick` | — | `sqft_lot`/`bedrooms`/`bathrooms`, 5 houses |
| 6 | Scaled Nearest Neighbor — read and weight | `ph-is-snn` | `bx-snn` | `mk-snn` | `sqft_living`, 5 houses |
| 7 | Summary: similar homes win | `ph-is-sum` (`--ph-accent`) | — | all four | none |

Keep the sentence "`div.ph-subs`, a one-cell grid (`min-height:calc(var(--fs-sub) * 1.3)`)" but change "five stacked `p.ph-subtitle.ph-s4-sub`" to "seven stacked". Two subtitles share `ph-is-knn` and two share `ph-is-snn`, so the opacity rule keys off `.ph-s4-sub:nth-of-type(N)` and colour off `.ph-is-*`.

- [ ] **Step 6: Update the hint, panel and c-calc tables**

Hint, at `deck-script.md` §S4: `The diagram above is 12 houses. Each carries four of the columns this API imputes — living area, lot size, bedrooms, bathrooms — and any one of them can be the one that came back blank.`

The panel `<dl>` table records `Steps`, `Reads`, `Chooses` and `Computes` per panel. Only panels 3 and 4 change, and they change **four cells each**, not just `Reads` — `Steps`, `Reads`, `Chooses` and `Computes` all move:

| Panel | `Steps` | `Reads` | `Chooses` | `Computes` |
| --- | --- | --- | --- | --- |
| 1, 2 | unchanged | `1 column — square feet` | unchanged | unchanged |
| 3 | `2 steps: find, then fill` | `3 columns to find, 1 to fill` | `The 5 closest on lot size, bedrooms and bathrooms` | `1 number: plain average of their 5 sizes` |
| 4 | `2 steps: find, then fill` | `3 columns to find, 1 to fill` | `The 5 closest on lot size, bedrooms and bathrooms` | `1 number: weighted average of their 5 sizes` |

The c-calc prose at `deck-script.md:554-557` says "two formula lines", `viewBox="0 0 300 118"` and "baseline y=96". Replace with:

``` text
**c-calc SVGs** — `svg.ph-calc`, one per calculation panel, identical shape:
a context line, one or two formula lines, the result, an `n` line, a strip of
twelve `#hs` at 0.3 scale (x = 22 to 264 in steps of 22, baseline y=100), and a
caption. `max-height:240px`, `width:100%`, `viewBox="0 0 300 128"`. The height
is 128, not more: the panel cell is ~562.5px wide, so the scale is 1.875 and 128
gives exactly 240px — at the cap, not over it.
```

And the panel table at `deck-script.md:563-568` — update **both** KNN rows, not just the Scaled NN one:

| Panel | New Formula | Result |
| --- | --- | --- |
| KNN | `this listing: 5 bed, 3 bath, 9000 sqft lot` / `12 compared on 3 columns, 5 kept` / `=AVERAGE(3800,3610,2310,2200,2090)` | `= 2802` |
| Scaled NN | `this listing: 5 bed, 3 bath, 9000 sqft lot` / `=SUMPRODUCT({3800;3610;2310;2200;2090},` / `{1/2;1/4;1/12;1/22;1/30}) ÷ SUM(w)` | `= 3470` |

The KNN row needs it because Task 6 Step 5 **deletes** the line `each house counts the same`, which that row currently quotes. Then rewrite the prose beneath the table:

``` text
The two KNN answers are 14010/5 = **2802** equal-weight and the same five
weighted by 1/d over three columns = **3470** — distances 2, 4, 12, 22, 30,
reciprocated. House 12, the largest on the slide, is not among the five: at 55
its distance ranks it sixth, so however big it is, it is not a neighbour — it
is a big house on a 6400 sq ft lot with 6 bedrooms and 4 bathrooms.
`src/api/shared.py` fits
`KNNImputer(n_neighbors=5, weights="distance")`, so the service always runs the
scaled variant.
Summary: `p.ph-panel-nums`: `AVG 2225 · MEDIUM 1885 · NN(5) 2802 · NN(5)w 3470`
```

- [ ] **Step 7: Update the summary bullets and speaker notes**

The four bullets at `deck-script.md:549-552` become:

``` text
- Average — one value for the whole column
- Medium — the middle of that column
- Nearest Neighbor — 5 closest on 3 columns, then their sizes
- Scaled NN — the same 5, closest counting most
```

The five speaker notes at `deck-script.md:577-581` become seven, one per stage, preserving the existing "this is the one that ships" line:

``` text
- Say (per click): "City average — one column, one number for every house." →
  "Middle value — mansions stop skewing it, still one number." →
  "Find the five closest — and to find them it reads three columns, not one." →
  "Now it averages their size. Three columns in, one column out." →
  "Same five, found the same way." →
  "Weighted by how close — the two closest carry the answer. This is the one
  that ships." →
  "Summary: neighbours adapt, averages don't."
```

- [ ] **Step 8: Confirm nothing stale survives**

Run: `grep -n "3468" presentation/deck.html presentation/deck-script.md`
Expected: no output.

Run: `grep -n "15 -80 1195 340\|300 118\|y=96\|Fragments: 5\|five stacked" presentation/deck-script.md`
Expected: no output.

---

## Execution Handoff

Plan complete at `docs/superpowers/plans/2026-10-05-s4-secondary-attributes.md`.

**For agentic workers:** use superpowers:subagent-driven-development or superpowers:executing-plans. Every task is independently verifiable with a console assertion or a screenshot. Do not batch Tasks 2-5 into one edit: Task 2's viewBox change is what makes Task 3's rows visible, and a collapsed viewBox reads as a Task 3 bug. Task 1 must complete before Task 6, because every number in Task 6 is copied from it.

There is nothing to lint or format afterwards: CI runs pytest, ruff and pyright over Python only, and both files touched here are HTML and Markdown. Verification is Task 7.
