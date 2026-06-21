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

// A GitHub-style calendar heatmap covering a trailing ~52 weeks: one cell per
// day, week-as-column / weekday-as-row, month labels across the top. The server
// sends only days that *have* workouts; we expand that into a dense grid here
// (every day in the window, zeros included) so the empty calendar is always
// drawn and the active days light up against it — the grid is what makes it
// read as a calendar. Dates are ISO day strings handled as UTC so the
// weekday/week math is stable regardless of the viewer's zone.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MS_DAY = 86400000;

// Discrete buckets read far better than a continuous ramp for small integer
// counts. Zero is a warm neutral (the empty grid); 1/2/3+ climb the app's sage
// green so a busy day stands out. Keep these two arrays in lockstep.
const COUNT_BUCKETS = ["0", "1", "2", "3+"];
const COUNT_COLORS = ["#E7E2D6", "#D6EBDC", "#86C29A", "#3E8E5A"];
const bucketOf = (c) => (c <= 0 ? "0" : c === 1 ? "1" : c === 2 ? "2" : "3+");

export function renderCalendar(el, data, opts = {}) {
  const { date = "date", value = "value" } = opts;

  if (!data || data.length === 0) {
    el.replaceChildren(emptyState());
    return;
  }

  // Sparse server data -> count keyed by ISO day string.
  const counts = new Map(data.map((d) => [d[date], d[value]]));

  // Trailing window of roughly three months, ending with the week that contains
  // today. Anchor "today" to the viewer's local calendar date but pin it to UTC
  // midnight so it lines up with the server's ISO day strings; the window starts
  // three calendar months back, snapped to that week's Sunday so every column is
  // one Sunday-started week.
  const now = new Date();
  const today = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  const threeMonthsBack = new Date(Date.UTC(now.getFullYear(), now.getMonth() - 3, now.getDate()));
  const start = addDays(threeMonthsBack, -threeMonthsBack.getUTCDay());

  // One row per day from window start through today, zeros filled in. Also note
  // the column where each month begins, for the top axis labels.
  const rows = [];
  const monthByCol = {};
  let lastCol = 0;
  for (let day = start; day <= today; day = addDays(day, 1)) {
    const iso = day.toISOString().slice(0, 10);
    const col = Math.floor((day - start) / MS_DAY / 7);
    rows.push({ iso, col, weekday: day.getUTCDay(), count: counts.get(iso) ?? 0 });
    // Label each month above its first *full* week-column (the one that sits
    // over the month's outlined region), not the partial column the 1st lands
    // in. Unless the 1st is itself a Sunday, that's the next column over.
    if (day.getUTCDate() === 1) {
      monthByCol[col + (day.getUTCDay() === 0 ? 0 : 1)] = MONTHS[day.getUTCMonth()];
    }
    lastCol = col;
  }

  const cols = Array.from({ length: lastCol + 1 }, (_, i) => i);
  const monthTicks = Object.keys(monthByCol).map(Number);

  // Square cells: fit the cell size to the available width but cap it so a short
  // window doesn't blow the cells up; the height is 7 weekday rows of that size,
  // and the chart width is sized to the grid so it stays tidy and left-aligned.
  const marginLeft = 28; // weekday letters
  const marginTop = 22; // month labels
  const cell = Math.min(28, Math.max(8, (width(el) - marginLeft) / cols.length));
  const plotWidth = marginLeft + cell * cols.length;

  const chart = Plot.plot({
    width: plotWidth,
    height: marginTop + cell * 7,
    marginLeft,
    marginTop,
    marginRight: 0,
    marginBottom: 0,
    padding: 0,
    style: { fontSize: LABEL_FONT_SIZE },
    x: {
      axis: "top",
      domain: cols,
      ticks: monthTicks,
      tickFormat: (c) => monthByCol[c] ?? "",
      tickSize: 0,
      label: null,
    },
    y: {
      domain: [0, 1, 2, 3, 4, 5, 6],
      tickFormat: (d) => "SMTWTFS"[d],
      tickSize: 0,
      label: null,
    },
    color: {
      type: "ordinal",
      domain: COUNT_BUCKETS,
      range: COUNT_COLORS,
      legend: true,
      label: "workouts",
    },
    marks: [
      Plot.cell(rows, {
        x: "col",
        y: "weekday",
        fill: (d) => bucketOf(d.count),
        inset: 1,
        rx: 2,
        title: (d) => `${d.iso}: ${d.count} workout${d.count === 1 ? "" : "s"}`,
      }),
    ],
  });

  // Outline each calendar month so the grid reads as a sequence of months, not
  // one undifferentiated ribbon of weeks.
  addMonthBorders(chart, rows, cell, marginLeft, marginTop, plotWidth);

  el.replaceChildren(chart);
}

