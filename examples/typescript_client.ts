const response = await fetch("http://127.0.0.1:8000/api/v1/ventilation/decision", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({indoor_temperature_c: 29, outdoor_temperature_c: 23, pm25_ug_m3: 10, smoke_context: "none"}),
});
console.log(await response.json());
