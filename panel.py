from flask import Flask, request, jsonify, Response
from datetime import datetime
import threading
import os
import json
from functools import wraps

app = Flask(__name__)

# --- 确保 cookies 文件夹存在 ---
COOKIE_DIR = 'cookies'
os.makedirs(COOKIE_DIR, exist_ok=True)

# 定义全局密钥
SECRET_KEY = "*"

def require_auth(f):
    """一个装饰器，用于验证请求头中的密码"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头获取 'X-Auth-Token'
        token = request.headers.get('X-Auth-Token')
        if not token or token != SECRET_KEY:
            return jsonify({"error": "Authentication failed. Invalid or missing token."}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- HTML/CSS/JS Template Embedded as a Python String ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bilibili Uploader Status Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: auto; background-color: #1e1e1e; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
        h1, h2 { color: #bb86fc; border-bottom: 2px solid #373737; padding-bottom: 10px; margin-top: 0; }
        h2 { margin-top: 30px; color: #03dac6; }
        .card { background-color: #2c2c2c; border-radius: 6px; padding: 15px; margin-bottom: 20px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .status-item strong { color: #03dac6; display: block; margin-bottom: 5px; }
        ul { list-style: none; padding: 0; }
        ul li { background-color: #333; padding: 10px 15px; border-radius: 4px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
        ul li a { color: #8ab4f8; text-decoration: none; }
        ul li a:hover { text-decoration: underline; }
        .placeholder { color: #666; }
        .footer { text-align: center; margin-top: 30px; font-size: 0.9em; color: #666; }
        textarea { width: 100%; min-height: 150px; box-sizing: border-box; background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; border-radius: 4px; padding: 10px; font-family: 'Courier New', Courier, monospace; resize: vertical; }
        button { background-color: #bb86fc; color: #121212; border: none; padding: 10px 20px; font-size: 1em; font-weight: bold; border-radius: 4px; cursor: pointer; transition: background-color 0.2s; margin-top: 10px; }
        button:hover { background-color: #a062f8; }
        #upload-status { margin-top: 10px; font-weight: bold; }
        .success { color: #03dac6; }
        .error { color: #cf6679; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Upload New Cookie</h2>
        <div class="card">
            <form id="cookie-form">
                <p>Paste the cookie content (JSON format from browser extension) below:</p>
                <textarea id="cookies-data" name="cookies_data" placeholder='[{"name": "SESSDATA", "value": "..."},{"name": "bili_jct", "value": "..."}, ...]' required></textarea>
                <button type="submit">Upload Cookie</button>
            </form>
            <div id="upload-status"></div>
        </div>
        
        <h1>Bilibili Uploader Status Dashboard</h1>
        <div class="card">
            <p><strong>Last Update:</strong> <span id="last-update">Waiting for data...</span></p>
            <p><strong>Latest Event:</strong> <span id="event" style="font-weight: bold; color: yellow;">Waiting for data...</span></p>
        </div>

        <div class="status-grid">
            <div class="status-item card"><strong>Current Account</strong><span id="current-account">N/A</span></div>
            <div class="status-item card"><strong>Total Successful Uploads</strong><span id="total-successful-uploads">0</span></div>
            <div class="status-item card"><strong>Accounts Status</strong><span id="accounts-status">0 / 0</span></div>
            <div class="status-item card"><strong>Failed Accounts</strong><span id="failed-accounts-count" style="color: #cf6679; font-weight: bold;">0</span></div>
        </div>

        <h2>Uploads by Account</h2>
        <div class="card"><ul id="uploads-by-account-list"><li class="placeholder">No upload data yet.</li></ul></div>

        <h2>Successful Uploads (BVIDs)</h2>
        <div class="card"><ul id="successful-videos-list"><li class="placeholder">No successful uploads yet.</li></ul></div>
        
        <div class="footer">Page auto-refreshes every 5 seconds. New cookies are detected automatically.</div>
    </div>

    <script>
        const SECRET_KEY = "__SECRET_KEY_PLACEHOLDER__";
        const sanitize = (str) => { const temp = document.createElement('div'); temp.textContent = str; return temp.innerHTML; };
        
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status', { headers: { 'X-Auth-Token': SECRET_KEY } });
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                document.getElementById('last-update').textContent = new Date(data.last_update).toLocaleString();
                document.getElementById('event').textContent = sanitize(data.event || 'N/A');
                document.getElementById('current-account').textContent = sanitize(data.current_account || 'N/A');
                document.getElementById('total-successful-uploads').textContent = data.total_successful_uploads || 0;
                document.getElementById('accounts-status').textContent = `${(data.total_accounts || 0) - (data.failed_accounts_count || 0)} / ${data.total_accounts || 0} active`;
                document.getElementById('failed-accounts-count').textContent = data.failed_accounts_count || 0;
                const uploadsList = document.getElementById('uploads-by-account-list');
                uploadsList.innerHTML = '';
                if (data.uploads_by_account && Object.keys(data.uploads_by_account).length > 0) {
                    for (const [account, count] of Object.entries(data.uploads_by_account)) {
                        uploadsList.innerHTML += `<li><span>${sanitize(account)}</span> <strong>${count} uploads</strong></li>`;
                    }
                } else { uploadsList.innerHTML = '<li class="placeholder">No upload data yet.</li>'; }
                const videosList = document.getElementById('successful-videos-list');
                videosList.innerHTML = '';
                if (data.successful_videos && data.successful_videos.length > 0) {
                    data.successful_videos.forEach(bvid => {
                        const sanitizedBvid = sanitize(bvid);
                        videosList.innerHTML += `<li><a href="https://www.bilibili.com/video/${sanitizedBvid}" target="_blank">${sanitizedBvid}</a><span><a href="https://www.bilibili.com/video/${sanitizedBvid}" target="_blank">Watch</a></span></li>`;
                    });
                } else { videosList.innerHTML = '<li class="placeholder">No successful uploads yet.</li>'; }
            } catch (error) { console.error("Failed to fetch status:", error); document.getElementById('event').textContent = 'Error connecting to server...'; }
        }
        
        async function handleFormSubmit(event) {
            event.preventDefault();
            const form = event.target;
            const textarea = document.getElementById('cookies-data');
            const statusDiv = document.getElementById('upload-status');
            const formData = new FormData(form);
            statusDiv.textContent = 'Uploading...'; statusDiv.className = '';
            try {
                const response = await fetch('/upload-cookie', { method: 'POST', headers: { 'X-Auth-Token': SECRET_KEY }, body: formData });
                const result = await response.json();
                if (response.ok) {
                    statusDiv.textContent = result.message;
                    statusDiv.className = 'success';
                    textarea.value = '';
                } else { throw new Error(result.error || 'Unknown error occurred.'); }
            } catch(error) { statusDiv.textContent = `Error: ${error.message}`; statusDiv.className = 'error'; }
        }

        document.addEventListener('DOMContentLoaded', () => {
            fetchStatus();
            setInterval(fetchStatus, 5000);
            document.getElementById('cookie-form').addEventListener('submit', handleFormSubmit);
        });
    </script>
</body>
</html>
"""

