# phData Style Tokens for reveal.js

Source of truth for deck styling. Single change point: `presentation/assets/phdata.css`.
Metric numbers live in one place: `presentation/assets/deck.js` (`DECK_METRICS`); slides reference via `data-metric` keys, never hardcode.

## Brand basis (measured from phdata.io, 2026-09-30, live computed styles)

- Why-section bg `--ph-navy: #111F3A` — `rgb(17,31,58)`; logo dark-pixel avg matches.
- Why h2/numbers/card border/graphic stroke `--ph-mint: #A5FECA` — `rgb(165,254,202)`, 152 SVG uses.
- Card border `1px solid rgba(165,254,202,0.5)`, radius `16px`; card h `#FFFFFF` 32px/400; body white 75%.
- Capabilities cells `#F0F1F5` (`rgb(240,241,245)`), radius `10px`, title `#232A43` 18px/450.
- CTA pill: navy bg, mint text, radius `80px`. Body font `Aspekta, system-ui, sans-serif`.

## phData tokens

```css
:root {
  --ph-navy: #111F3A;
  --ph-mint: #A5FECA;
  --ph-card-border: rgba(165, 254, 202, 0.5);
  --ph-card-radius: 16px;
  --ph-why-h: #FFFFFF;
  --ph-why-body: rgba(255, 255, 255, 0.75);
  --ph-cap-bg: #F0F1F5;
  --ph-cap-radius: 10px;
  --ph-cap-h: #232A43;
  --ph-cta-bg: #111F3A;
  --ph-cta-fg: #A5FECA;
  --ph-cta-radius: 80px;
  --ph-font: "Aspekta", system-ui, sans-serif;
  --ph-slide-bg: var(--ph-navy);
  --ph-s1: #A5FECA;
  --ph-s2: #BCCCD4;
  --ph-s3: #FFFFFF;
}
```

## Mapping onto reveal.js theme tokens

```css
:root {
  --r-background-color: var(--ph-slide-bg);
  --r-main-color: #FFFFFF;
  --r-main-font: var(--ph-font);
  --r-main-font-size: 40px;
  --r-heading-font: var(--ph-font);
  --r-heading-color: var(--ph-mint);
  --r-heading-text-transform: none;
  --r-heading-font-weight: 400;
  --r-heading1-size: 2.4em;
  --r-heading2-size: 1.5em;
  --r-heading3-size: 1.15em;
  --r-link-color: var(--ph-mint);
  --r-link-color-hover: #FFFFFF;
  --r-block-margin: 20px;
  --r-code-font: "SFMono-Regular", Consolas, monospace;
  --r-selection-background-color: var(--ph-mint);
  --r-selection-color: var(--ph-navy);
}
```

## Global background (every slide)

Navy base + geometric motif tile. File: `presentation/assets/motif.svg`
(Why-section SVG language: thin mint strokes, partial opacity, crossed-cell grid).
Single rule, no per-slide backgrounds:

```css
.reveal .slides section {
  background-color: var(--ph-slide-bg);
  background-image: url("motif.svg");
  background-repeat: repeat;
  background-size: 360px auto;
  background-position: top right;
}
```

Light content (Capabilities cells, tables) renders as `--ph-cap-bg` cards on the navy base.

Global scale (reveal auto-size, no per-slide font hacks):

```js
Reveal.initialize({
  width: 1280,
  height: 720,
  margin: 0.06,
  minScale: 0.2,
  maxScale: 2.0,
  center: true,
  hash: true,
  slideNumber: true,
});
```

## Slide patterns (semantic HTML only)

No `style` attributes anywhere. Layout via reveal helpers + deck classes.

### Cover

```html
<section class="ph-cover">
  <p class="ph-kicker">Sound Realty &times; phData</p>
  <h1 class="r-fit-text">Every listing, priced — even with missing data</h1>
  <p class="ph-sub">Production-ready valuation API: KNN imputation, 6&times; faster, hardened errors</p>
  <aside class="notes">10-min, non-technical. No code on slides.</aside>
</section>
```

### Metric band (phData hero pattern)

```html
<section class="ph-metrics">
  <h2>Executive summary</h2>
  <dl class="ph-metric-band">
    <div class="ph-metric">
      <dt>Real-world requests recovered</dt>
      <dd><span data-metric="nnr.recovered">10&ndash;20%</span></dd>
    </div>
    <div class="ph-metric">
      <dt>Prediction latency, p50</dt>
      <dd><span data-metric="perf.v2p50">9.4 ms</span> <small>was <span data-metric="perf.v1p50">55.8 ms</span></small></dd>
    </div>
    <div class="ph-metric">
      <dt>Unknown-zipcode behavior</dt>
      <dd>Clear 404, no crash</dd>
    </div>
  </dl>
</section>
```

### At-a-glance (phData case-study table)

