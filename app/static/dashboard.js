const panelRoot = document.querySelector("#dashboard-panels");
const refreshButton = document.querySelector("#refresh-button");
const systemMessage = document.querySelector("#system-message");
const seriesColors = ["#45c5ff", "#f7b955", "#ef6f8d"];
let refreshTimer;

function svgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function formatValue(value, unit) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (unit === "usd") return `$${number.toFixed(number < 0.01 ? 6 : 2)}`;
  if (unit === "percent") return `${number.toFixed(2)}%`;
  if (unit === "score_0_to_1") return number.toFixed(3);
  if (unit === "ms") return `${number.toLocaleString(undefined, { maximumFractionDigits: 1 })} ms`;
  return number.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function createChart(panel) {
  const width = 680;
  const height = 220;
  const pad = { top: 30, right: 16, bottom: 28, left: 48 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const threshold = Number(panel.threshold.value);
  const values = panel.series.flatMap((series) => series.values.map((point) => Number(point.value)));
  const maxValue = Math.max(1, threshold, ...values);
  const svg = svgElement("svg", {
    class: "chart",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `${panel.title}. ${panel.threshold.label}.`,
  });

  [0, 0.5, 1].forEach((ratio) => {
    const y = pad.top + plotHeight * ratio;
    svg.appendChild(svgElement("line", {
      class: "grid-line",
      x1: pad.left,
      x2: width - pad.right,
      y1: y,
      y2: y,
    }));
    const label = svgElement("text", { x: 4, y: y + 4 });
    label.textContent = formatValue(maxValue * (1 - ratio), panel.unit);
    svg.appendChild(label);
  });

  const thresholdY = pad.top + plotHeight - (Math.min(threshold, maxValue) / maxValue) * plotHeight;
  svg.appendChild(svgElement("line", {
    class: "threshold-line",
    x1: pad.left,
    x2: width - pad.right,
    y1: thresholdY,
    y2: thresholdY,
  }));
  const thresholdLabel = svgElement("text", {
    x: width - pad.right,
    y: Math.max(12, thresholdY - 7),
    "text-anchor": "end",
  });
  thresholdLabel.textContent = "threshold";
  svg.appendChild(thresholdLabel);

  panel.series.forEach((series, seriesIndex) => {
    const color = seriesColors[seriesIndex % seriesColors.length];
    const lastIndex = Math.max(1, series.values.length - 1);
    const points = series.values.map((point, index) => {
      const x = pad.left + (index / lastIndex) * plotWidth;
      const y = pad.top + plotHeight - (Number(point.value) / maxValue) * plotHeight;
      return { ...point, x, y };
    });
    svg.appendChild(svgElement("polyline", {
      class: "series-line",
      stroke: color,
      points: points.map((point) => `${point.x},${point.y}`).join(" "),
    }));

    points.filter((point) => Number(point.value) !== 0).forEach((point) => {
      const circle = svgElement("circle", {
        class: "data-point",
        cx: point.x,
        cy: point.y,
        r: 4,
        fill: color,
        tabindex: "0",
        role: "img",
        "aria-label": `${series.name}, ${point.label}: ${formatValue(point.value, panel.unit)}`,
      });
      const title = svgElement("title");
      title.textContent = `${series.name} · ${point.label} · ${formatValue(point.value, panel.unit)}`;
      circle.appendChild(title);
      svg.appendChild(circle);
    });
  });

  const fromLabel = svgElement("text", { x: pad.left, y: height - 6 });
  fromLabel.textContent = "−60 min";
  svg.appendChild(fromLabel);
  const nowLabel = svgElement("text", { x: width - pad.right, y: height - 6, "text-anchor": "end" });
  nowLabel.textContent = "now";
  svg.appendChild(nowLabel);
  return svg;
}

function createPanel(panel, index) {
  const article = document.createElement("article");
  article.className = `panel${panel.healthy ? "" : " is-breached"}`;
  article.setAttribute("aria-labelledby", `panel-title-${panel.id}`);

  const header = document.createElement("header");
  header.className = "panel-header";
  header.innerHTML = `
    <div>
      <p class="panel-index">Panel ${String(index + 1).padStart(2, "0")} · ${panel.unit}</p>
      <h2 id="panel-title-${panel.id}">${panel.title}</h2>
    </div>
    <span class="health-label">${panel.healthy ? "Within threshold" : "Threshold breached"}</span>
  `;
  article.appendChild(header);

  const metricRow = document.createElement("div");
  metricRow.className = "metric-row";
  panel.metrics.forEach((metric) => {
    const item = document.createElement("div");
    item.className = `metric${metric.tone === "primary" ? " is-primary" : ""}`;
    item.innerHTML = `
      <span class="metric-label">${metric.label}</span>
      <strong class="metric-value">${formatValue(metric.value, metric.unit || panel.unit)}</strong>
    `;
    metricRow.appendChild(item);
  });
  article.appendChild(metricRow);

  const chartWrap = document.createElement("div");
  chartWrap.className = "chart-wrap";
  chartWrap.appendChild(createChart(panel));
  article.appendChild(chartWrap);

  const legend = document.createElement("ul");
  legend.className = "chart-legend";
  panel.series.forEach((series, seriesIndex) => {
    const item = document.createElement("li");
    item.style.setProperty("--legend-color", seriesColors[seriesIndex % seriesColors.length]);
    item.textContent = series.name;
    legend.appendChild(item);
  });
  const thresholdItem = document.createElement("li");
  thresholdItem.style.setProperty("--legend-color", "#f7b955");
  thresholdItem.textContent = panel.threshold.label;
  legend.appendChild(thresholdItem);
  article.appendChild(legend);

  if (panel.breakdown) {
    const breakdown = document.createElement("div");
    breakdown.className = "breakdown";
    breakdown.setAttribute("aria-label", "Error breakdown");
    Object.entries(panel.breakdown).forEach(([name, count]) => {
      const item = document.createElement("span");
      item.textContent = `${name}: ${count}`;
      breakdown.appendChild(item);
    });
    article.appendChild(breakdown);
  }

  const details = document.createElement("details");
  details.className = "panel-details";
  details.innerHTML = `
    <summary>View accessible data summary</summary>
    <table class="detail-table">
      <thead><tr><th scope="col">Measure</th><th scope="col">Value</th></tr></thead>
      <tbody>
        ${panel.metrics.map((metric) => `
          <tr><th scope="row">${metric.label}</th><td>${formatValue(metric.value, metric.unit || panel.unit)}</td></tr>
        `).join("")}
        <tr><th scope="row">Threshold</th><td>${panel.threshold.label}</td></tr>
      </tbody>
    </table>
  `;
  article.appendChild(details);
  return article;
}

function renderSlo(slo) {
  const achieved = Math.max(0, Math.min(100, Number(slo.achieved_percent)));
  document.querySelector("#slo-achieved").textContent = `${achieved.toFixed(2)}%`;
  document.querySelector("#slo-target").textContent = `${Number(slo.target_percent).toFixed(1)}%`;
  document.querySelector("#slo-summary").textContent =
    `${slo.good_requests} of ${slo.total_requests} requests met the 3,000 ms objective.`;
  document.querySelector("#budget-copy").textContent =
    `${slo.remaining_bad_requests} bad requests remain in this window's proportional error budget.`;
  const meter = document.querySelector("#slo-meter");
  meter.setAttribute("aria-valuenow", achieved.toFixed(2));
  document.querySelector("#slo-fill").style.width = `${achieved}%`;
}

function renderDashboard(payload) {
  panelRoot.replaceChildren(...payload.panels.map(createPanel));
  renderSlo(payload.slo);
  document.querySelector("#window-value").textContent = `${payload.meta.time_range_minutes} min`;
  document.querySelector("#refresh-interval").textContent = payload.meta.refresh_seconds;
  document.querySelector("#generated-at").dateTime = payload.meta.generated_at;
  document.querySelector("#generated-at").textContent = new Date(payload.meta.generated_at).toLocaleTimeString();
  const liveState = document.querySelector("#live-state");
  liveState.classList.add("is-live");
  liveState.lastChild.textContent = " Live data";

  if (!payload.meta.has_data) {
    systemMessage.hidden = false;
    systemMessage.textContent =
      "No log records were found in the last 60 minutes. Send requests to POST /chat; this view will refresh automatically.";
  } else {
    systemMessage.hidden = true;
  }

  window.clearInterval(refreshTimer);
  refreshTimer = window.setInterval(loadDashboard, payload.meta.refresh_seconds * 1000);
}

async function loadDashboard() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Refreshing…";
  try {
    const response = await fetch("/dashboard/data", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderDashboard(await response.json());
  } catch (error) {
    systemMessage.hidden = false;
    systemMessage.textContent = `Dashboard data could not be loaded (${error.message}). Check the API and retry.`;
    document.querySelector("#live-state").classList.remove("is-live");
    document.querySelector("#live-state").lastChild.textContent = " Disconnected";
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh data";
  }
}

refreshButton.addEventListener("click", loadDashboard);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadDashboard();
});
loadDashboard();