# --- Server Logic ---
lock = threading.Lock()
latest_status = {
    "message": "服务器已启动，正在等待第一个状态更新...", "event": "server_start",
    "last_update": datetime.now().isoformat(), "uploads_by_account": {}, "successful_videos": [],
}

def clear_console(): os.system('cls' if os.name == 'nt' else 'clear')
def display_status_in_console():
    with lock: status_to_display = latest_status.copy()
    clear_console()
    print(" Bilibili 自动上传状态监控 (Console) ".center(60, "="))
    print(f"最后更新: {datetime.fromisoformat(status_to_display['last_update']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"最新事件: {status_to_display.get('event', 'N/A')}")
    print("-" * 60)
    print(f"成功上传: {status_to_display.get('total_successful_uploads', 0)} | "
          f"账号状态: {(status_to_display.get('total_accounts', 0) or 0) - (status_to_display.get('failed_accounts_count', 0) or 0)} / {status_to_display.get('total_accounts', 0) or 0}")
    print("-" * 60)
    print("访问 http://127.0.0.1:7652 在浏览器中查看仪表盘和上传Cookie。")
    print("按 Ctrl+C 停止服务器。")

def get_next_cookie_filename(directory):
    try:
        existing_files = os.listdir(directory)
        max_num = 0
        for f in existing_files:
            if f.endswith('.txt'):
                try:
                    num = int(os.path.splitext(f)[0]); max_num = max(max_num, num)
                except ValueError: continue
        return f"{max_num + 1}.txt"
    except Exception: return "1.txt"

@app.route('/', methods=['GET'])
def serve_dashboard():
    # 将密钥注入到HTML模板中
    return Response(HTML_TEMPLATE.replace('__SECRET_KEY_PLACEHOLDER__', SECRET_KEY))

@app.route('/api/status', methods=['GET'])
@require_auth
def get_status_api():
    with lock: return jsonify(latest_status)

@app.route('/status', methods=['POST'])
@require_auth
def receive_status_update():
    global latest_status
    data = request.json
    if not data: return jsonify({"error": "无效的请求"}), 400
    with lock: latest_status = data; latest_status['last_update'] = datetime.now().isoformat()
    display_status_in_console()
    return jsonify({"message": "状态已接收"}), 200

@app.route('/upload-cookie', methods=['POST'])
@require_auth
def upload_cookie():
    cookie_data_str = request.form.get('cookies_data')
    if not cookie_data_str: return jsonify({"error": "Cookie data is empty."}), 400
    try:
        cookies_list = json.loads(cookie_data_str)
        if not isinstance(cookies_list, list): raise ValueError("JSON is not a list.")
    except (json.JSONDecodeError, ValueError) as e: return jsonify({"error": f"Invalid JSON format: {e}"}), 400
    found_keys = {cookie.get('name') for cookie in cookies_list if isinstance(cookie, dict)}
    if 'SESSDATA' not in found_keys or 'bili_jct' not in found_keys:
        return jsonify({"error": "Missing 'SESSDATA' or 'bili_jct' in the cookie data."}), 400
    try:
        filename = get_next_cookie_filename(COOKIE_DIR)
        filepath = os.path.join(COOKIE_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(cookies_list, f, indent=4)
        print(f"新Cookie已保存到: {filepath}")
        return jsonify({"message": f"Success! Cookie saved as {filename}. Uploader will use it on the next cycle."}), 200
    except Exception as e:
        print(f"Error saving cookie file: {e}")
        return jsonify({"error": f"Failed to save the cookie file on the server: {e}"}), 500

if __name__ == '__main__':
    display_status_in_console()
    app.run(host='127.0.0.1', port=7652)