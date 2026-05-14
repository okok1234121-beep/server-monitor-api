import os
import json
import boto3
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import SessionLocal, Metric, Server

# ⚠️ 請確保這是你正確的 S3 儲存桶名稱
S3_BUCKET_NAME = "server-monitor-archive-kasa"
AWS_REGION = "us-east-1"

def archive_old_metrics(db: Session, days_to_keep=1):
    """將超過指定天數的指標數據封存到 S3，並從 RDS 刪除以節省空間"""
    
    # 使用時區感知的 UTC 時間，避免版本過期警告
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    print(f"🔍 準備尋找早於 {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC) 的舊資料...")

    try:
        # [精準修復] 使用正確的欄位名稱 recorded_at 進行查詢
        old_metrics = db.query(Metric, Server.hostname)\
                        .join(Server, Metric.server_id == Server.id)\
                        .filter(Metric.recorded_at < cutoff_time).all()

        if not old_metrics:
            print("✅ 目前沒有需要封存的舊資料。")
            return

        print(f"📦 找到 {len(old_metrics)} 筆舊資料，準備執行封存程序...")

        archive_data = []
        for metric, hostname in old_metrics:
            archive_data.append({
                "id": str(metric.id),
                "server": hostname,
                "cpu": float(metric.cpu_usage),
                "ram": float(metric.ram_usage),
                "disk": float(metric.disk_usage),
                "timestamp": metric.recorded_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        # 檔案命名包含時間戳記
        file_name = f"archive/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # 執行 S3 上傳
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=json.dumps(archive_data, indent=2),
            ContentType='application/json'
        )
        print(f"☁️ 數據已成功外移至 S3: s3://{S3_BUCKET_NAME}/{file_name}")

        # 刪除已封存的原始資料
        metric_ids_to_delete = [metric.id for metric, _ in old_metrics]
        db.query(Metric).filter(Metric.id.in_(metric_ids_to_delete)).delete(synchronize_session=False)
        db.commit()
        
        print(f"🗑️ 已從 RDS 清除 {len(old_metrics)} 筆舊紀錄，資料庫空間釋放完畢。")

    except Exception as e:
        db.rollback()
        print(f"❌ 執行封存時發生異常: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    db_session = SessionLocal()
    print("🚀 啟動冷熱資料分離程序 (Archiver)...")
    # 設定為 0 代表將現有所有資料進行封存測試
    archive_old_metrics(db_session, days_to_keep=0)