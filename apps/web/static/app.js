"use strict";
const $ = (selector) => {
    const element = document.querySelector(selector);
    if (!element)
        throw new Error(`Missing element: ${selector}`);
    return element;
};
const value = (form, name) => {
    const control = form.elements.namedItem(name);
    return control?.value ?? "";
};
const checked = (form, name) => {
    const control = form.elements.namedItem(name);
    return Boolean(control?.checked);
};
const numberValue = (form, name) => Number(value(form, name));
async function post(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok)
        throw new Error(body.detail ?? `Request failed: ${response.status}`);
    return body;
}
function escapeHtml(input) {
    return String(input)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
function list(items) {
    return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}
function errorCard(error) {
    return `<div class="error"><strong>Unable to calculate.</strong><p>${escapeHtml(error instanceof Error ? error.message : error)}</p></div>`;
}
function resultCard(title, body, tone = "neutral") {
    return `<article class="result-card ${tone}"><h3>${escapeHtml(title)}</h3>${body}</article>`;
}
// Tabs
for (const button of document.querySelectorAll(".tabs button")) {
    button.addEventListener("click", () => {
        for (const other of document.querySelectorAll(".tabs button"))
            other.classList.remove("active");
        for (const panel of document.querySelectorAll(".panel"))
            panel.classList.remove("active");
        button.classList.add("active");
        $(`#${button.dataset.tab}`).classList.add("active");
    });
}
const ventilationForm = $("#ventilation-form");
ventilationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const target = $("#ventilation-result");
    target.innerHTML = "<p>Evaluating…</p>";
    try {
        const result = await post("/api/v1/ventilation/decision", {
            indoor_temperature_c: numberValue(ventilationForm, "indoor"),
            outdoor_temperature_c: numberValue(ventilationForm, "outdoor"),
            pm25_ug_m3: numberValue(ventilationForm, "pm25"),
            outdoor_humidity_pct: numberValue(ventilationForm, "humidity"),
            wind_speed_kmh: numberValue(ventilationForm, "wind"),
            smoke_context: value(ventilationForm, "smoke"),
            cross_ventilation: checked(ventilationForm, "cross"),
            air_purifier_available: checked(ventilationForm, "purifier"),
        });
        const tone = result.decision === "Favorable Ventilation" ? "positive" : result.decision === "Keep Closed" ? "caution" : "conditional";
        target.innerHTML = resultCard(result.decision, `<p><strong>Confidence:</strong> ${escapeHtml(result.confidence)}</p>${list(result.reasons)}<p class="fine">${escapeHtml(result.safety_notice)}</p>`, tone);
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
const profileForm = $("#profile-form");
profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const target = $("#profile-result");
    target.innerHTML = "<p>Building profile…</p>";
    try {
        const result = await post("/api/v1/home/profile", {
            building_type: value(profileForm, "building_type"),
            floor_level: value(profileForm, "floor_level"),
            roof_exposure: value(profileForm, "roof_exposure"),
            window_orientation: value(profileForm, "window_orientation"),
            window_area: value(profileForm, "window_area"),
            external_shading: value(profileForm, "external_shading"),
            internal_shading: value(profileForm, "internal_shading"),
            insulation_context: value(profileForm, "insulation_context"),
            thermal_mass_context: value(profileForm, "thermal_mass_context"),
            cross_ventilation: checked(profileForm, "cross_ventilation"),
            single_sided_ventilation: checked(profileForm, "single_sided_ventilation"),
            internal_heat_sources: ["cooking", "computers"],
            occupancy: numberValue(profileForm, "occupancy"),
            cooling_equipment: ["portable fan"],
            outdoor_air_quality_concerns: checked(profileForm, "air_concern"),
        });
        target.innerHTML = [
            resultCard("Likely dominant pathway", `<p>${escapeHtml(result.likely_dominant_heat_pathway)}</p>`, "caution"),
            resultCard("Secondary pathway", `<p>${escapeHtml(result.secondary_heat_pathway)}</p>`),
            resultCard("Ventilation constraint", `<p>${escapeHtml(result.ventilation_limitation)}</p>`),
            resultCard("First investigations", list(result.suggested_low_risk_investigation), "positive"),
        ].join("");
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
const costForm = $("#cost-form");
costForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const target = $("#cost-result");
    target.innerHTML = "<p>Estimating…</p>";
    try {
        const result = await post("/api/v1/cooling/cost", {
            device_power_w: numberValue(costForm, "power"),
            estimated_duty_cycle: numberValue(costForm, "duty"),
            daily_runtime_hours: numberValue(costForm, "hours"),
            number_of_days: numberValue(costForm, "days"),
            electricity_price_per_kwh: numberValue(costForm, "price"),
            currency: value(costForm, "currency"),
            number_of_rooms: numberValue(costForm, "rooms"),
            cooling_strategy: value(costForm, "strategy"),
            fan_power_w: numberValue(costForm, "fan_power"),
            fan_runtime_hours: numberValue(costForm, "fan_hours"),
            fan_assisted_duty_cycle_reduction: numberValue(costForm, "fan_reduction"),
        });
        const currency = escapeHtml(result.currency);
        target.innerHTML = [
            resultCard("Low estimate", `<p class="metric">${currency} ${result.low.estimated_cost}</p><p>${result.low.energy_kwh} kWh</p>`, "positive"),
            resultCard("Central estimate", `<p class="metric">${currency} ${result.central.estimated_cost}</p><p>${result.central.energy_kwh} kWh</p>`, "conditional"),
            resultCard("High estimate", `<p class="metric">${currency} ${result.high.estimated_cost}</p><p>${result.high.energy_kwh} kWh</p>`, "caution"),
            resultCard("Assumptions", list(result.assumptions)),
        ].join("");
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
function syntheticClimateRecords() {
    const records = [];
    let seed = 17;
    const random = () => {
        seed = (seed * 9301 + 49297) % 233280;
        return seed / 233280;
    };
    for (let year = 1985; year <= 2025; year += 1) {
        for (let month = 1; month <= 12; month += 1) {
            const seasonal = 10 * Math.sin(((month - 1) / 12) * Math.PI * 2 - 1.2);
            const warming = (year - 1985) * 0.035;
            const noise = (random() - 0.5) * 2.4;
            const temperature = 15 + seasonal + warming + noise;
            records.push({
                timestamp: `${year}-${String(month).padStart(2, "0")}-15T12:00:00Z`,
                temperature_c: temperature,
                minimum_temperature_c: temperature - 5,
                maximum_temperature_c: temperature + 6,
                relative_humidity_pct: 55 + (random() - 0.5) * 20,
                source: "synthetic-demo",
                measurement_type: "synthetic",
            });
        }
    }
    return records;
}
function drawTrend(points) {
    const target = $("#trend-chart");
    const first = points[0];
    const last = points.at(-1);
    if (!first || !last) {
        target.innerHTML = "<p>No annual trend points available.</p>";
        return;
    }
    const width = 900;
    const height = 280;
    const values = points.map((point) => point.temperature_c);
    const min = Math.min(...values) - 0.5;
    const max = Math.max(...values) + 0.5;
    const path = points.map((point, index) => {
        const x = 30 + (index / Math.max(1, points.length - 1)) * (width - 60);
        const y = 20 + ((max - point.temperature_c) / (max - min)) * (height - 50);
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Synthetic annual mean temperature line chart"><path d="${path}" fill="none" stroke="currentColor" stroke-width="4"/><line x1="30" y1="${height - 30}" x2="${width - 30}" y2="${height - 30}" stroke="currentColor" opacity=".25"/><text x="30" y="${height - 8}">${first.year}</text><text x="${width - 70}" y="${height - 8}">${last.year}</text></svg>`;
}
$("#run-trend").addEventListener("click", async () => {
    const target = $("#trend-result");
    target.innerHTML = "<p>Analyzing synthetic data…</p>";
    try {
        const result = await post("/api/v1/climate/trend", { records: syntheticClimateRecords() });
        drawTrend(result.annual_means);
        target.innerHTML = [
            resultCard("OLS trend", `<p class="metric">${result.ols_slope_c_per_decade} °C / decade</p>`),
            resultCard("Theil–Sen trend", `<p class="metric">${result.theil_sen_slope_c_per_decade} °C / decade</p>`),
            resultCard("Bootstrap 95% interval", `<p>${result.bootstrap_ci_c_per_decade[0]} to ${result.bootstrap_ci_c_per_decade[1]} °C / decade</p>`),
            resultCard("Interpretation limits", list(result.warnings), "conditional"),
        ].join("");
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
const LOG_KEY = "heatsafe-seven-day-log-v1";
const readLog = () => JSON.parse(localStorage.getItem(LOG_KEY) ?? "[]");
const writeLog = (rows) => localStorage.setItem(LOG_KEY, JSON.stringify(rows));
function renderLog() {
    const rows = readLog();
    const target = $("#log-result");
    if (!rows.length) {
        target.innerHTML = "<p>No local records yet.</p>";
        return;
    }
    target.innerHTML = `<p><strong>${rows.length}</strong> local records. Latest: ${escapeHtml(rows.at(-1)?.timestamp)}</p>`;
}
const logForm = $("#log-form");
logForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const names = ["timestamp", "indoor_temperature_c", "indoor_humidity_pct", "outdoor_temperature_c", "pm25_ug_m3", "window_state", "fan_state", "cooling_state", "shade_state", "notes"];
    const row = {};
    for (const name of names)
        row[name] = value(logForm, name);
    const rows = readLog();
    rows.push(row);
    writeLog(rows.slice(-5000));
    logForm.reset();
    renderLog();
});
$("#export-log").addEventListener("click", () => {
    const rows = readLog();
    if (!rows.length)
        return;
    const first = rows[0];
    if (!first)
        return;
    const headers = Object.keys(first);
    const quote = (entry) => `"${entry.replaceAll('"', '""')}"`;
    const csv = [headers.join(","), ...rows.map((row) => headers.map((header) => quote(row[header] ?? "")).join(","))].join("\n");
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    anchor.download = "heatsafe-seven-day-log.csv";
    anchor.click();
    URL.revokeObjectURL(anchor.href);
});
$("#clear-log").addEventListener("click", () => {
    localStorage.removeItem(LOG_KEY);
    renderLog();
});
renderLog();
const plannerForm = document.querySelector("#planner-form");
plannerForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const target = $("#planner-result");
    const now = new Date();
    const baselinePm = numberValue(plannerForm, "pm25");
    const forecasts = Array.from({ length: 24 }, (_, hour) => {
        const timestamp = new Date(now.getTime() + hour * 3600_000);
        const localHour = timestamp.getHours();
        return {
            timestamp: timestamp.toISOString(),
            outdoor_temperature_c: 24 + 5 * Math.sin(((localHour - 8) / 24) * Math.PI * 2),
            outdoor_humidity_pct: 60,
            pm25_ug_m3: baselinePm + (hour >= 14 && hour <= 17 ? 28 : 0),
            wind_speed_kmh: 8,
            smoke_context: "none",
            solar_exposure: localHour >= 10 && localHour <= 17 ? "high" : "low",
        };
    });
    try {
        const result = await post("/api/v1/ventilation/plan", {
            indoor_temperature_c: numberValue(plannerForm, "indoor"),
            indoor_humidity_pct: numberValue(plannerForm, "humidity"),
            cross_ventilation: checked(plannerForm, "cross"),
            air_purifier_available: checked(plannerForm, "purifier"),
            window_orientation: "mixed",
            forecasts,
        });
        target.innerHTML = result.map((point) => resultCard(new Date(point.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), `<p><strong>${escapeHtml(point.classification)}</strong></p>${list(point.reasons)}`, point.classification === "More Favorable" ? "positive" : point.classification === "Less Favorable" ? "caution" : "conditional")).join("");
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
$("#run-comparator").addEventListener("click", async () => {
    const target = $("#comparator-result");
    const start = new Date();
    const records = Array.from({ length: 8 }, (_, hour) => ({
        timestamp: new Date(start.getTime() + hour * 3600_000).toISOString(),
        indoor_temperature_c: 30 - hour * 0.25,
        outdoor_temperature_c: 24 - hour * 0.1,
        indoor_humidity_pct: 55,
        outdoor_humidity_pct: 60,
        indoor_pm25_ug_m3: 10 + (hour > 2 ? 2 : 0),
        outdoor_pm25_ug_m3: 14,
        event: hour === 2 ? "Windows Opened" : null,
    }));
    try {
        const result = await post("/api/v1/compare/indoor-outdoor", { records });
        target.innerHTML = [
            resultCard("Thermal lag", `<p class="metric">${escapeHtml(result.estimated_thermal_lag_steps)} hours</p>`),
            resultCard("Indoor rate", `<p>${escapeHtml(result.indoor_temperature_rate_c_per_hour)} °C/hour</p>`),
            resultCard("Observations", list(result.observations), "conditional"),
            resultCard("Limitations", list(result.limitations)),
        ].join("");
    }
    catch (error) {
        target.innerHTML = errorCard(error);
    }
});
