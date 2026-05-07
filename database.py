import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# 設定 logging 模組
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL 資料庫連線字串
# 格式：postgresql+psycopg2://使用者名稱:密碼@主機位址:連接埠/資料庫名稱
# 請將 user, password, dbname 替換為你本地端 PostgreSQL 的實際設定
DATABASE_URL = "postgresql+psycopg2://postgres:35535@host.docker.internal:5432/server_monitor"

# 建立 SQLAlchemy 引擎
try:
    engine = create_engine(DATABASE_URL, echo=False)
    logger.info("成功建立 PostgreSQL 資料庫引擎。")
except Exception as e:
    logger.error(f"建立資料庫引擎失敗：{e}")

# 建立 Session 類別，供後續 FastAPI 注入使用
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 Base 類別，所有的 Model 都必須繼承它
Base = declarative_base()

# 定義資料表 Schema (SA/SD 規劃之結構)
class ServerHealthLog(Base):
    __tablename__ = "server_health_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_name = Column(String(50), nullable=False, index=True)
    cpu_usage = Column(Float, nullable=False)
    ram_usage = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# 獨立執行此檔案時，自動在資料庫中建立資料表
if __name__ == "__main__":
    try:
        logger.info("開始檢查並建立資料表...")
        # 執行這行指令，SQLAlchemy 會自動將繼承 Base 的 Model 轉換為 SQL 語法並建表
        Base.metadata.create_all(bind=engine)
        logger.info("資料表建立程序完成（若資料表已存在則會略過）。")
    except Exception as e:
        logger.error(f"建立資料表時發生錯誤：{e}")