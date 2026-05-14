from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

# 匯入我們昨天千辛萬苦寫好的資料庫模組與資料表 Schema
from database import SessionLocal, Server, Metric

# 建立 FastAPI 實例
app = FastAPI(
    title="Server Monitor API",
    description="伺服器監控與冷藏資料收集系統",
    version="1.0.0"
)

# ----------------------------------------
# 1. 資料庫連線依賴注入 (Dependency Injection)
# ----------------------------------------
def get_db():
    """每次 API 被呼叫時，提供一個獨立的資料庫連線，用完即關閉"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------
# 2. 定義資料驗證模型 (Pydantic Schema)
# ----------------------------------------
class MetricPayload(BaseModel):
    """定義 Agent 傳送過來的 JSON 格式與型別檢查"""
    hostname: str = Field(..., description="伺服器主機名稱", example="web-server-01")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU 使用率 (0-100)")
    ram_usage: float = Field(..., ge=0, le=100, description="記憶體 使用率 (0-100)")
    disk_usage: float = Field(..., ge=0, le=100, description="硬碟 使用率 (0-100)")

# ----------------------------------------
# 3. API 路由端點 (Endpoints)
# ----------------------------------------
@app.get("/")
def read_root():
    return {"message": "歡迎來到伺服器監控 API。系統運作正常 🚀"}

@app.post("/api/v1/metrics", status_code=201)
def receive_metrics(payload: MetricPayload, db: Session = Depends(get_db)):
    """
    接收伺服器效能指標：
    1. 檢查該伺服器是否存在，若無則自動註冊 (Upsert 概念)。
    2. 將指標數據關聯至該伺服器並寫入資料庫。
    """
    try:
        # 步驟 A：尋找這台伺服器是否已經在資料庫註冊過
        server = db.query(Server).filter(Server.hostname == payload.hostname).first()

        # 步驟 B：如果是第一次看到這台伺服器，自動幫它建檔
        if not server:
            server = Server(hostname=payload.hostname, status="online")
            db.add(server)
            db.commit()
            db.refresh(server) # 取得資料庫自動產生的 UUID

        # 步驟 C：建立效能指標紀錄
        new_metric = Metric(
            server_id=server.id,
            cpu_usage=payload.cpu_usage,
            ram_usage=payload.ram_usage,
            disk_usage=payload.disk_usage
        )
        
        db.add(new_metric)
        db.commit()

        return {
            "status": "success", 
            "message": f"成功紀錄 {payload.hostname} 的效能指標",
            "server_id": server.id
        }

    except Exception as e:
        db.rollback() # 發生錯誤時復原交易，避免資料庫卡死
        raise HTTPException(status_code=500, detail=f"寫入資料庫失敗：{str(e)}")