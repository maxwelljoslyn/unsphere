// Reusable charting module, built on Observable Plot.
//
// Plot is a high-level, SVG-emitting grammar of charts (it sits on top of D3).
// The whole point of this file is to keep that library an *implementation
// detail* behind a small, stable API: callers import renderLine / renderCalendar
// and pass plain data plus key names, never touching Plot directly. The Stats
// page is the first consumer, but any template can `import` from here later; if
// we ever swap the underlying library, callers don't change.
//
// No build step: this is a native ES module that pulls Plot straight from a CDN,
// matching how the app already loads htmx. Import it from a template with
// `<script type="module">import { renderLine } from "{% static 'js/charts.js' %}"`.

import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";

// One knob for all chart text — axis labels, tick labels (incl. the calendar's
// weekday letters), legends. Larger than Plot's tiny default so everything reads
// at a glance; bump it here to resize every chart at once.
const LABEL_FONT_SIZE = "14px";

// Shown in place of a chart when there's nothing to draw yet, so a new user's
// dashboard reads as "no data" rather than a broken/empty box.
function emptyState(message) {
  const p = document.createElement("p");
  p.className = "chart-empty";
  p.textContent = message || "No data yet.";
  return p;
}

// Width tracks the container so charts fit their column; height is fixed for a
// consistent aspect. Falls back to a sane default before layout settles.
function width(el) {
  return Math.max(280, Math.floor(el.getBoundingClientRect().width) || 640);
}

// A time-series line over a temporal x. Pass key names for x/y; x values are
// ISO date strings (parsed to Date here). `curve: "step-after"` gives the
// staircase used for cumulative totals — flat between points, a jump on each —
// but any Plot curve name works for ordinary trends.
export function renderLine(el, data, opts = {}) {
  const {
    x = "x",
    y = "y",
    xLabel = null,
    yLabel = null,
    color = "#2563eb",
    curve = "linear",
  } = opts;

  if (!data || data.length === 0) {
    el.replaceChildren(emptyState());
    return;
  }

  const rows = data.map((d) => ({ ...d, [x]: new Date(d[x]) }));

  const chart = Plot.plot({
    width: width(el),
    height: 260,
    marginLeft: 56,
    marginBottom: 36,
    style: { fontSize: LABEL_FONT_SIZE },
    x: { label: xLabel, type: "utc" },
    y: { label: yLabel, grid: true, nice: true, zero: true },
    marks: [
      Plot.ruleY([0]),
      Plot.lineY(rows, { x, y, stroke: color, strokeWidth: 2, curve }),
      Plot.dot(rows, { x, y, fill: color, r: 2.5 }),
    ],
  });

  el.replaceChildren(chart);
}

// A GitHub-style calendar heatmap: one cell per day, colored by `value`,
// arranged week-as-column / weekday-as-row and faceted into a row per year.
// Dates are ISO day strings parsed as UTC so the weekday/week math is stable
// regardless of the viewer's zone.
export function renderCalendar(el, data, opts = {}) {
  const { date = "date", value = "value", scheme = "greens" } = opts;

  if (!data || data.length === 0) {
    el.replaceChildren(emptyState());
    return;
  }

  const rows = data.map((d) => {
    const day = new Date(d[date]); // ISO "YYYY-MM-DD" parses as UTC midnight
    return {
      day,
      value: d[value],
      // String so the year-per-row facet is an ordinal label ("2026"), not a
      // quantitative axis that would format it as "2,026".
      year: String(day.getUTCFullYear()),
      weekday: day.getUTCDay(), // 0 = Sunday
      week: weekOfYear(day),
    };
  });

  const years = Array.from(new Set(rows.map((r) => r.year))).sort();
  const weeks = Array.from({ length: 53 }, (_, i) => i); // full year of columns
  const weekdays = [0, 1, 2, 3, 4, 5, 6];

  // Square cells: derive the size from the available width across all 53 weeks,
  // then make each year's row tall enough for 7 weekday cells of that size — so
  // the grid reads like a calendar instead of stretched bars.
  const marginLeft = 40;
  const marginRight = 52; // room for the year label Plot draws on the right edge
  const cell = Math.max(8, (width(el) - marginLeft - marginRight) / weeks.length);
  // Anchor the color scale at 0 so a single-workout day reads as a clear green,
  // not the near-white low end of a 1..2 domain.
  const maxValue = Math.max(1, ...rows.map((r) => r.value));

  const chart = Plot.plot({
    width: width(el),
    height: years.length * cell * 7 + 50, // + room for legend and axis
    marginLeft,
    marginRight,
    padding: 0,
    style: { fontSize: LABEL_FONT_SIZE },
    x: { axis: null, domain: weeks },
    y: {
      tickFormat: (d) => "SMTWTFS"[d],
      tickSize: 0,
      domain: weekdays,
      label: null,
    },
    fy: { domain: years, label: null },
    color: {
      scheme,
      legend: true,
      label: "workouts",
      type: "linear",
      domain: [0, maxValue],
    },
    marks: [
      Plot.cell(rows, {
        x: "week",
        y: "weekday",
        fy: "year",
        fill: "value",
        inset: 1,
        rx: 2,
        title: (d) => `${d.day.toISOString().slice(0, 10)}: ${d.value}`,
      }),
    ],
  });

  el.replaceChildren(chart);
}

// Zero-based index of the week within a date's year (Sunday-started weeks), used
// as the calendar's x position. Computed by hand so this module needs no d3
// time-interval imports.
function weekOfYear(date) {
  const start = Date.UTC(date.getUTCFullYear(), 0, 1);
  const startWeekday = new Date(start).getUTCDay();
  const dayOfYear = Math.floor((date.getTime() - start) / 86400000);
  return Math.floor((dayOfYear + startWeekday) / 7);
}
