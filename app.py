from flask import Flask, render_template, request, jsonify
import os, subprocess, shutil, threading, time

app = Flask(__name__)

# ✅ Android-friendly storage location (e.g. Termux or Pydroid)
BASE_DIR = '/storage/emulated/0/WebsiteDumps'
LOG_FILE = os.path.join(BASE_DIR, 'latest.log')
os.makedirs(BASE_DIR, exist_ok=True)

def run_wget(command):
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        process.wait()

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

    threading.Thread(target=run_wget, args=(cmd,), daemon=True).start()
    return jsonify({'status': 'started', 'default_name': domain})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        if "Saving to:" in line or any(ext in line for ext in ['.html', '.css', '.js', '.jpg', '.png', '.jpeg', '.gif', '.mp4']):
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

@app.route('/rename_and_move', methods=['POST'])
def rename_and_move():
    data = request.json
    old = data['old']
    new = data['new']
    old_path = os.path.join(BASE_DIR, old)
    new_path = os.path.join(BASE_DIR, new)

    # ⏳ Wait for dump to appear (up to 20s)
    for i in range(20):
        if os.path.exists(old_path):
            break
        time.sleep(1)
    else:
        return jsonify({'status': 'error', 'message': f'Dump folder \"{old}\" not found after waiting.'})

    try:
        if os.path.exists(new_path):
            return jsonify({'status': 'error', 'message': f'Target folder \"{new}\" already exists.'})
        shutil.move(old_path, new_path)
        return jsonify({'status': 'success', 'url': f'/sdcard/WebsiteDumps/{new}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
