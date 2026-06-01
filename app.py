import os
import requests
import platform
from datetime import datetime
from flask import Flask, render_template_string

app = Flask(__name__)

# CẤU HÌNH ĐỊNH DANH TELEGRAM BOT CỦA BẠN
TELEGRAM_TOKEN = "8801962093:AAGffyq07nsxXt-IEiOFrebgUNUN_cwISKY"
TELEGRAM_CHAT_ID = "7489077099"

# Danh sách 4 thiết bị hạ tầng (Bao gồm cả Máy in và IoT)
DEVICES = [
    {"name": "Core_Router_PC1", "ip": "192.168.116.10", "type": "Router"},
    {"name": "Access_Switch_PC2", "ip": "192.168.116.20", "type": "Switch"},
    {"name": "Office_Printer_HP", "ip": "192.168.116.30", "type": "Printer"},
    {"name": "Smart_Camera_IoT", "ip": "192.168.116.40", "type": "IoT_Device"}
]

# Từ điển lưu trạng thái trước đó để kiểm tra xem thiết bị có vừa mới bị sập hay không
PREVIOUS_STATUS = {}

def send_telegram_alert(device_name, ip):
    """Hàm tự động bắn tin nhắn về điện thoại qua Telegram API"""
    now = datetime.now().strftime('%H:%M:%S | %d/%m/%Y')
    message = f"⚠️ [ALERT] THIẾT BỊ MẤT KẾT NỐI!\n\n❌ Tên: {device_name}\n🌐 IP: {ip}\n⏰ Thời gian: {now}\n‼️ Vui lòng kiểm tra lại hạ tầng mạng!"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def check_status(device):
    global PREVIOUS_STATUS
    ip = device["ip"]
    name = device["name"]
    
    # TỰ ĐỘNG NHẬN DIỆN HỆ ĐIỀU HÀNH ĐỂ PING (Windows dùng -n, Linux/Render dùng -c)
    is_windows = platform.system().lower() == "windows"
    param = "-n" if is_windows else "-c"
    
    # Chuyển hướng đầu ra để tránh làm rác log console
    null_output = "> nul" if is_windows else "> /dev/null 2>&1"
    
    # Thực hiện lệnh ping phù hợp với hệ thống
    response = os.system(f"ping {param} 1 {ip} {null_output}")
    current_status = "ONLINE" if response == 0 else "OFFLINE"
    
    # Lấy trạng thái cũ của thiết bị này (mặc định ban đầu coi như ONLINE)
    old_status = PREVIOUS_STATUS.get(ip, "ONLINE")
    
    # Nếu trạng thái vừa đổi từ ONLINE sang OFFLINE -> Kích hoạt báo động ngay!
    if old_status == "ONLINE" and current_status == "OFFLINE":
        send_telegram_alert(name, ip)
        
    # Cập nhật lại trạng thái vào bộ nhớ tạm
    PREVIOUS_STATUS[ip] = current_status
    return current_status

# GIAO DIỆN WEB NOC DASHBOARD
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Enterprise Network Monitoring Station</title>
    <meta http-equiv="refresh" content="4">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #0b0f19; color: #cbd5e1; font-family: 'Segoe UI', sans-serif; }
        .noc-header { background: linear-gradient(90deg, #1e1b4b, #311042); border-bottom: 2px solid #4338ca; padding: 15px; }
        .card-custom { background-color: #111827; border: 1px solid #1f2937; border-radius: 10px; }
        .status-badge { padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
        .bg-online { background-color: #065f46; color: #34d399; border: 1px solid #059669; }
        .bg-offline { background-color: #7f1d1d; color: #f87171; border: 1px solid #dc2626; }
        .pulse-online { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="noc-header text-center mb-4">
        <h2 class="text-white fw-bold">NETWORK OPERATION CENTER (NOC) DASHBOARD</h2>
        <small class="text-info">Hệ thống Giám sát & Cảnh báo Tự động qua Telegram | Quét: 4s/lần</small>
    </div>
    <div class="container">
        <div class="row text-center mb-4">
            <div class="col-md-4"><div class="card-custom p-3"><h6>TỔNG THIẾT BỊ</h6><h2 class="fw-bold text-primary">{{ total }}</h2></div></div>
            <div class="col-md-4"><div class="card-custom p-3"><h6>ONLINE</h6><h2 class="fw-bold text-success">{{ online }}</h2></div></div>
            <div class="col-md-4"><div class="card-custom p-3"><h6>OFFLINE</h6><h2 class="fw-bold text-danger">{{ offline }}</h2></div></div>
        </div>
        <div class="row">
            <div class="col-md-8 mb-4">
                <div class="card-custom p-4 h-100">
                    <h5 class="mb-3 text-white border-bottom pb-2">HẠ TẦNG THIẾT BỊ TRONG DOANH NGHIỆP (MẠNG + IOT)</h5>
                    <table class="table table-dark table-hover align-middle">
                        <thead>
                            <tr><th>Tên Thiết Bị</th><th>Địa Chỉ IP</th><th>Phân Loại</th><th class="text-center">Trạng Thái</th></tr>
                        </thead>
                        <tbody>
                            {% for dev in data %}
                            <tr>
                                <td class="fw-bold text-info">{{ dev.name }}</td>
                                <td><code>{{ dev.ip }}</code></td>
                                <td><span class="badge bg-secondary">{{ dev.type }}</span></td>
                                <td class="text-center">
                                    {% if dev.status == 'ONLINE' %}
                                    <span class="status-badge bg-online pulse-online">● ONLINE</span>
                                    {% else %}
                                    <span class="status-badge bg-offline">■ OFFLINE</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card-custom p-4 text-center h-100">
                    <h5 class="mb-3 text-white border-bottom pb-2">TỶ LỆ HOẠT ĐỘNG</h5>
                    <div style="width: 180px; margin: auto;"><canvas id="statusChart"></canvas></div>
                </div>
            </div>
        </div>
    </div>
    <script>
        // Sửa lỗi cú pháp khi render dữ liệu số vào Javascript của Chart.js
        const onlineCount = parseInt("{{ online }}") || 0;
        const offlineCount = parseInt("{{ offline }}") || 0;

        const ctx = document.getElementById('statusChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline'],
                datasets: [{ data: [onlineCount, offlineCount], backgroundColor: ['#10b981', '#ef4444'], borderWidth: 0 }]
            },
            options: { plugins: { legend: { labels: { color: 'white' } } } }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    results = []
    online_cnt = 0
    offline_cnt = 0
    for dev in DEVICES:
        status = check_status(dev)
        if status == "ONLINE":
            online_cnt += 1
        else:
            offline_cnt += 1
        results.append({"name": dev["name"], "ip": dev["ip"], "type": dev["type"], "status": status})
    
    return render_template_string(HTML_TEMPLATE, data=results, total=len(DEVICES), online=online_cnt, offline=offline_cnt)

if __name__ == '__main__':
    # Giữ nguyên port 5000 phục vụ cả chạy local lẫn Render tự bắt port
    app.run(host='0.0.0.0', port=5000, debug=True)