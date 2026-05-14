import os
import json
import boto3
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, Metric, Server

# ⚠️ 替換成你三天前建立的 S3 儲存桶名稱！
# 格式大約是：server-monitor-archive-你的英文名字小寫
S3_BUCKET_NAME = "server-monitor-archive-kasa"
AWS_REGION = "us-east-1"

def archive_old_metrics(db: Session, days_to_keep=1):
    """將超過指定天數的指標數據封存到 S3，然後從 RDS 刪除"""
    
    # 1. 計算切割時間點 (例如：一天前的時間)
    cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
    print(f"🔍 準備尋找早於 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} 的舊資料...")

    try:
        # 2. 從資料庫撈出舊資料，並關聯伺服器名稱
        old_metrics = db.query(Metric, Server.hostname)\
                        .join(Server, Metric.server_id == Server.id)\
                        .filter(Metric.timestamp < cutoff_time).all()

        if not old_metrics:
            print("✅ 目前沒有需要封存的舊資料。")
            return

        print(f"📦 找到 {len(old_metrics)} 筆舊資料，準備打包...")

        # 3. 將資料轉換為 JSON 格式
        archive_data = []
        for metric, hostname in old_metrics:
            archive_data.append({
                "id": str(metric.id),
                "server": hostname,
                "cpu": metric.cpu_usage,
                "ram": metric.ram_usage,
                "disk": metric.disk_usage,
                "timestamp": metric.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

        # 4. 產生 S3 檔案名稱 (使用當下時間戳記)
        file_name = f"archive/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # 5. 上傳至 AWS S3
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=json.dumps(archive_data, indent=2),
            ContentType='application/json'
        )
        print(f"☁️ 成功上傳封存檔至 S3: s3://{S3_BUCKET_NAME}/{file_name}")

        # 6. 確認上傳成功後，從 RDS 刪除這些舊資料以釋放空間
        # (這裡我們使用 Bulk Delete 提升效能)
        metric_ids_to_delete = [metric.id for metric, _ in old_metrics]
        db.query(Metric).filter(Metric.id.in_(metric_ids_to_delete)).delete(synchronize_session=False)
        db.commit()
        
        print(f"🗑️ 已從 RDS 移除 {len(old_metrics)} 筆過期資料，釋放空間成功！")

    except Exception as e:
        db.rollback()
        print(f"❌ 封存過程發生錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # 初始化資料庫連線
    db_session = SessionLocal()
    
    # ⚠️ 為了方便現在立刻測試，我們把 days_to_keep 設為 0
    # 這代表「把剛剛前一秒傳進去的所有資料都當作舊資料封存起來」！
    print("🚀 啟動冷資料封存程序...")
    archive_old_metrics(db_session, days_to_keep=0)