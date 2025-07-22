
from flask import Flask, render_template, request, jsonify
import os, subprocess, time, shutil, threading, zipfile, requests

app = Flask(__name__)
BASE_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Telegram credentials
TELEGRAM_TOKEN = "7342786184:AAFT2dsNEgPiHasA2f1fP08M_QwxVS1ARYg"
CHAT_ID = "6064653643"

def run_wget_and_send(cmd, domain):
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        process.wait()

    # Create zip of the downloaded folder
    dump_path = os.path.join(BASE_DIR, domain)
    zip_path = dump_path + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dump_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dump_path)
                zipf.write(abs_path, rel_path)

    # Send zip to Telegram
    with open(zip_path, 'rb') as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
            data={"chat_id": CHAT_ID},
            files={"document": f}
        )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dump', methods=['POST'])
def dump():
    data = request.json
    url = data['url']
    depth = data.get('depth', '0')
    rate = data.get('rate', 'unlimited')
    wait = data.get('wait', '1')

    if not url.startswith(('http://', 'https://')):
        return jsonify({'status': 'error', 'message': 'Invalid URL'})

    domain = url.replace("http://", "").replace("https://", "").split('/')[0]
    dump_path = os.path.join(BASE_DIR, domain)
    os.makedirs(dump_path, exist_ok=True)

    cmd = [
        "wget", "--mirror", "--convert-links", "--adjust-extension",
        "--page-requisites", "--no-parent", "--verbose",
        f"--wait={wait}", f"--directory-prefix={dump_path}"
    ]
    if depth != "0":
        cmd += ["-l", depth]
    if rate != "unlimited":
        cmd += ["--limit-rate", rate]
    cmd.append(url)

    threading.Thread(target=run_wget_and_send, args=(cmd, domain), daemon=True).start()
    return jsonify({'status': 'started', 'default_name': domain})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        if "Saving to:" in line or ".html" in line or ".css" in line or ".js" in line or ".jpg" in line or ".png" in line or ".mp4" in line:
            if ".html" in line:
                prefix = "📄 HTML"
            elif ".css" in line:
                prefix = "🎨 CSS"
            elif ".js" in line:
                prefix = "📜 JS"
            elif any(ext in line for ext in ['.jpg', '.png', '.jpeg', '.gif']):
                prefix = "🖼️ Image"
            elif ".mp4" in line:
                prefix = "🎥 Video"
            else:
                prefix = "🧩 File"
            parsed_logs.append(f"{prefix}: {line.strip()}")
        else:
            parsed_logs.append(f"🔄 {line.strip()}")
    return jsonify({'logs': parsed_logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
