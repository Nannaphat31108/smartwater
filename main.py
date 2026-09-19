from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import os

app = FastAPI(title="Smart Watering")
DEVICE_KEY = os.getenv("DEVICE_KEY", "change-me-smartwater")

state = {
    "moisture": 0,
    "raw": 0,
    "pump": False,
    "auto": True,
    "threshold": 35,
    "sensor_ok": False,
    "last_seen": None,
    "command_id": 0,
    "command": "none",
}

class DeviceUpdate(BaseModel):
    moisture: int
    raw: int
    pump: bool
    sensor_ok: bool = True

class Setting(BaseModel):
    value: int

def check_key(key):
    if key != DEVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid device key")

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/api/status")
def status():
    return state

@app.post("/api/device/update")
def device_update(data: DeviceUpdate, x_device_key: str | None = Header(default=None)):
    check_key(x_device_key)
    state["moisture"] = max(0, min(100, data.moisture))
    state["raw"] = data.raw
    state["pump"] = data.pump
    state["sensor_ok"] = data.sensor_ok
    state["last_seen"] = datetime.now(timezone.utc).isoformat()
    return {"ok": True, "auto": state["auto"], "threshold": state["threshold"]}

@app.get("/api/device/command")
def device_command(x_device_key: str | None = Header(default=None)):
    check_key(x_device_key)
    return {"id": state["command_id"], "command": state["command"], "auto": state["auto"], "threshold": state["threshold"]}

def command(name):
    state["command_id"] += 1
    state["command"] = name
    return {"ok": True, "id": state["command_id"], "command": name}

@app.post("/api/water")
def water():
    return command("water")

@app.post("/api/stop")
def stop():
    return command("stop")

@app.post("/api/auto/{enabled}")
def auto(enabled: int):
    state["auto"] = bool(enabled)
    if not state["auto"]:
        command("stop")
    return {"ok": True, "auto": state["auto"]}

@app.post("/api/threshold/{value}")
def threshold(value: int):
    state["threshold"] = max(10, min(80, value))
    return {"ok": True, "threshold": state["threshold"]}

HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Watering</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#eef6f1;color:#173b2b}.hero{background:#176b45;color:#fff;text-align:center;padding:28px 15px}.hero h1{margin:0}.wrap{max-width:680px;margin:auto;padding:20px}.card{background:#fff;border-radius:20px;padding:24px;margin-bottom:18px;box-shadow:0 5px 20px #00000012}.center{text-align:center}.moist{font-size:68px;font-weight:700;margin:10px}.bar{height:22px;background:#ddd;border-radius:20px;overflow:hidden}.fill{height:100%;background:#29a268;width:0;transition:.4s}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.box{background:#f3f8f5;border-radius:14px;padding:17px;text-align:center}.big{font-size:22px;font-weight:700;margin-top:5px}button{width:100%;border:0;border-radius:13px;padding:16px;margin-top:12px;font-weight:700;font-size:16px;cursor:pointer}.water{background:#1685e5;color:#fff}.stop{background:#dc4141;color:#fff}.auto{background:#176b45;color:#fff}input{width:100%}.muted{color:#748078;font-size:13px}.offline{color:#dc4141}.online{color:#176b45}
</style></head><body><div class="hero"><h1>SMART WATERING</h1><div>Cloud Control Dashboard</div></div><div class="wrap">
<div class="card center"><div class="muted">SOIL MOISTURE</div><div id="m" class="moist">--%</div><div class="bar"><div id="fill" class="fill"></div></div><p id="soil">Waiting for ESP32...</p></div>
<div class="card"><div class="grid"><div class="box"><span class="muted">PUMP</span><div id="pump" class="big">--</div></div><div class="box"><span class="muted">AUTO</span><div id="auto" class="big">--</div></div></div><button class="water" onclick="post('/api/water')">WATER NOW</button><button class="stop" onclick="post('/api/stop')">STOP PUMP</button><button class="auto" onclick="toggleAuto()" id="ab">AUTO MODE</button></div>
<div class="card center"><div class="muted">AUTO WATER BELOW</div><h2 id="tv">35%</h2><input id="th" type="range" min="10" max="80" value="35" onchange="threshold(this.value)"></div>
<div class="card center"><div id="online">ESP32: --</div><div class="muted" id="raw">RAW: --</div><div class="muted" id="seen">Last update: --</div></div></div>
<script>
let auto=true;async function post(u){await fetch(u,{method:'POST'});setTimeout(load,250)}async function toggleAuto(){await post('/api/auto/'+(auto?0:1))}async function threshold(v){document.getElementById('tv').textContent=v+'%';await post('/api/threshold/'+v)}
async function load(){try{let d=await(await fetch('/api/status')).json();auto=d.auto;document.getElementById('m').textContent=d.moisture+'%';document.getElementById('fill').style.width=d.moisture+'%';document.getElementById('pump').textContent=d.pump?'ON':'OFF';document.getElementById('auto').textContent=d.auto?'ON':'OFF';document.getElementById('ab').textContent='AUTO MODE: '+(d.auto?'ON':'OFF');document.getElementById('th').value=d.threshold;document.getElementById('tv').textContent=d.threshold+'%';document.getElementById('raw').textContent='RAW: '+d.raw;let live=false;if(d.last_seen){live=(Date.now()-Date.parse(d.last_seen))<20000}let o=document.getElementById('online');o.textContent='ESP32: '+(live?'ONLINE':'OFFLINE');o.className=live?'online':'offline';document.getElementById('seen').textContent='Last update: '+(d.last_seen?new Date(d.last_seen).toLocaleString():'--');let s=document.getElementById('soil');s.textContent=!d.sensor_ok?'CHECK SENSOR':(d.moisture<d.threshold?'DRY - WATER NEEDED':'MOISTURE OK')}catch(e){console.log(e)}}load();setInterval(load,3000);
</script></body></html>'''
