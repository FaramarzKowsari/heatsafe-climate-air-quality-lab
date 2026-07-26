(() => {
  "use strict";

  const STORAGE_KEY = "heatsafe-seven-day-log-v1";
  const form = document.querySelector("#log-form");
  const tableBody = document.querySelector("#log-table-body");
  const dashboardEmpty = document.querySelector("#dashboard-empty");
  const dashboardContent = document.querySelector("#dashboard-content");
  const metrics = document.querySelector("#metrics");
  const chartContainer = document.querySelector("#temperature-chart");
  const insights = document.querySelector("#insights");
  const countPill = document.querySelector("#entry-count-pill");
  const rangePill = document.querySelector("#date-range-pill");

  if (!form || !tableBody) return;

  let entries = loadEntries();

  function loadEntries() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter(validEntry) : [];
    } catch {
      return [];
    }
  }

  function validEntry(item) {
    return item && typeof item.id === "string" && typeof item.date === "string" &&
      typeof item.time === "string" && Number.isFinite(Number(item.indoorTemp));
  }

  function saveEntries() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }

  function isoStamp(entry) {
    return new Date(`${entry.date}T${entry.time}:00`).getTime();
  }

  function sortedEntries() {
    return [...entries].sort((a, b) => isoStamp(a) - isoStamp(b));
  }

  function latestSevenDays() {
    const sorted = sortedEntries();
    if (!sorted.length) return [];
    const latest = isoStamp(sorted[sorted.length - 1]);
    const start = latest - (7 * 24 * 60 * 60 * 1000);
    return sorted.filter((entry) => isoStamp(entry) >= start && isoStamp(entry) <= latest);
  }

  function setDefaults() {
    const now = new Date();
    form.elements.date.value = now.toISOString().slice(0, 10);
    form.elements.time.value = now.toTimeString().slice(0, 5);
  }

  function optionalNumber(name) {
    const raw = form.elements[name].value;
    return raw === "" ? null : Number(raw);
  }

  function collectEntry() {
    return {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      date: form.elements.date.value,
      time: form.elements.time.value,
      room: form.elements.room.value.trim(),
      indoorTemp: Number(form.elements.indoorTemp.value),
      outdoorTemp: optionalNumber("outdoorTemp"),
      humidity: optionalNumber("humidity"),
      pm25: optionalNumber("pm25"),
      comfort: form.elements.comfort.value,
      occupancy: optionalNumber("occupancy"),
      windows: form.elements.windows.value,
      shade: form.elements.shade.value,
      fan: form.elements.fan.value,
      cooling: form.elements.cooling.value,
      purifier: form.elements.purifier.value,
      activity: form.elements.activity.value,
      notes: form.elements.notes.value.trim()
    };
  }

  function validateEntry(entry) {
    if (!entry.date || !entry.time) return "Date and time are required.";
    if (!Number.isFinite(entry.indoorTemp) || entry.indoorTemp < -30 || entry.indoorTemp > 70) {
      return "Indoor temperature must be between -30°C and 70°C.";
    }
    if (entry.outdoorTemp !== null && (!Number.isFinite(entry.outdoorTemp) || entry.outdoorTemp < -60 || entry.outdoorTemp > 70)) {
      return "Outdoor temperature must be between -60°C and 70°C.";
    }
    if (entry.humidity !== null && (!Number.isFinite(entry.humidity) || entry.humidity < 0 || entry.humidity > 100)) {
      return "Humidity must be between 0% and 100%.";
    }
    if (entry.pm25 !== null && (!Number.isFinite(entry.pm25) || entry.pm25 < 0 || entry.pm25 > 2000)) {
      return "PM2.5 must be between 0 and 2,000 µg/m³.";
    }
    return "";
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function formatNumber(value, digits = 1) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(Number(value));
  }

  function average(values) {
    const nums = values.filter((v) => Number.isFinite(Number(v))).map(Number);
    return nums.length ? nums.reduce((sum, value) => sum + value, 0) / nums.length : null;
  }

  function renderTable() {
    const rows = [...entries].sort((a, b) => isoStamp(b) - isoStamp(a));
    tableBody.innerHTML = rows.map((entry) => `
      <tr>
        <td>${esc(entry.date)}<br><span class="small">${esc(entry.time)}</span></td>
        <td>${esc(entry.room || "—")}</td>
        <td>${formatNumber(entry.indoorTemp)}°C</td>
        <td>${entry.outdoorTemp === null ? "—" : `${formatNumber(entry.outdoorTemp)}°C`}</td>
        <td>${entry.humidity === null ? "—" : `${formatNumber(entry.humidity, 0)}%`}</td>
        <td>${esc(entry.windows)}</td>
        <td>${esc(entry.shade)}</td>
        <td>${esc(entry.fan)}</td>
        <td>${esc(entry.cooling)}</td>
        <td>${esc(entry.notes || "—")}</td>
        <td class="no-print"><button type="button" class="danger delete-entry" data-id="${esc(entry.id)}" style="min-height:36px;padding:6px 10px">Delete</button></td>
      </tr>`).join("");

    if (!rows.length) {
      tableBody.innerHTML = `<tr><td colspan="11"><div class="empty-state">No observations stored yet.</div></td></tr>`;
    }
  }

  function buildChart(data) {
    if (!data.length) return "";
    const width = 900;
    const height = 330;
    const pad = { left: 58, right: 24, top: 24, bottom: 58 };
    const temps = data.flatMap((entry) => [entry.indoorTemp, entry.outdoorTemp]).filter((v) => Number.isFinite(Number(v))).map(Number);
    let min = Math.floor(Math.min(...temps) - 1);
    let max = Math.ceil(Math.max(...temps) + 1);
    if (min === max) { min -= 1; max += 1; }

    const x = (index) => pad.left + (index * (width - pad.left - pad.right) / Math.max(1, data.length - 1));
    const y = (temp) => pad.top + ((max - temp) * (height - pad.top - pad.bottom) / (max - min));

    const indoorPoints = data.map((entry, i) => `${x(i)},${y(Number(entry.indoorTemp))}`).join(" ");
    const outdoorSegments = [];
    let current = [];
    data.forEach((entry, i) => {
      if (Number.isFinite(Number(entry.outdoorTemp))) {
        current.push(`${x(i)},${y(Number(entry.outdoorTemp))}`);
      } else if (current.length) {
        outdoorSegments.push(current.join(" "));
        current = [];
      }
    });
    if (current.length) outdoorSegments.push(current.join(" "));

    const grid = [];
    for (let tick = min; tick <= max; tick += Math.max(1, Math.ceil((max - min) / 6))) {
      grid.push(`<line x1="${pad.left}" y1="${y(tick)}" x2="${width - pad.right}" y2="${y(tick)}" stroke="#dbe8ea" stroke-width="1"/>
        <text x="${pad.left - 10}" y="${y(tick) + 4}" text-anchor="end" font-size="12" fill="#5d7278">${tick}°</text>`);
    }

    const labelStep = Math.max(1, Math.ceil(data.length / 7));
    const labels = data.map((entry, i) => {
      if (i % labelStep !== 0 && i !== data.length - 1) return "";
      const label = `${entry.date.slice(5)} ${entry.time}`;
      return `<text x="${x(i)}" y="${height - 26}" transform="rotate(-35 ${x(i)} ${height - 26})" text-anchor="end" font-size="11" fill="#5d7278">${esc(label)}</text>`;
    }).join("");

    const indoorDots = data.map((entry, i) => `<circle cx="${x(i)}" cy="${y(Number(entry.indoorTemp))}" r="4" fill="#087a95"><title>${entry.date} ${entry.time}: Indoor ${entry.indoorTemp}°C</title></circle>`).join("");
    const outdoorDots = data.map((entry, i) => Number.isFinite(Number(entry.outdoorTemp)) ? `<circle cx="${x(i)}" cy="${y(Number(entry.outdoorTemp))}" r="3.5" fill="#e76e38"><title>${entry.date} ${entry.time}: Outdoor ${entry.outdoorTemp}°C</title></circle>` : "").join("");

    return `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">
      ${grid.join("")}
      <polyline fill="none" stroke="#087a95" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" points="${indoorPoints}"/>
      ${outdoorSegments.map((points) => `<polyline fill="none" stroke="#e76e38" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="${points}"/>`).join("")}
      ${indoorDots}${outdoorDots}${labels}
    </svg>`;
  }

  function generateInsights(data) {
    const sorted = [...data].sort((a, b) => isoStamp(a) - isoStamp(b));
    const indoor = sorted.map((e) => Number(e.indoorTemp));
    const maxEntry = sorted.reduce((best, e) => Number(e.indoorTemp) > Number(best.indoorTemp) ? e : best, sorted[0]);
    const minEntry = sorted.reduce((best, e) => Number(e.indoorTemp) < Number(best.indoorTemp) ? e : best, sorted[0]);
    const withOutdoor = sorted.filter((e) => Number.isFinite(Number(e.outdoorTemp)));
    const gaps = withOutdoor.map((e) => Number(e.indoorTemp) - Number(e.outdoorTemp));
    const avgGap = average(gaps);
    const openEntries = sorted.filter((e) => e.windows !== "closed");
    const coolingEntries = sorted.filter((e) => e.cooling !== "off");
    const humidEntries = sorted.filter((e) => Number(e.humidity) >= 60);

    const cards = [
      { title: "Hottest observation", body: `${formatNumber(maxEntry.indoorTemp)}°C on ${maxEntry.date} at ${maxEntry.time}${maxEntry.room ? ` in ${esc(maxEntry.room)}` : ""}.` },
      { title: "Coolest observation", body: `${formatNumber(minEntry.indoorTemp)}°C on ${minEntry.date} at ${minEntry.time}.` },
      { title: "Indoor–outdoor gap", body: avgGap === null ? "Not enough outdoor-temperature entries." : `Average indoor minus outdoor difference: ${formatNumber(avgGap)}°C.` },
      { title: "Action context", body: `${openEntries.length} entries with windows open or partly open; ${coolingEntries.length} with active cooling or fan-only cooling mode.` }
    ];

    if (humidEntries.length) {
      cards.push({ title: "Humidity pattern", body: `${humidEntries.length} entries recorded humidity at or above 60%. Interpret this with local conditions and actual measurements.` });
    }

    return cards.map((card) => `<article class="insight"><strong>${card.title}</strong><span>${card.body}</span></article>`).join("");
  }

  function renderDashboard() {
    renderTable();
    const data = latestSevenDays();
    countPill.textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"}`;

    if (!data.length) {
      dashboardEmpty.hidden = false;
      dashboardContent.hidden = true;
      rangePill.textContent = "No date range";
      return;
    }

    dashboardEmpty.hidden = true;
    dashboardContent.hidden = false;
    rangePill.textContent = `${data[0].date} → ${data[data.length - 1].date}`;

    const avgIndoor = average(data.map((e) => e.indoorTemp));
    const avgHumidity = average(data.map((e) => e.humidity));
    const maxIndoor = Math.max(...data.map((e) => Number(e.indoorTemp)));
    const minIndoor = Math.min(...data.map((e) => Number(e.indoorTemp)));

    metrics.innerHTML = `
      <article class="metric"><span class="metric-label">Average indoor</span><strong>${formatNumber(avgIndoor)}°C</strong><span class="metric-note">${data.length} observations in range</span></article>
      <article class="metric"><span class="metric-label">Highest indoor</span><strong>${formatNumber(maxIndoor)}°C</strong><span class="metric-note">Observed maximum</span></article>
      <article class="metric"><span class="metric-label">Lowest indoor</span><strong>${formatNumber(minIndoor)}°C</strong><span class="metric-note">Observed minimum</span></article>
      <article class="metric"><span class="metric-label">Average humidity</span><strong>${avgHumidity === null ? "—" : `${formatNumber(avgHumidity, 0)}%`}</strong><span class="metric-note">Where humidity was recorded</span></article>`;

    chartContainer.innerHTML = buildChart(data);
    insights.innerHTML = generateInsights(data);
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function csvEscape(value) {
    const text = value === null || value === undefined ? "" : String(value);
    return `"${text.replaceAll('"', '""')}"`;
  }

  function exportCsv() {
    const headers = ["date","time","room","indoor_temp_c","outdoor_temp_c","humidity_percent","pm25_ug_m3","comfort","occupancy","windows","shade","fan","cooling","purifier","activity","notes"];
    const rows = sortedEntries().map((e) => [
      e.date,e.time,e.room,e.indoorTemp,e.outdoorTemp,e.humidity,e.pm25,e.comfort,e.occupancy,e.windows,e.shade,e.fan,e.cooling,e.purifier,e.activity,e.notes
    ].map(csvEscape).join(","));
    download(`heatsafe-home-heat-log-${new Date().toISOString().slice(0,10)}.csv`, [headers.join(","), ...rows].join("\n"), "text/csv;charset=utf-8");
  }

  function exportJson() {
    download(`heatsafe-home-heat-log-${new Date().toISOString().slice(0,10)}.json`, JSON.stringify({ schema: "heatsafe-seven-day-log-v1", exportedAt: new Date().toISOString(), entries: sortedEntries() }, null, 2), "application/json");
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const entry = collectEntry();
    const error = validateEntry(entry);
    if (error) { window.alert(error); return; }
    entries.push(entry);
    saveEntries();
    const date = form.elements.date.value;
    const time = form.elements.time.value;
    form.reset();
    setDefaults();
    form.elements.date.value = date;
    form.elements.time.value = time;
    renderDashboard();
  });

  document.querySelector("#reset-form")?.addEventListener("click", () => {
    form.reset();
    setDefaults();
  });

  document.querySelector("#print-log")?.addEventListener("click", () => window.print());
  document.querySelector("#export-csv")?.addEventListener("click", exportCsv);
  document.querySelector("#export-json")?.addEventListener("click", exportJson);

  document.querySelector("#clear-all")?.addEventListener("click", () => {
    if (!entries.length) return;
    if (window.confirm("Delete all stored HeatSafe log observations from this browser?")) {
      entries = [];
      saveEntries();
      renderDashboard();
    }
  });

  tableBody.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-entry");
    if (!button) return;
    const id = button.dataset.id;
    entries = entries.filter((entry) => entry.id !== id);
    saveEntries();
    renderDashboard();
  });

  document.querySelector("#import-json")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      const imported = Array.isArray(parsed) ? parsed : parsed.entries;
      if (!Array.isArray(imported)) throw new Error("No entries array found.");
      const clean = imported.filter(validEntry);
      if (!clean.length) throw new Error("No valid observations found.");
      if (!window.confirm(`Import ${clean.length} valid observations and replace the current local log?`)) return;
      entries = clean;
      saveEntries();
      renderDashboard();
    } catch (error) {
      window.alert(`Could not import the file: ${error.message}`);
    } finally {
      event.target.value = "";
    }
  });

  setDefaults();
  renderDashboard();
})();
