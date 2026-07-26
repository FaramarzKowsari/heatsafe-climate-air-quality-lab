(() => {
  "use strict";
  const KEY="heatsafe-ventilation-planner-v1";
  const form=document.querySelector("#vent-form");
  const table=document.querySelector("#hour-table");
  const result=document.querySelector("#plan-result");
  const count=document.querySelector("#hour-count");
  const plannerStatus=document.querySelector("#planner-status");
  const locationPill=document.querySelector("#location-pill");
  const sourceSummary=document.querySelector("#source-summary");
  if(!form||!table)return;

  const thresholds={clean:12,moderate:35,high:55,usefulDelta:1.5,strongDelta:3,highHumidity:75,minimumWind:1};
  let state=load();

  function load(){try{const x=JSON.parse(localStorage.getItem(KEY)||"{}");return {home:x.home||{},hours:Array.isArray(x.hours)?x.hours.filter(valid):[],location:x.location||null,importedFrom:x.importedFrom||"",fetchedAt:x.fetchedAt||null};}catch{return {home:{},hours:[],location:null,importedFrom:"",fetchedAt:null};}}
  function valid(x){return x&&typeof x.id==="string"&&x.timestamp&&Number.isFinite(Number(x.outdoorTemp));}
  function save(){state.home=home();localStorage.setItem(KEY,JSON.stringify(state));}
  function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
  function num(v,d=1){return v===null||v===undefined||!Number.isFinite(Number(v))?"—":new Intl.NumberFormat("en-US",{maximumFractionDigits:d}).format(Number(v));}
  function optional(name){const v=form.elements[name].value;return v===""?null:Number(v);}
  function t(x){return new Date(x.timestamp).getTime();}
  function sorted(){return [...state.hours].sort((a,b)=>t(a)-t(b));}
  function home(){return {indoorTemp:Number(form.elements.indoorTemp.value),indoorHumidity:optional("indoorHumidity"),cross:form.elements.crossVentilation.value==="yes",purifier:form.elements.purifier.value==="yes",orientation:form.elements.orientation.value,constraints:form.elements.constraints.value.trim()};}
  function collectHour(){return {id:crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random()}`,timestamp:form.elements.timestamp.value,outdoorTemp:Number(form.elements.outdoorTemp.value),outdoorHumidity:optional("outdoorHumidity"),pm25:optional("pm25"),wind:optional("wind"),smoke:form.elements.smoke.value,solar:form.elements.solar.value,usAqi:null,euAqi:null,radiation:null,source:form.elements.source.value.trim()||"Manual entry"};}
  function validateHome(h){if(!Number.isFinite(h.indoorTemp)||h.indoorTemp<-20||h.indoorTemp>70)return "Indoor temperature must be between -20°C and 70°C.";return "";}
  function validateHour(x){if(!x.timestamp)return "Date and time are required.";if(x.outdoorTemp<-60||x.outdoorTemp>70)return "Outdoor temperature must be between -60°C and 70°C.";if(x.outdoorHumidity!==null&&(x.outdoorHumidity<0||x.outdoorHumidity>100))return "Humidity must be between 0% and 100%.";if(x.pm25!==null&&(x.pm25<0||x.pm25>2000))return "PM2.5 must be between 0 and 2,000 µg/m³.";if(x.wind!==null&&(x.wind<0||x.wind>300))return "Wind speed must be between 0 and 300 km/h.";return "";}
  function setNextHour(){const d=new Date();d.setMinutes(0,0,0);d.setHours(d.getHours()+1);d.setMinutes(d.getMinutes()-d.getTimezoneOffset());form.elements.timestamp.value=d.toISOString().slice(0,16);}

  function decision(h,x){
    const missing=[],reasons=[];let classification,confidence;
    const delta=h.indoorTemp-x.outdoorTemp;
    if(delta>=thresholds.strongDelta)reasons.push(`Outdoor air is ${delta.toFixed(1)}°C cooler than indoor air.`);
    else if(delta>=thresholds.usefulDelta)reasons.push(`Outdoor air is modestly cooler by ${delta.toFixed(1)}°C.`);
    else if(delta>0)reasons.push(`Outdoor air is only ${delta.toFixed(1)}°C cooler, so heat removal may be limited.`);
    else reasons.push(`Outdoor air is ${(-delta).toFixed(1)}°C warmer than indoor air.`);

    if(x.smoke==="likely"){classification="Less Favorable";confidence=x.pm25!==null?"High":"Moderate";reasons.push("A likely smoke context makes uncontrolled outdoor-air entry unfavorable.");}
    else if(x.pm25!==null&&x.pm25>=thresholds.high){classification="Less Favorable";confidence="High";reasons.push(`PM2.5 is elevated at ${x.pm25.toFixed(1)} µg/m³.`);}
    else if(delta<=0){classification="Less Favorable";confidence=x.pm25!==null?"High":"Moderate";}
    else if(x.pm25===null){classification="Conditional";confidence="Low";missing.push("PM2.5");reasons.push("No PM2.5 value is available, so outdoor-air quality cannot be assessed.");}
    else if(x.pm25<=thresholds.clean&&delta>=thresholds.usefulDelta){classification="More Favorable";confidence=x.smoke==="none"?"High":"Moderate";reasons.push(`PM2.5 is comparatively low at ${x.pm25.toFixed(1)} µg/m³.`);}
    else if(x.pm25<=thresholds.moderate&&delta>=thresholds.strongDelta){classification="Conditional";confidence="Moderate";reasons.push(`PM2.5 is not low (${x.pm25.toFixed(1)} µg/m³), but cooling potential is substantial.`);}
    else if(x.pm25<=thresholds.moderate){classification="Conditional";confidence="Moderate";reasons.push(`PM2.5 is ${x.pm25.toFixed(1)} µg/m³ and the temperature advantage is limited.`);}
    else{classification="Less Favorable";confidence="High";reasons.push(`PM2.5 is high enough (${x.pm25.toFixed(1)} µg/m³) to outweigh modest cooling potential.`);}

    if(x.smoke==="possible"){reasons.push("Possible smoke was entered, so local verification is important.");if(classification==="More Favorable"){classification="Conditional";confidence="Moderate";}}
    if(x.outdoorHumidity!==null&&x.outdoorHumidity>=thresholds.highHumidity){reasons.push(`Outdoor relative humidity is high at ${x.outdoorHumidity.toFixed(0)}%, reducing comfort benefit.`);if(classification==="More Favorable"){classification="Conditional";confidence="Moderate";}}
    if(x.wind!==null&&x.wind<thresholds.minimumWind){reasons.push("Wind is very weak, so natural air exchange may be slow.");if(classification==="More Favorable"&&!h.cross){classification="Conditional";confidence="Moderate";}}
    reasons.push(h.cross?"Cross-ventilation is available, which can improve air exchange when outdoor conditions are suitable.":"Only limited or single-sided ventilation is assumed.");
    if(h.purifier&&classification==="Conditional")reasons.push("An air purifier may help manage indoor particles after a short controlled ventilation period.");
    const hour=new Date(x.timestamp).getHours();
    if(x.solar==="high"&&hour>=11&&hour<=18)reasons.push("High daytime solar exposure may continue adding heat even while windows are open.");
    if(h.constraints)reasons.push("A user constraint was recorded and should be considered before acting.");
    if(String(x.source).includes("Open-Meteo"))reasons.push("This hour uses model-derived forecast data, not a local indoor or regulatory sensor.");
    return {classification,confidence,reasons,missing,delta};
  }

  function className(c){return c==="More Favorable"?"favorable":c==="Conditional"?"conditional":c==="Less Favorable"?"closed":"insufficient";}

  function renderTable(){
    const xs=sorted();count.textContent=`${xs.length} ${xs.length===1?"hour":"hours"}`;
    if(state.location){
      locationPill.hidden=false;
      locationPill.textContent=[state.location.name,state.location.country].filter(Boolean).join(", ");
      sourceSummary.textContent=`Imported from ${state.importedFrom||"live data"}${state.fetchedAt?` at ${new Date(state.fetchedAt).toLocaleString()}`:""}. Rows remain editable.`;
    } else {
      locationPill.hidden=true;
      sourceSummary.textContent="Add up to 72 hours manually or import live values.";
    }
    table.innerHTML=xs.length?xs.map(x=>`<tr><td>${esc(x.timestamp.replace("T"," "))}</td><td>${num(x.outdoorTemp)}°C</td><td>${x.outdoorHumidity===null?"—":`${num(x.outdoorHumidity,0)}%`}</td><td>${x.pm25===null?"—":num(x.pm25)}</td><td>${x.wind===null?"—":`${num(x.wind)} km/h`}</td><td>${esc(x.smoke)}</td><td>${esc(x.solar)}</td><td>${x.usAqi===null||x.usAqi===undefined?"—":num(x.usAqi,0)}</td><td>${esc(x.source)}</td><td class="no-print"><button class="danger del" data-id="${esc(x.id)}" style="min-height:36px;padding:6px 9px">Delete</button></td></tr>`).join(""):`<tr><td colspan="10"><div class="empty-state">No hourly values added. Load live conditions or add a manual hour.</div></td></tr>`;
  }

  function buildPlan(){
    const h=home(),err=validateHome(h);if(err){alert(err);return;}
    const xs=sorted();if(!xs.length){alert("Add, import or load at least one hourly value.");return;}
    save();
    const assessed=xs.map(x=>({...x,...decision(h,x)}));
    const favorable=assessed.filter(x=>x.classification==="More Favorable");
    const conditional=assessed.filter(x=>x.classification==="Conditional");
    const closed=assessed.filter(x=>x.classification==="Less Favorable");
    const top=[...favorable].sort((a,b)=>b.delta-a.delta).slice(0,3).map(x=>x.id);
    const sourceText=state.location?`Location: ${[state.location.name,state.location.admin1,state.location.country].filter(Boolean).join(", ")}. `:"";
    result.innerHTML=`
      <div class="result-summary"><span class="kicker">YOUR HOURLY PLAN</span><h2>${favorable.length} more favorable hour${favorable.length===1?"":"s"}</h2><p>${sourceText}${conditional.length} conditional and ${closed.length} less favorable hour${closed.length===1?"":"s"}.</p><div class="result-meta"><span>Indoor: ${num(h.indoorTemp)}°C</span><span>Cross-ventilation: ${h.cross?"yes":"limited"}</span><span>Hours assessed: ${assessed.length}</span></div></div>
      <div class="decision-grid">
        <article class="decision-card"><span class="classification favorable">More Favorable</span><h3>${favorable.length} hours</h3><p>Cooling potential and outdoor-air inputs support a more favorable classification.</p></article>
        <article class="decision-card"><span class="classification conditional">Conditional</span><h3>${conditional.length} hours</h3><p>Use shorter controlled periods and verify conditions locally.</p></article>
        <article class="decision-card"><span class="classification closed">Less Favorable</span><h3>${closed.length} hours</h3><p>Heat, PM2.5 or smoke inputs argue against opening windows.</p></article>
        <article class="decision-card"><span class="classification insufficient">Limitations</span><h3>Educational defaults</h3><p>Sensor placement, model resolution, forecast error and local official thresholds can change the real decision.</p></article>
      </div>
      <h2 style="margin-top:28px">Hour-by-hour reasons</h2>
      <div>${assessed.map(x=>`<article class="hour-card ${top.includes(x.id)?"best-window":""}"><div class="hour-time">${esc(x.timestamp.replace("T"," "))}${top.includes(x.id)?'<br><span class="small">Top cooling window</span>':""}</div><div><span class="classification ${className(x.classification)}">${x.classification}</span><div class="hour-values">Outdoor ${num(x.outdoorTemp)}°C · PM2.5 ${x.pm25===null?"unknown":num(x.pm25)} · Wind ${x.wind===null?"unknown":num(x.wind)+" km/h"}<br>Confidence: ${x.confidence}</div></div><div><ul class="decision-reasons">${x.reasons.map(r=>`<li>${esc(r)}</li>`).join("")}</ul></div></article>`).join("")}</div>
      <div class="source-box"><strong>Attribution:</strong> rows labelled Open-Meteo use weather data from Open-Meteo and air-quality forecasts from Open-Meteo/CAMS. Location search is based on GeoNames. Model grid cells and timestamps may differ from local sensors.</div>
      <div class="safety-box"><strong>Safety notice:</strong> educational decision support only. This is not an official warning service, medical advice or a substitute for local public-health and emergency guidance.</div>
      <div class="tool-actions no-print"><button class="ghost" type="button" id="print-plan">Print plan</button><button class="ghost" type="button" id="copy-summary">Copy summary</button></div>`;
    result.hidden=false;result.scrollIntoView({behavior:"smooth",block:"start"});
    result.querySelector("#print-plan")?.addEventListener("click",()=>window.print());
    result.querySelector("#copy-summary")?.addEventListener("click",async()=>{
      const text=assessed.map(x=>`${x.timestamp}: ${x.classification} (${x.confidence}) — ${x.reasons.join(" ")}`).join("\n");
      try{await navigator.clipboard.writeText(text);alert("Plan summary copied.");}catch{prompt("Copy this plan:",text);}
    });
  }

  function download(name,content,type){const b=new Blob([content],{type});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(u);}
  function csvEscape(v){return `"${String(v??"").replaceAll('"','""')}"`;}
  function exportCsv(){const h=["timestamp","outdoor_temp_c","outdoor_humidity_pct","pm25_ug_m3","wind_speed_kmh","smoke_context","solar_exposure","shortwave_radiation_w_m2","us_aqi","european_aqi","source"];const rows=sorted().map(x=>[x.timestamp,x.outdoorTemp,x.outdoorHumidity,x.pm25,x.wind,x.smoke,x.solar,x.radiation,x.usAqi,x.euAqi,x.source].map(csvEscape).join(","));download(`heatsafe-ventilation-hours-${new Date().toISOString().slice(0,10)}.csv`,[h.join(","),...rows].join("\n"),"text/csv;charset=utf-8");}
  function exportJson(){save();download(`heatsafe-ventilation-plan-${new Date().toISOString().slice(0,10)}.json`,JSON.stringify(state,null,2),"application/json");}
  function restoreHome(h){if(!h)return;const map={indoorTemp:"indoorTemp",indoorHumidity:"indoorHumidity",cross:"crossVentilation",purifier:"purifier",orientation:"orientation",constraints:"constraints"};Object.entries(h).forEach(([k,v])=>{const f=form.elements[map[k]];if(!f)return;if(k==="cross"||k==="purifier")f.value=v?"yes":"no";else if(v!==null&&v!==undefined)f.value=v;});}

  form.addEventListener("submit",e=>{e.preventDefault();if(!form.reportValidity())return;const h=home(),he=validateHome(h);if(he){alert(he);return;}const x=collectHour(),xe=validateHour(x);if(xe){alert(xe);return;}if(state.hours.length>=72){alert("This browser planner accepts up to 72 hourly rows.");return;}state.hours.push(x);save();const source=form.elements.source.value;form.elements.outdoorTemp.value="";form.elements.outdoorHumidity.value="";form.elements.pm25.value="";form.elements.wind.value="";form.elements.smoke.value="none";form.elements.solar.value="low";form.elements.source.value=source;const d=new Date(x.timestamp);d.setHours(d.getHours()+1);d.setMinutes(d.getMinutes()-d.getTimezoneOffset());form.elements.timestamp.value=d.toISOString().slice(0,16);renderTable();});
  document.querySelector("#reset-hour")?.addEventListener("click",()=>{form.elements.outdoorTemp.value="";form.elements.outdoorHumidity.value="";form.elements.pm25.value="";form.elements.wind.value="";form.elements.smoke.value="none";form.elements.solar.value="low";setNextHour();});
  document.querySelector("#build-plan")?.addEventListener("click",buildPlan);
  document.querySelector("#export-csv")?.addEventListener("click",exportCsv);
  document.querySelector("#export-json")?.addEventListener("click",exportJson);
  document.querySelector("#clear-hours")?.addEventListener("click",()=>{if(state.hours.length&&confirm("Delete all hourly values from this browser?")){state.hours=[];state.location=null;state.importedFrom="";state.fetchedAt=null;save();renderTable();result.hidden=true;}});
  table.addEventListener("click",e=>{const b=e.target.closest(".del");if(!b)return;state.hours=state.hours.filter(x=>x.id!==b.dataset.id);save();renderTable();});
  document.querySelector("#import-json")?.addEventListener("change",async e=>{const f=e.target.files?.[0];if(!f)return;try{const p=JSON.parse(await f.text());const xs=Array.isArray(p)?p:p.hours;if(!Array.isArray(xs))throw new Error("No hours array.");const clean=xs.filter(valid).slice(0,72);if(!clean.length)throw new Error("No valid hourly rows.");if(confirm(`Import ${clean.length} rows and replace current hourly data?`)){state.hours=clean;state.location=p.location||null;state.importedFrom=p.importedFrom||"JSON import";state.fetchedAt=p.fetchedAt||null;if(p.home)restoreHome(p.home);save();renderTable();}}catch(err){alert(`Import failed: ${err.message}`);}finally{e.target.value="";}});
  document.querySelector("#load-demo")?.addEventListener("click",()=>{
    if(state.hours.length&&!confirm("Replace current hours with a 24-hour demonstration dataset?"))return;
    form.elements.indoorTemp.value=29;form.elements.crossVentilation.value="yes";form.elements.purifier.value="yes";
    const base=new Date();base.setMinutes(0,0,0);const rows=[];
    for(let i=0;i<24;i++){const d=new Date(base.getTime()+i*3600000);const hour=d.getHours();const temp=23+9*Math.max(0,Math.sin((hour-7)/24*Math.PI*2));const pm=(hour>=18&&hour<=21)?26:8;rows.push({id:`demo-${i}`,timestamp:new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16),outdoorTemp:Number(temp.toFixed(1)),outdoorHumidity:hour<8?72:48,pm25:pm,wind:hour<6?0.5:6,smoke:"none",solar:hour>=11&&hour<=17?"high":hour>=8&&hour<=19?"medium":"low",radiation:null,usAqi:null,euAqi:null,source:"Synthetic demonstration"});}
    state.hours=rows;state.location=null;state.importedFrom="Synthetic demonstration";state.fetchedAt=new Date().toISOString();save();renderTable();buildPlan();
  });

  restoreHome(state.home);setNextHour();renderTable();
  if(new URLSearchParams(location.search).get("source")==="live" && state.hours.length){
    plannerStatus.textContent=`Loaded ${state.hours.length} live forecast rows. Review indoor temperature and smoke context, then build the plan.`;
    setTimeout(buildPlan,150);
  }
})();