function addDays(d, n) {
  return new Date(d.getTime() + n * MS_DAY);
}

// Draw a staircase border around each calendar month's cells, the way D3's
// classic "calendar view" does. Plot has no mark for this, but we sized the
// chart so its band positions are exactly `origin + index * cell`, so we can
// trace the outline in those same SVG coordinates and inject one <path> per
// month. A month within a single week-column is a contiguous run of weekdays,
// so we only need the min/max weekday per column to trace its boundary; clipped
// months at the window edges fall out for free since we read the actual cells.
function addMonthBorders(figure, rows, cell, ox, oy, plotWidth) {
  const SVG_NS = "http://www.w3.org/2000/svg";
  // `legend: true` makes Plot return a <figure> wrapping the legend and the
  // plot; the plot is the svg whose width matches the chart (legend swatches
  // are tiny). Guard the no-legend case where Plot returns the svg directly.
  const svgs = figure.tagName === "svg" ? [figure] : [...figure.querySelectorAll("svg")];
  const svg = svgs.find((s) => Math.round(+s.getAttribute("width")) === Math.round(plotWidth)) || svgs.at(-1);
  if (!svg) return;

  // "YYYY-MM" -> Map(column -> [minWeekday, maxWeekday]).
  const months = new Map();
  for (const r of rows) {
    const key = r.iso.slice(0, 7);
    let byCol = months.get(key);
    if (!byCol) months.set(key, (byCol = new Map()));
    const run = byCol.get(r.col);
    if (!run) byCol.set(r.col, [r.weekday, r.weekday]);
    else byCol.set(r.col, [Math.min(run[0], r.weekday), Math.max(run[1], r.weekday)]);
  }

  const xL = (c) => ox + c * cell;
  const xR = (c) => ox + (c + 1) * cell;
  const yT = (w) => oy + w * cell;
  const yB = (w) => oy + (w + 1) * cell;

  for (const byCol of months.values()) {
    const cols = [...byCol.keys()].sort((a, b) => a - b);
    const pts = [];
    // Top edge, left to right, stepping vertically where the run's top changes.
    for (let i = 0; i < cols.length; i++) {
      const top = byCol.get(cols[i])[0];
      if (i === 0) pts.push([xL(cols[i]), yT(top)]);
      pts.push([xR(cols[i]), yT(top)]);
      if (i < cols.length - 1) pts.push([xL(cols[i + 1]), yT(byCol.get(cols[i + 1])[0])]);
    }
    // Down the right edge, then the bottom edge back left, stepping again.
    const last = cols[cols.length - 1];
    pts.push([xR(last), yB(byCol.get(last)[1])]);
    for (let i = cols.length - 1; i >= 0; i--) {
      pts.push([xL(cols[i]), yB(byCol.get(cols[i])[1])]);
      if (i > 0) pts.push([xR(cols[i - 1]), yB(byCol.get(cols[i - 1])[1])]);
    }
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", "M" + pts.map(([x, y]) => `${x},${y}`).join("L") + "Z");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#2B2722"); // --ink
    path.setAttribute("stroke-width", "1.5");
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("pointer-events", "none");
    svg.appendChild(path);
  }
}