```html
<section>
  <h2>At a glance</h2>
  <table class="ph-glance">
    <tbody>
      <tr><th scope="row">Client</th><td>Sound Realty, Seattle housing valuations</td></tr>
      <tr><th scope="row">Challenge</th><td>Incomplete listings rejected; slow responses; unclear errors</td></tr>
      <tr><th scope="row">Delivery</th><td>KNN imputation (k=5) on <code>/predict/v2</code>; load-once caching; typed contracts</td></tr>
      <tr><th scope="row">Result</th><td>Missing-data requests score; p95 <span data-metric="perf.v2p95">13.4 ms</span>; 404 on unknown zip</td></tr>
    </tbody>
  </table>
</section>
```

### Solution comparison (Mean / Median / KNN)

Use `r-stack` + fragments so each diagram swaps in place; each solution is a `figure` with `figcaption`.
KNN table values come from `notebooks/imputation_experiment.ipynb` §7 (sqft_above −17%, bathrooms −16%, floors −15%, grade −14%).

### Auto-size rules

- `r-fit-text`: cover title + hero numbers only. Never body copy.
- `r-stack`: Mean/Median/KNN diagram swap.
- `r-stretch`: one diagram/visual per slide max (direct child of `section`).
- Global `width/height/margin` handles the rest; no per-slide font sizes.

## Single-source metrics (`deck.js`)

```js
const DECK_METRICS = {
  perf: { v1p50: "55.8 ms", v1p95: "78.9 ms", v2p50: "9.4 ms", v2p95: "13.4 ms" },
  nnr: { recovered: "10–20%" },
  knn: { k: "5", sqftAbove: "−17%", bathrooms: "−16%", floors: "−15%", grade: "−14%" },
};
document.querySelectorAll("[data-metric]").forEach((el) => {
  const v = el.dataset.metric.split(".").reduce((o, k) => o?.[k], DECK_METRICS);
  if (v != null) el.textContent = v;
});
```

Measured 2026-09-29, in-process TestClient, n=30, payload `98042`: v1 per-request load vs v2 lifespan-cached.
Method: `load_artifacts()` per call in `src/api/endpoints.py:36` vs once in `src/api/lifespan.py:20`.
Report as local-harness numbers, not production SLAs.

## Class catalog (all rendering flows through these)

- `.ph-cover`, `.ph-kicker`, `.ph-sub`
- `.ph-metric-band`, `.ph-metric`
- `.ph-glance` (table)
- `.ph-callout` (decision: KNN selected), `.ph-risk` (cost of doing nothing)
- `.ph-cols` (two-column prose), `.ph-diagram` (figure wrapper)
- `.ph-foot` (source line: `CANDIDATE_PROJECT.md:11`, notebook §7, file:line)

## Template A — Why phData (numbered thirds)

Observed on phdata.io: section heading `Why phData`, then 3 columns.
Screen-reader order per column: number, heading, body.
Columns: `01 Built for the real world` / `02 Strong systems start underneath` / `03 Built for what's next`.
Graphics are line SVG stroked `--ph-mint` with `--ph-mist` secondary; no words in graphics.
Deck mapping: `.ph-why` list of 3, each `p.ph-num` + `h3` + `p`. Numbers are text, never images.

```html
<section class="ph-why">
  <h2>Why this approach</h2>
  <ol class="ph-why-grid">
    <li><p class="ph-num">01</p><h3>Built for the real world</h3><p>Works on messy listings, not just clean demos.</p></li>
    <li><p class="ph-num">02</p><h3>Strong systems start underneath</h3><p>One load, typed contracts, clear errors.</p></li>
    <li><p class="ph-num">03</p><h3>Built for what's next</h3><p>New fields and volume without rework.</p></li>
  </ol>
</section>
```

## Template B — Capabilities (six-cell grid)

Observed on phdata.io: section heading `Capabilities`, then 6 cells, each title + one-line body.
Titles verbatim: AI and machine learning / Data engineering / Data migrations / Generative AI / Analytics and agentic activation / Elastic operations.
Deck mapping: `.ph-caps` list of 6, `h3` + `p` per cell, no `Learn more` links in deck.
Use for the modernization slide (S8) or a delivery-scope slide: each fix is one cell.

```html
<section class="ph-caps">
  <h2>What was delivered</h2>
  <ul class="ph-caps-grid">
    <li><h3>Missing-data handling</h3><p>Blanks filled from similar homes.</p></li>
    <li><h3>Load-once serving</h3><p>Model and data cached at startup.</p></li>
    <li><h3>Clear errors</h3><p>Unknown zip named in plain words.</p></li>
    <li><h3>Current runtime</h3><p>One supported version, locked installs.</p></li>
    <li><h3>Typed contracts</h3><p>Docs promise what the API returns.</p></li>
    <li><h3>Tested paths</h3><p>Null, missing, zero, and bad-zip covered.</p></li>
  </ul>
</section>
```
