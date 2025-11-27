from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
import json
import os
from dotenv import load_dotenv

# 1. โหลด Config
load_dotenv()

APP_API_KEY = os.getenv("MY_API_KEY") # Key ที่ device ต้องส่งมา
DATA_FILE_PATH = "forfastapi.json"    # ไฟล์ที่ app.py เขียนไว้

if not APP_API_KEY:
    print("⚠️  WARNING: MY_API_KEY is not set in .env. Security is disabled!")

app = FastAPI(
    title="Earthquake Data API",
    description="API สำหรับดึงข้อมูลแผ่นดินไหวล่าสุดจาก Local JSON",
    version="1.0.0"
)

# 2. ตั้งค่า Security Header (ชื่อ Header คือ X-API-Key)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """ฟังก์ชันตรวจสอบ API Key"""
    if not APP_API_KEY:
        # ถ้าไม่ได้ตั้ง Key ใน .env ให้ผ่านได้เลย (สำหรับ Test)
        return "no-key-set"
    
    if api_key_header == APP_API_KEY:
        return api_key_header
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )

@app.get("/")
async def root():
    return {"message": "Earthquake API is running. Use /latest to get data."}

@app.get("/latest")
async def get_latest_earthquake(api_key: str = Security(get_api_key)):
    """
    อ่านไฟล์ forfastapi.json และส่งข้อมูลกลับ
    """
    if not os.path.exists(DATA_FILE_PATH):
        raise HTTPException(status_code=404, detail="Data file not found. Wait for app.py to fetch data.")
    
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # รันเซิร์ฟเวอร์ที่ Port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)