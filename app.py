from flask import Flask, render_template, request, jsonify
import os, subprocess, time, shutil, threading, zipfile, requests

app = Flask(__name__)
BASE_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
DEBUG_LOG = os.path.join(os.getcwd(), 'logs', 'debug.log')
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

BOT_TOKEN = '7342786184:AAFT2dsNEgPiHasA2f1fP08M_QwxVS1ARYg'
CHAT_ID = '6064653643'

def log_debug(message):
    with open(DEBUG_LOG, 'a') as f:
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        f.write(f"{timestamp} {message}\n")
    print(f"[DEBUG] {message}")

def send_to_telegram(file_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        files = {'document': (os.path.basename(file_path), f)}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data)
    return response.ok

def run_wget(command):
    log_debug("Starting wget command...")
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        process.wait()
    log_debug("wget command completed.")

def zip_folder(folder_path, output_path):
    log_debug(f"Zipping folder: {folder_path}")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, folder_path)
                zipf.write(full_path, rel_path)
    log_debug(f"Created ZIP: {output_path}")

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

    def task():
        try:
            run_wget(cmd)
            zip_path = f"{dump_path}.zip"
            zip_folder(dump_path, zip_path)
            success = send_to_telegram(zip_path, f"📦 Dumped site: {domain}")
            if success:
                log_debug("✅ ZIP sent to Telegram successfully.")
                os.remove(zip_path)
                log_debug("🧹 Removed local ZIP.")
            else:
                log_debug("❌ Failed to send to Telegram.")
        except Exception as e:
            log_debug(f"⚠️ Error during process: {str(e)}")

    threading.Thread(target=task, daemon=True).start()
    return jsonify({'status': 'started', 'message': f"Dumping {domain} and sending to Telegram..."})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        parsed_logs.append(line.strip())
    return jsonify({'logs': parsed_logs})

@app.route('/debug')
def get_debug():
    if not os.path.exists(DEBUG_LOG):
        return jsonify({'debug': []})
    with open(DEBUG_LOG, 'r') as f:
        return jsonify({'debug': f.readlines()[-30:]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
