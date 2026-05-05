import requests
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# --- 1. 碳排放常數 ---
TRANSPORT_FACTORS = {
    "hsr": 0.032, "tra": 0.054, "bus": 0.080, 
    "car": 0.190, "scooter": 0.046
}

ACCOM_FACTORS = {
    "eco": 12.0,        # 環保旅店/背包客棧
    "standard": 25.0,   # 一般旅館/民宿
    "luxury": 45.0      # 星級飯店/渡假村
}

# --- 2. 距離計算服務 (全免費開源版) ---
class FreeDistanceCalculator:
    def get_distance(self, transport_type: str, origin: str, destination: str) -> float:
        if transport_type in ["hsr", "tra", "bus"]:
            print(f"[TDX 模擬] 查詢從 {origin} 到 {destination} 的里程")
            return 165.0  # 模擬大眾運輸站間里程
        elif transport_type in ["car", "scooter"]:
            lon1, lat1 = self._get_coordinates(origin)
            time.sleep(1) 
            lon2, lat2 = self._get_coordinates(destination)
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
            print(f"[OSRM API] 計算導航距離: {origin} -> {destination}")
            response = requests.get(osrm_url)
            data = response.json()
            if data.get("code") != "Ok":
                raise ValueError("無法規劃導航路線")
            return data["routes"][0]["distance"] / 1000.0
        else:
            raise ValueError("未知的交通方式")

    def _get_coordinates(self, address: str) -> tuple:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "countrycodes": "tw", "limit": 1}
        headers = {"User-Agent": "TaiwanCarbonFootprintApp/1.1"} 
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        if not data:
            raise ValueError(f"找不到地址: {address}")
        return (float(data[0]["lon"]), float(data[0]["lat"]))

# --- 3. 資料模型定義 ---
class TripSegment(BaseModel):
    transport_type: str
    origin: str          
    destination: str
    passengers: int = 1

class Accommodation(BaseModel):
    accom_type: str
    nights: int = 1

class FullTripRequest(BaseModel):
    segments: List[TripSegment] = []
    accommodations: List[Accommodation] = []

# --- 4. FastAPI 應用程式 ---
app = FastAPI(title="台灣旅遊碳排放計算機 API (含住宿)")
calculator = FreeDistanceCalculator()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/calculate_full")
def calculate_full_trip(request: FullTripRequest):
    try:
        transport_carbon = 0.0
        accom_carbon = 0.0

        # 計算所有交通段落
        for seg in request.segments:
            distance = calculator.get_distance(seg.transport_type, seg.origin, seg.destination)
            factor = TRANSPORT_FACTORS.get(seg.transport_type)
            if seg.transport_type == "car":
                transport_carbon += (distance * factor) / seg.passengers
            else:
                transport_carbon += distance * factor

        # 計算所有住宿
        for acc in request.accommodations:
            factor = ACCOM_FACTORS.get(acc.accom_type, 25.0)
            accom_carbon += factor * acc.nights

        total_carbon = transport_carbon + accom_carbon

        return {
            "status": "success",
            "data": {
                "transport_carbon_kg": round(transport_carbon, 2),
                "accom_carbon_kg": round(accom_carbon, 2),
                "total_carbon_kg": round(total_carbon, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))