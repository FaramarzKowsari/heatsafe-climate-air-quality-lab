(() => {
  "use strict";
  const KEY = "heatsafe-indoor-outdoor-comparator-v1";
  const form = document.querySelector("#compare-form");
  const body = document.querySelector("#table-body");
  const empty = document.querySelector("#empty-state");
  const analysis = document.querySelector("#analysis");
  const metrics = document.querySelector("#metrics");
  const chart = document.querySelector("#chart");
  const insights = document.querySelector("#insights");
  const eventAnalysis = document.querySelector("#event-analysis");
  const countPill = document.querySelector("#count-pill");
  const rangePill = document.querySelector("#range-pill");
  if (!form || !body) return;

  let entries = load();

  const eventLabels = {
    "none":"No new action","windows-opened":"Windows opened","windows-closed":"Windows closed",
    "shade-closed":"Shade closed","shade-opened":"Shade opened","fan-started":"Fan started",
    "fan-stopped":"Fan stopped","cooling-started":"Cooling started","cooling-stopped":"Cooling stopped",
    "purifier-started":"Purifier started","cooking-started":"Cooking started",
    "occupancy-changed":"Occupancy changed","other":"Other"
  };

  function load() {
    try {
      const data = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(data) ? data.filter(valid) : [];
    } catch { return []; }
  }
  function valid(e) {
    return e && typeof e.id === "string" && e.timestamp &&
      Number.isFinite(Number(e.indoorTemp)) && Number.isFinite(Number(e.outdoorTemp));
  }
  function save() { localStorage.setItem(KEY, JSON.stringify(entries)); }
  function t(e) { return new Date(e.timestamp).getTime(); }
  function sorted() { return [...entries].sort((a,b)=>t(a)-t(b)); }
  function esc(v) { return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;"); }
  function num(v,d=1) { return v===null||v===undefined||!Number.isFinite(Number(v)) ? "—" : new Intl.NumberFormat("en-US",{maximumFractionDigits:d}).format(Number(v)); }
  function avg(xs) { const n=xs.filter(x=>Number.isFinite(Number(x))).map(Number); return n.length?n.reduce((a,b)=>a+b,0)/n.length:null; }
  function median(xs) { const n=xs.filter(x=>Number.isFinite(Number(x))).map(Number).sort((a,b)=>a-b); if(!n.length)return null; const m=Math.floor(n.length/2); return n.length%2?n[m]:(n[m-1]+n[m])/2; }
  function optional(name) { const v=form.elements[name].value; return v===""?null:Number(v); }

  function setNow() {
    const d = new Date(Date.now()-new Date().getTimezoneOffset()*60000);
    form.elements.timestamp.value = d.toISOString().slice(0,16);
  }

  function collect() {
    return {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      timestamp: form.elements.timestamp.value,
      room: form.elements.room.value.trim(),
      event: form.elements.event.value,
      indoorTemp: Number(form.elements.indoorTemp.value),
      outdoorTemp: Number(form.elements.outdoorTemp.value),
      humidity: optional("humidity"), outdoorHumidity: optional("outdoorHumidity"), pm25: optional("pm25"),
      windows: form.elements.windows.value, shade: form.elements.shade.value,
      fan: form.elements.fan.value, cooling: form.elements.cooling.value,
      purifier: form.elements.purifier.value, notes: form.elements.notes.value.trim()
    };
  }
  function validate(e) {
    if(!e.timestamp) return "Date and time are required.";
    if(e.indoorTemp < -30 || e.indoorTemp > 70) return "Indoor temperature must be between -30°C and 70°C.";
    if(e.outdoorTemp < -60 || e.outdoorTemp > 70) return "Outdoor temperature must be between -60°C and 70°C.";
    if(e.humidity!==null && (e.humidity<0||e.humidity>100)) return "Indoor humidity must be between 0% and 100%.";
    if(e.outdoorHumidity!==null && (e.outdoorHumidity<0||e.outdoorHumidity>100)) return "Outdoor humidity must be between 0% and 100%.";
    if(e.pm25!==null && (e.pm25<0||e.pm25>2000)) return "PM2.5 must be between 0 and 2,000 µg/m³.";
    return "";
  }

  function renderTable() {
    const data=[...entries].sort((a,b)=>t(b)-t(a));
    body.innerHTML = data.length ? data.map(e=>`
      <tr><td>${esc(e.timestamp.replace("T"," "))}</td><td>${esc(e.room||"—")}</td>
      <td>${num(e.indoorTemp)}°C</td><td>${num(e.outdoorTemp)}°C</td><td>${num(e.indoorTemp-e.outdoorTemp)}°C</td>
      <td>${e.humidity===null?"—":`${num(e.humidity,0)}%`}</td><td>${e.pm25===null?"—":num(e.pm25)}</td>
      <td>${esc(eventLabels[e.event]||e.event)}</td><td>${esc(e.windows)}</td><td>${esc(e.shade)}</td>
      <td>${esc(e.fan)}</td><td>${esc(e.cooling)}</td><td>${esc(e.notes||"—")}</td>
      <td class="no-print"><button class="danger del" data-id="${esc(e.id)}" style="min-height:36px;padding:6px 9px">Delete</button></td></tr>`).join("")
      : `<tr><td colspan="14"><div class="empty-state">No observations stored.</div></td></tr>`;
  }

  function chartSvg(data) {
    if(!data.length) return "";
    const w=900,h=330,p={l:58,r:24,t:24,b:58};
    const vals=data.flatMap(e=>[e.indoorTemp,e.outdoorTemp]).map(Number);
    let min=Math.floor(Math.min(...vals)-1),max=Math.ceil(Math.max(...vals)+1);
    if(min===max){min--;max++;}
    const x=i=>p.l+i*(w-p.l-p.r)/Math.max(1,data.length-1);
    const y=v=>p.t+(max-v)*(h-p.t-p.b)/(max-min);
    const step=Math.max(1,Math.ceil((max-min)/6));
    let grid="";
    for(let v=min;v<=max;v+=step) grid+=`<line x1="${p.l}" y1="${y(v)}" x2="${w-p.r}" y2="${y(v)}" stroke="#dbe8ea"/><text x="${p.l-10}" y="${y(v)+4}" text-anchor="end" font-size="12" fill="#5d7278">${v}°</text>`;
    const indoor=data.map((e,i)=>`${x(i)},${y(e.indoorTemp)}`).join(" ");
    const outdoor=data.map((e,i)=>`${x(i)},${y(e.outdoorTemp)}`).join(" ");
    const labelStep=Math.max(1,Math.ceil(data.length/7));
    const labels=data.map((e,i)=>(i%labelStep===0||i===data.length-1)?`<text x="${x(i)}" y="${h-25}" transform="rotate(-35 ${x(i)} ${h-25})" text-anchor="end" font-size="11" fill="#5d7278">${esc(e.timestamp.slice(5).replace("T"," "))}</text>`:"").join("");
    const markers=data.map((e,i)=>e.event!=="none"?`<circle cx="${x(i)}" cy="${y(e.indoorTemp)}" r="7" fill="#ffb64f" stroke="#17323b" stroke-width="2"><title>${eventLabels[e.event]}</title></circle>`:"").join("");
    return `<svg viewBox="0 0 ${w} ${h}" aria-hidden="true">${grid}<polyline fill="none" stroke="#087a95" stroke-width="4" points="${indoor}"/><polyline fill="none" stroke="#e76e38" stroke-width="3" points="${outdoor}"/>${markers}${labels}</svg>`;
  }

  function estimateLag(data) {
    if(data.length<5) return {hours:null,score:null,note:"At least five reasonably spaced observations are needed."};
    const intervals=[];
    for(let i=1;i<data.length;i++) intervals.push((t(data[i])-t(data[i-1]))/3600000);
    const typical=median(intervals.filter(v=>v>0&&v<=12));
    if(!typical) return {hours:null,score:null,note:"Time spacing is too irregular."};
    let best={shift:0,corr:-2};
    const maxShift=Math.min(8,Math.floor(data.length/3));
    for(let shift=0;shift<=maxShift;shift++){
      const xs=[],ys=[];
      for(let i=shift;i<data.length;i++){xs.push(Number(data[i-shift].outdoorTemp));ys.push(Number(data[i].indoorTemp));}
      const c=correlation(xs,ys);
      if(Number.isFinite(c)&&c>best.corr) best={shift,corr:c};
    }
    return {hours:best.shift*typical,score:best.corr,note:"Exploratory correlation-based estimate; not a physical-model identification."};
  }
  function correlation(x,y){
    if(x.length<3||x.length!==y.length)return null;
    const mx=avg(x),my=avg(y); let nume=0,dx=0,dy=0;
    for(let i=0;i<x.length;i++){const a=x[i]-mx,b=y[i]-my;nume+=a*b;dx+=a*a;dy+=b*b;}
    return dx&&dy?nume/Math.sqrt(dx*dy):null;
  }

  function rates(data) {
    const out=[];
    for(let i=1;i<data.length;i++){
      const hours=(t(data[i])-t(data[i-1]))/3600000;
      if(hours>0&&hours<=12) out.push({rate:(data[i].indoorTemp-data[i-1].indoorTemp)/hours,from:data[i-1],to:data[i]});
    }
    return out;
  }

  function eventResponses(data) {
    const rows=[];
    data.forEach((e,i)=>{
      if(e.event==="none") return;
      let next=null;
      for(let j=i+1;j<data.length;j++){
        const hours=(t(data[j])-t(e))/3600000;
        if(hours>=0.25&&hours<=3){next=data[j];break;}
        if(hours>3) break;
      }
      if(next){
        rows.push({event:e.event,start:e,next,hours:(t(next)-t(e))/3600000,delta:next.indoorTemp-e.indoorTemp,outdoorDelta:next.outdoorTemp-e.outdoorTemp});
      }
    });
    if(!rows.length) return `<div class="empty-state">No annotated action has a follow-up observation 15 minutes to 3 hours later.</div>`;
    return `<div class="table-wrap"><table class="data-table" style="min-width:760px"><thead><tr><th>Action</th><th>Follow-up</th><th>Elapsed</th><th>Indoor change</th><th>Outdoor change</th><th>Interpretation</th></tr></thead><tbody>${rows.map(r=>{
      const phrase=r.delta<-0.2?"Indoor temperature fell after the action.":r.delta>0.2?"Indoor temperature rose after the action.":"Indoor temperature changed little.";
      return `<tr><td>${esc(eventLabels[r.event])}</td><td>${esc(r.next.timestamp.replace("T"," "))}</td><td>${num(r.hours,1)} h</td><td>${r.delta>=0?"+":""}${num(r.delta)}°C</td><td>${r.outdoorDelta>=0?"+":""}${num(r.outdoorDelta)}°C</td><td>${phrase} This is observational, not causal.</td></tr>`;
    }).join("")}</tbody></table></div>`;
  }

  function renderAnalysis() {
    renderTable();
    const data=sorted();
    countPill.textContent=`${entries.length} ${entries.length===1?"entry":"entries"}`;
    rangePill.textContent=data.length?`${data[0].timestamp.slice(0,10)} → ${data[data.length-1].timestamp.slice(0,10)}`:"No range";
    if(data.length<2){empty.hidden=false;analysis.hidden=true;return;}
    empty.hidden=true;analysis.hidden=false;

    const gaps=data.map(e=>e.indoorTemp-e.outdoorTemp);
    const rs=rates(data);
    const coolingRates=rs.filter(r=>r.rate<0).map(r=>r.rate);
    const heatingRates=rs.filter(r=>r.rate>0).map(r=>r.rate);
    const lag=estimateLag(data);
    const night=data.filter(e=>{const h=new Date(e.timestamp).getHours();return h>=20||h<=8;});
    const nightRange=night.length?Math.max(...night.map(e=>e.indoorTemp))-Math.min(...night.map(e=>e.indoorTemp)):null;

    metrics.innerHTML=`
      <article class="metric"><span class="metric-label">Average indoor–outdoor gap</span><strong>${num(avg(gaps))}°C</strong><span class="metric-note">Positive means indoors warmer</span></article>
      <article class="metric"><span class="metric-label">Typical cooling rate</span><strong>${coolingRates.length?`${num(median(coolingRates))}°C/h`:"—"}</strong><span class="metric-note">Median of falling intervals</span></article>
      <article class="metric"><span class="metric-label">Estimated thermal lag</span><strong>${lag.hours===null?"—":`${num(lag.hours,1)} h`}</strong><span class="metric-note">${lag.score===null?"Insufficient data":`Correlation ${num(lag.score,2)}`}</span></article>
      <article class="metric"><span class="metric-label">Night temperature range</span><strong>${nightRange===null?"—":`${num(nightRange)}°C`}</strong><span class="metric-note">20:00–08:00 observations</span></article>`;
    chart.innerHTML=chartSvg(data);

    const hottest=data.reduce((a,b)=>a.indoorTemp>b.indoorTemp?a:b);
    const coolest=data.reduce((a,b)=>a.indoorTemp<b.indoorTemp?a:b);
    const open=data.filter(e=>e.windows!=="closed");
    const closed=data.filter(e=>e.windows==="closed");
    const openGap=avg(open.map(e=>e.indoorTemp-e.outdoorTemp));
    const closedGap=avg(closed.map(e=>e.indoorTemp-e.outdoorTemp));

    insights.innerHTML=`
      <article class="insight"><strong>Hottest indoor observation</strong>${num(hottest.indoorTemp)}°C at ${esc(hottest.timestamp.replace("T"," "))}.</article>
      <article class="insight"><strong>Coolest indoor observation</strong>${num(coolest.indoorTemp)}°C at ${esc(coolest.timestamp.replace("T"," "))}.</article>
      <article class="insight"><strong>Window-state context</strong>${open.length&&closed.length?`Average gap while open/partial: ${num(openGap)}°C; while closed: ${num(closedGap)}°C. These groups may occur under different weather.`:"Record both open and closed periods for comparison."}</article>
      <article class="insight"><strong>Lag limitation</strong>${esc(lag.note)}</article>`;
    eventAnalysis.innerHTML=eventResponses(data);
  }

  function download(name,content,type){const b=new Blob([content],{type});const u=URL.createObjectURL(b);const a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(u);}
  function csvEscape(v){return `"${String(v??"").replaceAll('"','""')}"`;}
  function exportCsv(){
    const h=["timestamp","room","indoor_temp_c","outdoor_temp_c","indoor_humidity_pct","outdoor_humidity_pct","pm25_ug_m3","event","windows","shade","fan","cooling","purifier","notes"];
    const rows=sorted().map(e=>[e.timestamp,e.room,e.indoorTemp,e.outdoorTemp,e.humidity,e.outdoorHumidity,e.pm25,e.event,e.windows,e.shade,e.fan,e.cooling,e.purifier,e.notes].map(csvEscape).join(","));
    download(`heatsafe-indoor-outdoor-${new Date().toISOString().slice(0,10)}.csv`,[h.join(","),...rows].join("\n"),"text/csv;charset=utf-8");
  }
  function exportJson(){download(`heatsafe-indoor-outdoor-${new Date().toISOString().slice(0,10)}.json`,JSON.stringify({schema:"heatsafe-indoor-outdoor-v1",exportedAt:new Date().toISOString(),entries:sorted()},null,2),"application/json");}

  form.addEventListener("submit",e=>{
    e.preventDefault();if(!form.reportValidity())return;const item=collect();const error=validate(item);if(error){alert(error);return;}
    entries.push(item);save();const room=form.elements.room.value;form.reset();setNow();form.elements.room.value=room;renderAnalysis();
  });
  document.querySelector("#reset-form")?.addEventListener("click",()=>{form.reset();setNow();});
  document.querySelector("#print-compare")?.addEventListener("click",()=>window.print());
  document.querySelector("#export-csv")?.addEventListener("click",exportCsv);
  document.querySelector("#export-json")?.addEventListener("click",exportJson);
  document.querySelector("#clear-all")?.addEventListener("click",()=>{if(entries.length&&confirm("Delete all comparator observations from this browser?")){entries=[];save();renderAnalysis();}});
  body.addEventListener("click",e=>{const b=e.target.closest(".del");if(!b)return;entries=entries.filter(x=>x.id!==b.dataset.id);save();renderAnalysis();});
  document.querySelector("#import-json")?.addEventListener("change",async e=>{
    const f=e.target.files?.[0];if(!f)return;
    try{const p=JSON.parse(await f.text());const xs=Array.isArray(p)?p:p.entries;if(!Array.isArray(xs))throw new Error("No entries array.");const clean=xs.filter(valid);if(!clean.length)throw new Error("No valid entries.");if(confirm(`Replace current data with ${clean.length} imported observations?`)){entries=clean;save();renderAnalysis();}}
    catch(err){alert(`Import failed: ${err.message}`);}finally{e.target.value="";}
  });
  document.querySelector("#load-demo")?.addEventListener("click",()=>{
    if(entries.length&&!confirm("Replace current comparator data with a demonstration dataset?"))return;
    const base=new Date();base.setHours(15,0,0,0);base.setDate(base.getDate()-1);
    const vals=[
      [0,30.4,35.8,"none","closed","open","off","off"],
      [1,30.8,35.0,"shade-closed","closed","closed","off","off"],
      [2,30.9,33.6,"fan-started","closed","closed","on","off"],
      [4,30.5,29.4,"windows-opened","open","closed","on","off"],
      [5,29.8,27.8,"none","open","closed","on","off"],
      [7,28.9,25.7,"windows-closed","closed","closed","on","off"],
      [14,27.9,24.2,"windows-opened","open","open","off","off"],
      [15,27.2,23.5,"none","open","open","off","off"]
    ];
    entries=vals.map((v,i)=>({id:`demo-${i}`,timestamp:new Date(base.getTime()+v[0]*3600000).toISOString().slice(0,16),room:"Living room",indoorTemp:v[1],outdoorTemp:v[2],humidity:52,outdoorHumidity:48,pm25:8,event:v[3],windows:v[4],shade:v[5],fan:v[6],cooling:v[7],purifier:"off",notes:i===3?"Outdoor air became cooler than indoors.":""}));
    save();renderAnalysis();
  });

  setNow();renderAnalysis();
})();
