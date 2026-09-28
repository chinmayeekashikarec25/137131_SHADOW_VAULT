from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import asyncio
from typing import Dict, List
import uuid

app = FastAPI(title="Fleet Monitor & ADAS")

# We will serve static files like CSS and JS
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# In-memory state for prototype
# active_drivers: dict of driver_id -> websocket
active_drivers: Dict[str, WebSocket] = {}
# control_centers: list of websockets
control_centers: List[WebSocket] = []

# Mock vehicle locations
vehicle_data = {}

import random

# Initialize dummy vehicles for prototype visualization
# Spread them along the route from Bailadila (18.6300, 81.2300) to Visakhapatnam (17.6128, 83.1919)
dummy_vehicles = [f"TRK-{i}" for i in range(100, 110)] # 10 trucks

start_lat, start_lng = 18.6300, 81.2300
end_lat, end_lng = 17.6128, 83.1919

for i, v in enumerate(dummy_vehicles):
    # Distribute them very closely near the start of the route (Bailadila)
    progress = (i / len(dummy_vehicles)) * 0.02 # Only spread across the first 2% of the route
    vehicle_data[v] = {
        "lat": start_lat + (end_lat - start_lat) * progress + (random.random() - 0.5) * 0.005,
        "lng": start_lng + (end_lng - start_lng) * progress + (random.random() - 0.5) * 0.005,
        "status": "active"
    }

async def simulate_fleet():
    while True:
        await asyncio.sleep(2)
        for v in dummy_vehicles:
            # Move them slowly towards Visakhapatnam
            vehicle_data[v]["lat"] += (end_lat - start_lat) * 0.0001
            vehicle_data[v]["lng"] += (end_lng - start_lng) * 0.0001
        
        if control_centers:
            for ws in control_centers:
                try:
                    await ws.send_json({"type": "fleet_update", "data": vehicle_data})
                except:
                    pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_fleet())

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    response = templates.TemplateResponse(request=request, name="landing.html", context={"request": request})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def login_page(request: Request):
    response = templates.TemplateResponse(request=request, name="index.html", context={"request": request})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.post("/login")
async def login(role: str = Form(...)):
    if role == "driver":
        # Automatically assign a random vehicle ID for the driver
        assigned_id = f"TRK-{random.randint(200, 999)}"
        return RedirectResponse(url=f"/driver/{assigned_id}", status_code=303)
    elif role == "control":
        return RedirectResponse(url="/control", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/driver", response_class=HTMLResponse)
async def driver_dashboard_default(request: Request):
    return templates.TemplateResponse(request=request, name="driver.html", context={"request": request, "vehicle_id": "KA-01-MG-104"})

@app.get("/driver/{vehicle_id}", response_class=HTMLResponse)
async def driver_dashboard(request: Request, vehicle_id: str):
    return templates.TemplateResponse(request=request, name="driver.html", context={"request": request, "vehicle_id": vehicle_id})

@app.get("/control", response_class=HTMLResponse)
async def control_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="control.html", context={"request": request})

# WebSocket for Truck Drivers
@app.websocket("/ws/driver/{vehicle_id}")
async def websocket_driver(websocket: WebSocket, vehicle_id: str):
    await websocket.accept()
    active_drivers[vehicle_id] = websocket
    
    # Send initial data
    await websocket.send_json({"type": "info", "message": f"Connected to vehicle {vehicle_id}"})
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle location updates
            if message["type"] == "location_update":
                vehicle_data[vehicle_id] = {
                    "lat": message["lat"],
                    "lng": message["lng"],
                    "status": "active"
                }
                # Broadcast to control centers
                await broadcast_to_control({"type": "fleet_update", "data": vehicle_data})
                
            # Handle SOS/Help calls
            elif message["type"] == "sos":
                alert = {"type": "sos_alert", "vehicle_id": vehicle_id, "message": "Driver requested help!"}
                await broadcast_to_control(alert)
                
            # Handle MPU6050 Tilt Alert
            elif message["type"] == "tilt_alert":
                alert = {"type": "sos_alert", "vehicle_id": vehicle_id, "message": "CRITICAL: Vehicle has tilted and fallen and needs immediate help!"}
                await broadcast_to_control(alert)
                
    except WebSocketDisconnect:
        del active_drivers[vehicle_id]
        if vehicle_id in vehicle_data:
            vehicle_data[vehicle_id]["status"] = "offline"
            await broadcast_to_control({"type": "fleet_update", "data": vehicle_data})

# WebSocket for Control Center
@app.websocket("/ws/control")
async def websocket_control(websocket: WebSocket):
    await websocket.accept()
    control_centers.append(websocket)
    
    # Send current fleet state
    await websocket.send_json({"type": "fleet_update", "data": vehicle_data})
    
    try:
        while True:
            data = await websocket.receive_text()
            # Control center might send commands back to vehicles
    except WebSocketDisconnect:
        control_centers.remove(websocket)

async def broadcast_to_control(message: dict):
    for ws in control_centers:
        await ws.send_json(message)

# API Endpoint for NRF Module (Hardware integration)
class NRFData(BaseModel):
    vehicle_id: str
    signal_strength: int
    detected_vehicle_id: str = None # If it detects another vehicle

@app.post("/api/nrf")
async def receive_nrf_data(data: NRFData):
    # This endpoint receives data from hardware NRF module.
    if data.vehicle_id in active_drivers and data.detected_vehicle_id:
        alert = {
            "type": "proximity_alert",
            "message": f"Vehicle {data.detected_vehicle_id} is approaching! Reduce speed.",
            "distance": data.signal_strength
        }
        await active_drivers[data.vehicle_id].send_json(alert)
        
    return {"status": "received"}

# API Endpoint for General Hardware Sensors (DHT22 & MPU6050)
class SensorData(BaseModel):
    vehicle_id: str
    temperature: float
    humidity: float
    tilt_detected: bool

@app.post("/api/sensor")
async def receive_sensor_data(data: SensorData):
    # 1. Check for emergency tilt (MPU6050)
    if data.tilt_detected:
         alert = {"type": "sos_alert", "vehicle_id": data.vehicle_id, "message": "CRITICAL: Vehicle has tilted and fallen and needs immediate help!"}
         await broadcast_to_control(alert)
         
         if data.vehicle_id in active_drivers:
             await active_drivers[data.vehicle_id].send_json({"type": "proximity_alert", "message": "⚠️ VEHICLE TILT DETECTED ⚠️"})
    
    # 2. Forward real-time DHT22 environment stats to the driver's specific UI
    if data.vehicle_id in active_drivers:
        await active_drivers[data.vehicle_id].send_json({
            "type": "environment_update",
            "temperature": data.temperature,
            "humidity": data.humidity
        })
        
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
