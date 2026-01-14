# 檔案：api/index.py
from http.server import BaseHTTPRequestHandler
import requests
import json
import os
from urllib.parse import urlparse, parse_qs

# 從環境變數讀取金鑰 (等等會在 Vercel 網頁設定，不要寫死在這裡)
CLIENT_ID = os.environ.get("TDX_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TDX_CLIENT_SECRET")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 解析網址參數 ?no=408
        query = parse_qs(urlparse(self.path).query)
        train_no = query.get('no', [None])[0]

        if not train_no:
            self.respond(400, {"error": "Missing train no"})
            return

        # 1. 取得 Token
        token = self.get_token()
        if not token:
            self.respond(500, {"error": "Auth failed"})
            return

        # 2. 查詢該車次即時動態
        url = f"https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/TrainLiveBoard/TrainNo/{train_no}?$format=JSON"
        headers = {"authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers)
        
        final_data = {"delay": 0, "status": "unknown"}
        
        if res.status_code == 200:
            data = res.json()
            if data and "TrainLiveBoards" in data and len(data["TrainLiveBoards"]) > 0:
                info = data["TrainLiveBoards"][0]
                final_data = {
                    "delay": info.get("DelayTime", 0),
                    "loc": info.get("StationName", {}).get("Zh_tw", "未知"),
                    "status_code": info.get("TrainStationStatus", 4)
                }
            else:
                 final_data["status"] = "no_data" # 可能尚未發車

        self.respond(200, final_data)

    def get_token(self):
        url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        data = {'grant_type': 'client_credentials', 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
        try:
            res = requests.post(url, data=data)
            return res.json().get('access_token')
        except:
            return None

    def respond(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        # 允許跨域 (雖然同源不需要，但以防萬一)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))