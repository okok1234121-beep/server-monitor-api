import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入 .env 檔案中的環境變數
load_dotenv()

# 從環境變數讀取連線字串，若讀取不到則為 None
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("環境變數 DATABASE_URL 未設定，請檢查 .env 檔案")
    raise ValueError("No DATABASE_URL set in environment variables")

# 建立 SQLAlchemy 引擎
try:
    engine = create_engine(DATABASE_URL)
    # check_same_thread=False 僅用於 SQLite，PostgreSQL 不需要
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("資料庫引擎初始化成功")
except Exception as e:
    logger.error(f"資料庫連線失敗: {e}")
    raise

# 取得資料庫會話的 Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()