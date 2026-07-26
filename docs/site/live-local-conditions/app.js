(() => {
  "use strict";

  const LOCATION_KEY = "heatsafe-live-location-v1";
  const DATA_KEY = "heatsafe-live-data-v1";
  const PLANNER_KEY = "heatsafe-ventilation-planner-v1";

  const searchInput = document.querySelector("#city-search");
  const searchButton = document.querySelector("#search-location");
  const locationButton = document.querySelector("#use-location");
  const results = document.querySelector("#location-results");
  const searchStatus = document.querySelector("#search-status");
  const loadButton = document.querySelector("#load-data");
  const loadStatus = document.querySelector("#load-status");
  const dashboardEmpty = document.querySelector("#dashboard-empty");
  const dashboardContent = document.querySelector("#dashboard-content");

  let selectedLocation = loadJson(LOCATION_KEY, null);
  let mergedData = loadJson(DATA_KEY, null);

  function loadJson(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || "null") ?? fallback; }
    catch { return fallback; }
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function num(value, digits = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(Number(value));
  }

  function status(element, message, kind = "normal", loading = false) {
    element.innerHTML = `${loading ? '<span class="spinner" aria-hidden="true"></span>' : ""}<span>${esc(message)}</span>`;
    element.className = `status-line ${kind === "error" ? "error-box" : kind === "success" ? "success-box" : ""}`;
  }

  function formatLocation(location) {
    return [location.name, location.admin1, location.country].filter(Boolean).join(", ");
  }

  function selectLocation(location, persist = true) {
    selectedLocation = {
      name: location.name || "Selected coordinates",
      admin1: location.admin1 || "",
      country: location.country || "",
      country_code: location.country_code || "",
      latitude: Number(location.latitude),
      longitude: Number(location.longitude),
      timezone: location.timezone || "auto",
      elevation: location.elevation ?? null,
      source: location.source || "Open-Meteo Geocoding"
    };
    if (persist) localStorage.setItem(LOCATION_KEY, JSON.stringify(selectedLocation));
    loadButton.disabled = false;
    renderSelectedResult();
    status(searchStatus, `Selected: ${formatLocation(selectedLocation)}`, "success");
  }

  function renderSelectedResult() {
    if (!selectedLocation) return;
    results.innerHTML = `
      <button type="button" class="location-option location-selected">
        <strong>${esc(formatLocation(selectedLocation))}</strong>
        <span>${num(selectedLocation.latitude, 4)}, ${num(selectedLocation.longitude, 4)} · ${esc(selectedLocation.timezone || "timezone auto")}</span>
      </button>`;
  }

  async function searchLocations() {
    const query = searchInput.value.trim();
    if (query.length < 2) {
      status(searchStatus, "Enter at least two characters.", "error");
      return;
    }
    searchButton.disabled = true;
    status(searchStatus, "Searching locations…", "normal", true);
    results.innerHTML = "";
    try {
      const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query)}&count=8&language=en&format=json`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Location service returned HTTP ${response.status}.`);
      const data = await response.json();
      const locations = Array.isArray(data.results) ? data.results : [];
      if (!locations.length) {
        status(searchStatus, "No matching locations were found.", "error");
        return;
      }
      status(searchStatus, `Choose one of ${locations.length} matching locations.`);
      results.innerHTML = locations.map((location, index) => `
        <button type="button" class="location-option" data-index="${index}">
          <strong>${esc(formatLocation(location))}</strong>
          <span>${num(location.latitude, 4)}, ${num(location.longitude, 4)} · ${esc(location.timezone || "timezone unavailable")}</span>
        </button>`).join("");
      results.querySelectorAll(".location-option").forEach((button) => {
        button.addEventListener("click", () => selectLocation(locations[Number(button.dataset.index)]));
      });
    } catch (error) {
      status(searchStatus, `Location search failed: ${error.message}`, "error");
    } finally {
      searchButton.disabled = false;
    }
  }

  function useDeviceLocation() {
    if (!navigator.geolocation) {
      status(searchStatus, "This browser does not provide geolocation. Search for a city instead.", "error");
      return;
    }
    locationButton.disabled = true;
    status(searchStatus, "Waiting for browser location permission…", "normal", true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        selectLocation({
          name: "Device location",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "auto",
          source: "Browser geolocation"
        });
        locationButton.disabled = false;
      },
      (error) => {
        status(searchStatus, `Location could not be used: ${error.message}. Search for a city instead.`, "error");
        locationButton.disabled = false;
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 600000 }
    );
  }

  function getArray(object, name) {
    return Array.isArray(object?.[name]) ? object[name] : [];
  }

  function mergeForecasts(weather, air, limit) {
    const weatherTimes = getArray(weather.hourly, "time");
    const airTimes = getArray(air.hourly, "time");
    const airIndex = new Map(airTimes.map((time, index) => [time, index]));
    const rows = [];

    for (let index = 0; index < weatherTimes.length && rows.length < limit; index++) {
      const time = weatherTimes[index];
      const aqIndex = airIndex.get(time);
      const radiation = getArray(weather.hourly, "shortwave_radiation")[index];
      rows.push({
        timestamp: time,
        outdoorTemp: getArray(weather.hourly, "temperature_2m")[index] ?? null,
        outdoorHumidity: getArray(weather.hourly, "relative_humidity_2m")[index] ?? null,
        wind: getArray(weather.hourly, "wind_speed_10m")[index] ?? null,
        radiation: radiation ?? null,
        solar: Number(radiation) >= 400 ? "high" : Number(radiation) >= 100 ? "medium" : "low",
        pm25: aqIndex === undefined ? null : getArray(air.hourly, "pm2_5")[aqIndex] ?? null,
        usAqi: aqIndex === undefined ? null : getArray(air.hourly, "us_aqi")[aqIndex] ?? null,
        euAqi: aqIndex === undefined ? null : getArray(air.hourly, "european_aqi")[aqIndex] ?? null,
        dust: aqIndex === undefined ? null : getArray(air.hourly, "dust")[aqIndex] ?? null
      });
    }

    return {
      fetchedAt: new Date().toISOString(),
      location: selectedLocation,
      timezone: weather.timezone || air.timezone || selectedLocation.timezone || "auto",
      timezoneAbbreviation: weather.timezone_abbreviation || air.timezone_abbreviation || "",
      weatherGrid: { latitude: weather.latitude, longitude: weather.longitude, elevation: weather.elevation },
      airGrid: { latitude: air.latitude, longitude: air.longitude, elevation: air.elevation },
      current: {
        temperature: weather.current?.temperature_2m ?? rows[0]?.outdoorTemp ?? null,
        humidity: weather.current?.relative_humidity_2m ?? rows[0]?.outdoorHumidity ?? null,
        wind: weather.current?.wind_speed_10m ?? rows[0]?.wind ?? null,
        pm25: air.current?.pm2_5 ?? rows[0]?.pm25 ?? null,
        usAqi: air.current?.us_aqi ?? rows[0]?.usAqi ?? null,
        euAqi: air.current?.european_aqi ?? rows[0]?.euAqi ?? null,
        dust: air.current?.dust ?? rows[0]?.dust ?? null,
        weatherTime: weather.current?.time ?? rows[0]?.timestamp ?? null,
        airTime: air.current?.time ?? rows[0]?.timestamp ?? null
      },
      rows
    };
  }

  async function loadForecast() {
    if (!selectedLocation) return;
    const hours = Number(document.querySelector("#hours").value);
    loadButton.disabled = true;
    status(loadStatus, "Loading weather and air-quality forecasts…", "normal", true);

    const lat = encodeURIComponent(selectedLocation.latitude);
    const lon = encodeURIComponent(selectedLocation.longitude);
    const weatherUrl =
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,relative_humidity_2m,wind_speed_10m` +
      `&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation` +
      `&forecast_hours=${hours}&timezone=auto`;
    const airUrl =
      `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}` +
      `&current=pm2_5,us_aqi,european_aqi,dust` +
      `&hourly=pm2_5,us_aqi,european_aqi,dust` +
      `&forecast_hours=${hours}&timezone=auto`;

    try {
      const [weatherResponse, airResponse] = await Promise.all([fetch(weatherUrl), fetch(airUrl)]);
      if (!weatherResponse.ok) throw new Error(`Weather service returned HTTP ${weatherResponse.status}.`);
      if (!airResponse.ok) throw new Error(`Air-quality service returned HTTP ${airResponse.status}.`);
      const [weather, air] = await Promise.all([weatherResponse.json(), airResponse.json()]);
      if (weather.error) throw new Error(weather.reason || "Weather API error.");
      if (air.error) throw new Error(air.reason || "Air-quality API error.");

      mergedData = mergeForecasts(weather, air, hours);
      if (!mergedData.rows.length) throw new Error("No matching hourly rows were returned.");
      localStorage.setItem(DATA_KEY, JSON.stringify(mergedData));
      renderDashboard();
      status(loadStatus, `Loaded ${mergedData.rows.length} hourly rows.`, "success");
    } catch (error) {
      status(loadStatus, `Live data could not be loaded: ${error.message} The manual planner is still available.`, "error");
    } finally {
      loadButton.disabled = false;
    }
  }

  function aqiClass(aqi) {
    if (!Number.isFinite(Number(aqi))) return "";
    if (Number(aqi) <= 50) return "aqi-good";
    if (Number(aqi) <= 100) return "aqi-moderate";
    return "aqi-poor";
  }

  function buildChart(rows) {
    const data = rows.slice(0, Math.min(48, rows.length));
    if (!data.length) return "";
    const width = 920, height = 350;
    const p = { left: 58, right: 58, top: 24, bottom: 64 };
    const temps = data.map((row) => Number(row.outdoorTemp)).filter(Number.isFinite);
    const pms = data.map((row) => Number(row.pm25)).filter(Number.isFinite);
    let tMin = Math.floor(Math.min(...temps) - 1), tMax = Math.ceil(Math.max(...temps) + 1);
    if (tMin === tMax) { tMin--; tMax++; }
    const pmMax = Math.max(20, Math.ceil((Math.max(...pms, 0) + 5) / 10) * 10);

    const x = (index) => p.left + index * (width - p.left - p.right) / Math.max(1, data.length - 1);
    const yTemp = (value) => p.top + (tMax - value) * (height - p.top - p.bottom) / (tMax - tMin);
    const yPm = (value) => p.top + (pmMax - value) * (height - p.top - p.bottom) / pmMax;

    let grid = "";
    const tStep = Math.max(1, Math.ceil((tMax - tMin) / 6));
    for (let value = tMin; value <= tMax; value += tStep) {
      grid += `<line x1="${p.left}" y1="${yTemp(value)}" x2="${width-p.right}" y2="${yTemp(value)}" stroke="#dbe8ea"/>
      <text x="${p.left-9}" y="${yTemp(value)+4}" text-anchor="end" font-size="12" fill="#5d7278">${value}°</text>`;
    }

    const tempPoints = data.map((row, index) => `${x(index)},${yTemp(Number(row.outdoorTemp))}`).join(" ");
    const pmSegments = [];
    let current = [];
    data.forEach((row, index) => {
      if (Number.isFinite(Number(row.pm25))) current.push(`${x(index)},${yPm(Number(row.pm25))}`);
      else if (current.length) { pmSegments.push(current.join(" ")); current = []; }
    });
    if (current.length) pmSegments.push(current.join(" "));

    const labelStep = Math.max(1, Math.ceil(data.length / 8));
    const labels = data.map((row, index) => {
      if (index % labelStep !== 0 && index !== data.length - 1) return "";
      const label = row.timestamp.slice(5).replace("T", " ");
      return `<text x="${x(index)}" y="${height-28}" transform="rotate(-35 ${x(index)} ${height-28})" text-anchor="end" font-size="11" fill="#5d7278">${esc(label)}</text>`;
    }).join("");

    return `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">
      ${grid}
      <text x="${width-p.right+8}" y="${p.top+4}" font-size="12" fill="#725bb6">PM2.5</text>
      <text x="${width-p.right+8}" y="${yPm(pmMax)+4}" font-size="11" fill="#725bb6">${pmMax}</text>
      <text x="${width-p.right+8}" y="${yPm(0)+4}" font-size="11" fill="#725bb6">0</text>
      <polyline fill="none" stroke="#087a95" stroke-width="4" points="${tempPoints}"/>
      ${pmSegments.map((points) => `<polyline fill="none" stroke="#725bb6" stroke-width="3" points="${points}"/>`).join("")}
      ${labels}
    </svg>`;
  }

  function renderDashboard() {
    if (!mergedData?.rows?.length) {
      dashboardEmpty.hidden = false;
      dashboardContent.hidden = true;
      return;
    }
    dashboardEmpty.hidden = true;
    dashboardContent.hidden = false;

    document.querySelector("#location-title").textContent = formatLocation(mergedData.location);
    document.querySelector("#location-meta").textContent =
      `${num(mergedData.location.latitude, 4)}, ${num(mergedData.location.longitude, 4)} · ` +
      `${mergedData.timezone}${mergedData.timezoneAbbreviation ? ` (${mergedData.timezoneAbbreviation})` : ""} · ` +
      `Fetched ${new Date(mergedData.fetchedAt).toLocaleString()}`;

    const current = mergedData.current;
    document.querySelector("#current-grid").innerHTML = `
      <article class="current-card"><span>Outdoor temperature</span><strong>${num(current.temperature)}°C</strong><span>${esc(current.weatherTime || "model time unavailable")}</span></article>
      <article class="current-card"><span>Relative humidity</span><strong>${num(current.humidity, 0)}%</strong><span>Model-derived</span></article>
      <article class="current-card"><span>Wind speed</span><strong>${num(current.wind)} km/h</strong><span>10 m wind</span></article>
      <article class="current-card"><span>PM2.5</span><strong>${num(current.pm25)} µg/m³</strong><span>${esc(current.airTime || "model time unavailable")}</span></article>
      <article class="current-card ${aqiClass(current.usAqi)}"><span>U.S. AQI</span><strong>${num(current.usAqi, 0)}</strong><span>Consolidated model AQI</span></article>`;

    document.querySelector("#live-chart").innerHTML = buildChart(mergedData.rows);
    document.querySelector("#live-table").innerHTML = mergedData.rows.map((row) => `
      <tr><td>${esc(row.timestamp)}</td><td>${num(row.outdoorTemp)}°C</td>
      <td>${num(row.outdoorHumidity,0)}%</td><td>${num(row.wind)} km/h</td>
      <td>${num(row.radiation,0)} W/m²</td><td>${num(row.pm25)} µg/m³</td>
      <td>${num(row.usAqi,0)}</td><td>${num(row.euAqi,0)}</td><td>${num(row.dust)} µg/m³</td></tr>`).join("");

    const temps = mergedData.rows.map((row) => Number(row.outdoorTemp)).filter(Number.isFinite);
    const pms = mergedData.rows.map((row) => Number(row.pm25)).filter(Number.isFinite);
    const coolest = mergedData.rows.reduce((best, row) =>
      Number(row.outdoorTemp) < Number(best.outdoorTemp) ? row : best, mergedData.rows[0]);
    const warmest = mergedData.rows.reduce((best, row) =>
      Number(row.outdoorTemp) > Number(best.outdoorTemp) ? row : best, mergedData.rows[0]);
    const lowestPm = mergedData.rows.filter((row) => Number.isFinite(Number(row.pm25)))
      .sort((a,b) => Number(a.pm25) - Number(b.pm25))[0];

    document.querySelector("#live-insights").innerHTML = `
      <article class="insight"><strong>Coolest loaded hour</strong>${esc(coolest.timestamp)} · ${num(coolest.outdoorTemp)}°C.</article>
      <article class="insight"><strong>Warmest loaded hour</strong>${esc(warmest.timestamp)} · ${num(warmest.outdoorTemp)}°C.</article>
      <article class="insight"><strong>Lowest modeled PM2.5</strong>${lowestPm ? `${esc(lowestPm.timestamp)} · ${num(lowestPm.pm25)} µg/m³.` : "PM2.5 was not returned."}</article>
      <article class="insight"><strong>Loaded ranges</strong>Temperature ${num(Math.min(...temps))}–${num(Math.max(...temps))}°C; PM2.5 ${pms.length ? `${num(Math.min(...pms))}–${num(Math.max(...pms))} µg/m³` : "unavailable"}.</article>`;
  }

  function plannerState() {
    const smoke = document.querySelector("#smoke-override").value;
    const indoor = Number(document.querySelector("#indoor-temp").value);
    const cross = document.querySelector("#cross-vent").value === "yes";
    return {
      home: {
        indoorTemp: Number.isFinite(indoor) ? indoor : 29,
        indoorHumidity: null,
        cross,
        purifier: false,
        orientation: "mixed",
        constraints: ""
      },
      location: mergedData.location,
      importedFrom: "HeatSafe Live Local Conditions",
      fetchedAt: mergedData.fetchedAt,
      hours: mergedData.rows.slice(0, 72).map((row, index) => ({
        id: `live-${Date.now()}-${index}`,
        timestamp: row.timestamp,
        outdoorTemp: row.outdoorTemp,
        outdoorHumidity: row.outdoorHumidity,
        pm25: row.pm25,
        wind: row.wind,
        smoke,
        solar: row.solar,
        radiation: row.radiation,
        usAqi: row.usAqi,
        euAqi: row.euAqi,
        source: "Open-Meteo weather + CAMS air-quality forecast"
      }))
    };
  }

  function sendToPlanner() {
    if (!mergedData?.rows?.length) return;
    const indoor = Number(document.querySelector("#indoor-temp").value);
    if (!Number.isFinite(indoor) || indoor < -20 || indoor > 70) {
      status(loadStatus, "Enter a valid indoor temperature between -20°C and 70°C before sending.", "error");
      return;
    }
    localStorage.setItem(PLANNER_KEY, JSON.stringify(plannerState()));
    window.location.href = "../home-ventilation-planner/?source=live";
  }

  function download(name, content, type) {
    const blob = new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = name;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    URL.revokeObjectURL(url);
  }

  function csvEscape(value) {
    return `"${String(value ?? "").replaceAll('"', '""')}"`;
  }

  function exportCsv() {
    const headers = ["timestamp","temperature_2m_c","relative_humidity_2m_pct","wind_speed_10m_kmh","shortwave_radiation_w_m2","pm2_5_ug_m3","us_aqi","european_aqi","dust_ug_m3"];
    const rows = mergedData.rows.map((row) => [
      row.timestamp,row.outdoorTemp,row.outdoorHumidity,row.wind,row.radiation,row.pm25,row.usAqi,row.euAqi,row.dust
    ].map(csvEscape).join(","));
    download(`heatsafe-live-${new Date().toISOString().slice(0,10)}.csv`, [headers.join(","), ...rows].join("\n"), "text/csv;charset=utf-8");
  }

  searchButton.addEventListener("click", searchLocations);
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); searchLocations(); }
  });
  locationButton.addEventListener("click", useDeviceLocation);
  loadButton.addEventListener("click", loadForecast);
  document.querySelector("#open-manual").addEventListener("click", () => { window.location.href = "../home-ventilation-planner/"; });
  document.querySelector("#send-planner").addEventListener("click", sendToPlanner);
  document.querySelector("#export-json").addEventListener("click", () =>
    download(`heatsafe-live-${new Date().toISOString().slice(0,10)}.json`, JSON.stringify(mergedData, null, 2), "application/json"));
  document.querySelector("#export-csv").addEventListener("click", exportCsv);
  document.querySelector("#print-dashboard").addEventListener("click", () => window.print());

  if (selectedLocation) {
    loadButton.disabled = false;
    renderSelectedResult();
    status(searchStatus, `Restored: ${formatLocation(selectedLocation)}`, "success");
  }
  if (mergedData?.rows?.length) renderDashboard();
})();
