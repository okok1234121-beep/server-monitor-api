import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Numeric, DateTime, ForeignKey, Text, BigInteger, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base

# 設定日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 載入 .env 檔案
# CRITICAL: override=False 確保當 Docker 或系統已提供環境變數時，不會被本地 .env 蓋掉
load_dotenv(override=False)

# 獲取資料庫連線字串 (優先讀取雲端環境變數)
DATABASE_URL = os.getenv("DATABASE_URL")

# 初始化檢查
if not DATABASE_URL:
    logger.error("環境變數 DATABASE_URL 未設定。請檢查 .env 檔案或 Docker 啟動參數。")
    # 不在此拋出異常，避免匯入時直接崩潰，但會在建立引擎時失敗

# 建立 SQLAlchemy 引擎
engine = create_engine(DATABASE_URL, echo=False) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 專業監控架構模型 (方案 A) ---

class Server(Base):
    """伺服器清單表"""
    __tablename__ = 'servers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(100), nullable=False)
    ip_address = Column(String(45))
    os_info = Column(String(50))
    status = Column(String(20), default='online')
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))

class Metric(Base):
    """效能指標表 (時序資料)"""
    __tablename__ = 'metrics'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey('servers.id', ondelete="CASCADE"))
    cpu_usage = Column(Numeric(5, 2))
    ram_usage = Column(Numeric(5, 2))
    disk_usage = Column(Numeric(5, 2))
    recorded_at = Column(DateTime(timezone=True), index=True, server_default=text('now()'))

class Log(Base):
    """系統日誌表 (支援 S3 封存)"""
    __tablename__ = 'logs'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey('servers.id', ondelete="CASCADE"))
    level = Column(String(10), index=True)
    message = Column(Text)
    extra_data = Column(JSONB) # 儲存非結構化資訊
    created_at = Column(DateTime(timezone=True), index=True, server_default=text('now()'))

def init_db():
    """執行資料庫初始化與建表"""
    if not engine:
        logger.error("資料庫引擎未就緒，無法初始化。")
        return

    try:
        logger.info("正在執行雲端資料庫建表程序...")
        Base.metadata.create_all(bind=engine)
        logger.info("資料庫初始化成功：Schema 已同步至 RDS。")
    except Exception as e:
        logger.error(f"建立資料表時發生錯誤：{e}")
        raise

if __name__ == "__main__":
    init_db()