# 使用官方 Python 3.13 slim 輕量化版本作為基底
FROM python:3.13-slim

# 設定容器內部的工作目錄
WORKDIR /app

# 將本地端的 requirements.txt 複製到容器內
COPY requirements.txt .

# 安裝 Python 依賴套件，並加上 --no-cache-dir 避免產生無用的暫存檔，進一步縮小映像檔體積
RUN pip install --no-cache-dir -r requirements.txt

# 將專案內的所有程式碼 (database.py, main.py 等) 複製到容器內
COPY . .

# 宣告容器對外開放的 Port (這只是標示，實際要在執行時做 Port Mapping)
EXPOSE 8000

# 啟動 FastAPI 伺服器，綁定 0.0.0.0 讓外部請求可以連入
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]