from http.server import BaseHTTPRequestHandler
import requests
import json
import os
from urllib.parse import urlparse, parse_qs

CLIENT_ID = os.environ.get("TDX_CLIENT_ID")
CLIENT_SECRET = os.environ.get("TDX_CLIENT_SECRET")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        train_no = query.get('no', [None])[0]

        if not train_no:
            self.respond(400, {"error": "Missing train no"})
            return

        token = self.get_token()
        if not token:
            self.respond(500, {"error": "Auth failed"})
            return

        url = f"https://tdx.transportdata.tw/api/basic/v3/Rail/TRA/TrainLiveBoard/TrainNo/{train_no}?$format=JSON"
        headers = {"authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers)
        
        # 預設狀態：尚未發車
        final_data = {
            "status": "not_started", 
            "delay": 0, 
            "loc": "尚未發車", 
            "statusCode": 0
        }
        
        if res.status_code == 200:
            data = res.json()
            # 如果 TrainLiveBoards 有資料，代表車子正在跑
            if data and "TrainLiveBoards" in data and len(data["TrainLiveBoards"]) > 0:
                info = data["TrainLiveBoards"][0]
                final_data = {
                    "status": "running",
                    "delay": info.get("DelayTime", 0),
                    "loc": info.get("StationName", {}).get("Zh_tw", "移動中"),
                    "statusCode": info.get("TrainStationStatus", 4)
                }
            # 如果回傳空陣列，維持預設的 "not_started"

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
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
