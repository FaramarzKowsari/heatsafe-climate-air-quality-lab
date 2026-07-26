(() => {
  "use strict";

  const STORAGE_KEY = "heatsafe-24-hour-plan-v1";
  const LOG_KEY = "heatsafe-seven-day-log-v1";
  const CHECK_KEY = "heatsafe-24-hour-checks-v1";

  const form = document.querySelector("#plan-form");
  const result = document.querySelector("#plan-result");
  const copyButton = document.querySelector("#copy-plan");
  const printButton = document.querySelector("#print-plan");
  const status = document.querySelector("#plan-save-status");

  if (!form || !result) return;

  let lastSummary = "";

  function stringValue(name) {
    return String(form.elements[name]?.value || "");
  }

  function numberValue(name, fallback = null) {
    const raw = form.elements[name]?.value;
    if (raw === "" || raw === undefined) return fallback;
    const value = Number(raw);
    return Number.isFinite(value) ? value : fallback;
  }

  function collect() {
    return {
      planDate: stringValue("planDate"),
      homeLabel: stringValue("homeLabel").trim(),
      currentIndoor: numberValue("currentIndoor"),
      humidity: numberValue("humidity"),
      heatStorage: stringValue("heatStorage"),
      vulnerable: stringValue("vulnerable"),
      dayHigh: numberValue("dayHigh"),
      nightLow: numberValue("nightLow"),
      airQuality: stringValue("airQuality"),
      pm25: numberValue("pm25"),
      sunExposure: stringValue("sunExposure"),
      nightNoiseSafety: stringValue("nightNoiseSafety"),
      externalShade: stringValue("externalShade"),
      crossVentilation: stringValue("crossVentilation"),
      fan: stringValue("fan"),
      cooling: stringValue("cooling"),
      purifier: stringValue("purifier"),
      coolRoom: stringValue("coolRoom"),
      wakeTime: stringValue("wakeTime"),
      sleepTime: stringValue("sleepTime"),
      notes: stringValue("notes").trim()
    };
  }

  function validate(data) {
    if (!data.planDate) return "Plan date is required.";
    if (!Number.isFinite(data.currentIndoor) || data.currentIndoor < -20 || data.currentIndoor > 70) return "Current indoor temperature must be between -20°C and 70°C.";
    if (!Number.isFinite(data.dayHigh) || data.dayHigh < -30 || data.dayHigh > 70) return "Expected outdoor high must be between -30°C and 70°C.";
    if (!Number.isFinite(data.nightLow) || data.nightLow < -40 || data.nightLow > 60) return "Expected overnight low must be between -40°C and 60°C.";
    if (data.humidity !== null && (data.humidity < 0 || data.humidity > 100)) return "Humidity must be between 0% and 100%.";
    if (data.pm25 !== null && (data.pm25 < 0 || data.pm25 > 2000)) return "PM2.5 must be between 0 and 2,000 µg/m³.";
    return "";
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  }

  function action(text, category = "general") {
    return { text, category };
  }

  function buildPlan(data) {
    const canVentilateAir = data.airQuality === "acceptable";
    const airUncertain = data.airQuality === "uncertain";
    const nightCoolingPotential = data.nightLow < data.currentIndoor - 1;
    const strongNightCooling = data.nightLow < data.currentIndoor - 4;
    const hotDay = data.dayHigh >= 30;
    const veryHotDay = data.dayHigh >= 35;
    const humid = data.humidity !== null && data.humidity >= 60;
    const highStorage = data.heatStorage === "high";
    const shadeStronglyNeeded = data.sunExposure === "high";
    const canNightOpen = data.nightNoiseSafety !== "no";
    const hasCross = data.crossVentilation !== "no";

    const blocks = [];

    const early = [];
    if (canVentilateAir && nightCoolingPotential && canNightOpen) {
      early.push(action(`Use the early-morning cool period for ${hasCross ? "cross-ventilation" : "controlled window ventilation"} before outdoor temperatures rise.`, "cool"));
      if (strongNightCooling) early.push(action("Open interior doors along a safe airflow path so stored heat can leave more than one room.", "cool"));
    } else if (!canVentilateAir) {
      early.push(action("Keep windows closed because outdoor air was entered as poor or smoky; use filtered indoor air and mechanical cooling where available.", "clean"));
    } else if (airUncertain) {
      early.push(action("Check a trusted local air-quality source before opening windows. Use a short, supervised ventilation test only if outdoor air is acceptable.", "caution"));
    } else {
      early.push(action("Outdoor night cooling appears limited; avoid a long flush that could add heat.", "caution"));
    }
    early.push(action("Record the starting indoor temperature and close the ventilation phase before the outdoor air becomes warmer than the home.", "general"));
    blocks.push({ time: `Wake period · ${data.wakeTime}`, title: "Use the coolest available window", status: canVentilateAir && nightCoolingPotential ? "Cooling opportunity" : "Conditional start", statusClass: canVentilateAir && nightCoolingPotential ? "status-cool" : "status-caution", actions: early });

    const morning = [];
    if (data.externalShade === "yes") morning.push(action("Deploy external shade before direct sun reaches the glass.", "shade"));
    else if (data.externalShade === "partial") morning.push(action("Use all available external shade early and close interior solar-control layers before direct sun enters.", "shade"));
    else morning.push(action("Close interior blinds or curtains before strong sun; note that exterior shade is usually more effective than interior fabric alone.", "shade"));
    morning.push(action("Move cooking, laundry and other heat-producing tasks to a cooler time where practical.", "general"));
    if (data.coolRoom === "yes") morning.push(action("Prepare the cooler priority room: water, fan, charger, medication plan and clean-air equipment if needed.", "general"));
    blocks.push({ time: "08:00–11:00", title: "Prevent heat before it enters", status: "Solar control", statusClass: "status-shade", actions: morning });

    const midday = [];
    midday.push(action("Keep sun-exposed windows shaded and avoid reopening them simply because the room feels stuffy.", "shade"));
    if (data.fan === "yes") midday.push(action(humid ? "Use a fan for air movement, while recognizing that high humidity can reduce perceived cooling." : "Use a fan across the occupied zone rather than directing it into an empty room.", "cool"));
    if (data.cooling === "ac") midday.push(action("Use air conditioning or heat-pump cooling in the priority zone with doors and windows positioned to avoid wasting cooled air.", "cool"));
    else if (data.cooling === "evaporative") midday.push(action(humid ? "Evaporative cooling may be less effective under the entered humidity; monitor the room rather than assuming performance." : "Use evaporative cooling only with the ventilation pattern required by the equipment and local humidity.", "cool"));
    else if (data.cooling === "portable") midday.push(action("Use the portable cooling device in one closed priority zone and manage its exhaust or heat rejection correctly.", "cool"));
    else midday.push(action("Without mechanical cooling, reduce internal heat, occupy the coolest zone and follow local heat guidance closely.", "caution"));
    if (veryHotDay || data.vulnerable === "yes") midday.push(action("Increase check-ins and use official cooling locations or local assistance if the home cannot remain safely usable.", "caution"));
    blocks.push({ time: "11:00–16:00", title: "Defend the home during peak heat", status: veryHotDay ? "High-heat period" : "Daytime protection", statusClass: veryHotDay ? "status-caution" : "status-shade", actions: midday });

    const late = [];
    late.push(action("Do not assume outdoor air is cooler yet. Compare outdoor and indoor conditions before changing window position.", "general"));
    if (shadeStronglyNeeded) late.push(action("Keep west- and southwest-facing windows shaded through late afternoon.", "shade"));
    if (highStorage) late.push(action("Expect walls, ceilings and furniture to release stored heat after the outdoor peak; maintain the priority room rather than ending cooling too early.", "caution"));
    blocks.push({ time: "16:00–19:00", title: "Manage delayed heat and west sun", status: highStorage ? "Stored-heat phase" : "Transition phase", statusClass: highStorage ? "status-caution" : "status-shade", actions: late });

    const evening = [];
    if (canVentilateAir && nightCoolingPotential && canNightOpen) {
      evening.push(action("Begin ventilation only after outdoor air is cooler than the indoor space you want to cool.", "cool"));
      evening.push(action(hasCross ? "Create a defined inlet and outlet path; use a fan to support the path if needed." : "Use one-sided ventilation in shorter controlled periods and observe whether indoor temperature actually falls.", "cool"));
    } else if (!canVentilateAir) {
      evening.push(action("Keep the clean-air boundary closed. Run the purifier in the priority room if available.", "clean"));
      if (data.purifier !== "yes") evening.push(action("Minimize particle-generating indoor activities and follow local smoke guidance.", "clean"));
    } else {
      evening.push(action("Check outdoor temperature and air quality before ventilating; the entered conditions do not support an automatic open-window recommendation.", "caution"));
    }
    blocks.push({ time: "19:00–22:00", title: "Choose the evening transition deliberately", status: canVentilateAir && nightCoolingPotential ? "Potential ventilation window" : "Conditional ventilation", statusClass: canVentilateAir && nightCoolingPotential ? "status-cool" : "status-caution", actions: evening });

    const sleep = [];
    sleep.push(action("Prioritize the coolest usable sleeping location and reduce unnecessary bedding, lighting and electronics.", "general"));
    if (data.fan === "yes") sleep.push(action("Place the fan to move air across the sleeping zone without creating a trip or electrical hazard.", "cool"));
    if (data.cooling !== "none") sleep.push(action("Use a stable nighttime cooling setting that protects sleep rather than repeatedly allowing the room to reheat.", "cool"));
    if (data.airQuality === "poor" && data.purifier === "yes") sleep.push(action("Keep the purifier operating in the sleeping or priority room with windows closed.", "clean"));
    if (data.vulnerable === "yes") sleep.push(action("Arrange an overnight check-in or contingency plan and follow official advice for vulnerable occupants.", "caution"));
    blocks.push({ time: `Sleep period · ${data.sleepTime}`, title: "Protect sleep and overnight recovery", status: "Night resilience", statusClass: "status-clean", actions: sleep });

    const overnight = [];
    if (canVentilateAir && strongNightCooling && canNightOpen) overnight.push(action("If safe, continue controlled night flushing and close openings before outdoor air warms or conditions worsen.", "cool"));
    else if (canVentilateAir && nightCoolingPotential && data.nightNoiseSafety === "limited") overnight.push(action("Use short supervised ventilation periods rather than leaving openings unattended.", "cool"));
    else overnight.push(action("Maintain the best available cooled or clean-air zone; reassess before sunrise.", "general"));
    overnight.push(action("Record the overnight low indoor temperature in the Seven-Day Heat Log to see whether the home recovered.", "general"));
    blocks.push({ time: "Overnight–next morning", title: "Measure whether the home recovered", status: "Recovery check", statusClass: "status-cool", actions: overnight });

    const checklist = [
      "Check official heat and air-quality information",
      "Fill drinking water and essential supplies",
      "Prepare the coolest priority room",
      "Deploy shade before direct sun",
      "Reduce cooking and internal heat",
      "Charge phone and backup power",
      "Check on higher-risk occupants",
      "Record morning and evening indoor temperatures"
    ];

    if (data.airQuality === "poor") checklist.push("Confirm clean-air room and purifier setup");
    if (data.notes) checklist.push(`Personal priority: ${data.notes}`);

    return { blocks, checklist };
  }

  function render(data, plan) {
    const label = data.homeLabel ? ` for ${esc(data.homeLabel)}` : "";
    const airText = data.airQuality === "acceptable" ? "Outdoor air entered as acceptable" : data.airQuality === "poor" ? "Outdoor air entered as poor/smoky" : "Outdoor air quality uncertain";
    const pmText = data.pm25 === null ? "PM2.5 not entered" : `PM2.5 entered: ${data.pm25} µg/m³`;

    const blocksHtml = plan.blocks.map((block) => `
      <article class="plan-block">
        <div class="plan-time">${esc(block.time)}</div>
        <div>
          <span class="plan-status ${block.statusClass}">${esc(block.status)}</span>
          <h3>${esc(block.title)}</h3>
          <ul>${block.actions.map((item) => `<li>${esc(item.text)}</li>`).join("")}</ul>
        </div>
      </article>`).join("");

    const savedChecks = loadChecks(data.planDate);
    const checklistHtml = plan.checklist.map((item, index) => `
      <label class="check-item"><input type="checkbox" class="plan-check" data-index="${index}" ${savedChecks.includes(index) ? "checked" : ""}><span>${esc(item)}</span></label>`).join("");

    result.innerHTML = `
      <div class="result-summary">
        <span class="kicker">YOUR MANUAL 24-HOUR PLAN</span>
        <h2>HeatSafe plan${label} · ${esc(data.planDate)}</h2>
        <p>Built from your entered home conditions and weather assumptions. It does not claim to be a live forecast.</p>
        <div class="result-meta"><span>Indoor now: ${data.currentIndoor}°C</span><span>Expected high: ${data.dayHigh}°C</span><span>Expected low: ${data.nightLow}°C</span></div>
      </div>

      <div class="plan-meta-grid">
        <article class="plan-meta"><strong>Night cooling potential</strong><br>${data.nightLow < data.currentIndoor - 1 ? "Present in the entered temperatures" : "Limited in the entered temperatures"}</article>
        <article class="plan-meta"><strong>Air-quality input</strong><br>${airText}<br><span class="small">${pmText}</span></article>
        <article class="plan-meta"><strong>Home heat storage</strong><br>${esc(data.heatStorage)}<br><span class="small">Based on your selection</span></article>
      </div>

      <div class="plan-timeline">${blocksHtml}</div>

      <h2 style="margin-top:30px">Preparation checklist</h2>
      <p class="small">Checklist progress is stored locally for this plan date.</p>
      <div class="action-checklist">${checklistHtml}</div>

      <div class="safety-box"><strong>Escalation:</strong> when the home cannot remain usable, follow official local warnings, use designated cooling or clean-air locations, and seek urgent assistance for signs of heat illness.</div>`;

    lastSummary = [
      `HeatSafe 24-Hour Plan${data.homeLabel ? ` — ${data.homeLabel}` : ""}`,
      `Date: ${data.planDate}`,
      `Indoor now: ${data.currentIndoor}°C; expected outdoor high: ${data.dayHigh}°C; overnight low: ${data.nightLow}°C.`,
      ...plan.blocks.flatMap((block) => [`${block.time} — ${block.title}`, ...block.actions.map((item) => `• ${item.text}`)]),
      "Educational plan only. Follow official local heat, smoke and emergency guidance."
    ].join("\n");

    result.hidden = false;
    copyButton.hidden = false;
    printButton.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "start" });

    result.querySelectorAll(".plan-check").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        const checked = [...result.querySelectorAll(".plan-check:checked")].map((box) => Number(box.dataset.index));
        saveChecks(data.planDate, checked);
      });
    });
  }

  function loadChecks(date) {
    try {
      const all = JSON.parse(localStorage.getItem(CHECK_KEY) || "{}");
      return Array.isArray(all[date]) ? all[date] : [];
    } catch {
      return [];
    }
  }

  function saveChecks(date, checked) {
    let all = {};
    try { all = JSON.parse(localStorage.getItem(CHECK_KEY) || "{}"); } catch { all = {}; }
    all[date] = checked;
    localStorage.setItem(CHECK_KEY, JSON.stringify(all));
  }

  function setDefaults() {
    form.elements.planDate.value = new Date().toISOString().slice(0, 10);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = collect();
    const error = validate(data);
    if (error) { window.alert(error); return; }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    status.textContent = "Your plan assumptions were saved only in this browser.";
    render(data, buildPlan(data));
  });

  document.querySelector("#reset-plan")?.addEventListener("click", () => {
    form.reset();
    setDefaults();
    localStorage.removeItem(STORAGE_KEY);
    result.hidden = true;
    result.innerHTML = "";
    copyButton.hidden = true;
    printButton.hidden = true;
    status.textContent = "No plan assumptions are currently saved.";
  });

  document.querySelector("#print-plan")?.addEventListener("click", () => window.print());

  document.querySelector("#copy-plan")?.addEventListener("click", async () => {
    if (!lastSummary) return;
    try {
      await navigator.clipboard.writeText(lastSummary);
      copyButton.textContent = "Copied";
      setTimeout(() => { copyButton.textContent = "Copy summary"; }, 1600);
    } catch {
      window.prompt("Copy this plan:", lastSummary);
    }
  });

  document.querySelector("#use-latest-log")?.addEventListener("click", () => {
    try {
      const entries = JSON.parse(localStorage.getItem(LOG_KEY) || "[]");
      if (!Array.isArray(entries) || !entries.length) {
        window.alert("No HeatSafe log observations were found in this browser.");
        return;
      }
      const latest = [...entries]
        .filter((entry) => entry && entry.date && entry.time)
        .sort((a, b) => new Date(`${b.date}T${b.time}:00`) - new Date(`${a.date}T${a.time}:00`))[0];

      if (Number.isFinite(Number(latest.indoorTemp))) form.elements.currentIndoor.value = latest.indoorTemp;
      if (Number.isFinite(Number(latest.humidity))) form.elements.humidity.value = latest.humidity;
      if (Number.isFinite(Number(latest.pm25))) form.elements.pm25.value = latest.pm25;
      if (latest.date) form.elements.planDate.value = latest.date;
      status.textContent = `Latest Heat Log entry from ${latest.date} ${latest.time} was loaded. Review all forecast assumptions before building the plan.`;
    } catch {
      window.alert("The saved Heat Log could not be read.");
    }
  });

  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const data = JSON.parse(saved);
      Object.entries(data).forEach(([name, value]) => {
        const field = form.elements[name];
        if (field && value !== null) field.value = value;
      });
      status.textContent = "Saved plan assumptions from this browser were restored.";
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      setDefaults();
    }
  } else {
    setDefaults();
  }
})();
