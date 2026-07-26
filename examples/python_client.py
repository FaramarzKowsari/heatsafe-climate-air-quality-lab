import httpx
payload={"indoor_temperature_c":29,"outdoor_temperature_c":23,"pm25_ug_m3":10,"smoke_context":"none"}
print(httpx.post("http://127.0.0.1:8000/api/v1/ventilation/decision",json=payload,timeout=10).json())
