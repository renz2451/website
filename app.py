from flask import Flask, render_template, request, jsonify
import os
import subprocess
import shutil
import threading
import uuid

app = Flask(__name__)

# Android public Download folder
ANDROID_DOWNLOAD_PATH = "/storage/emulated/0/Download"
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
TEMP_DIR = os.path.join(os.getcwd(), 'temp')

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

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
    unique_id = str(uuid.uuid4())[:6]
    folder_name = f"{domain}_{unique_id}"
    dump_path = os.path.join(TEMP_DIR, folder_name)
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
    return jsonify({'status': 'started', 'default_name': folder_name})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})

    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        if "Saving to:" in line:
            parsed_logs.append(f"💾 {line.strip()}")
        else:
            parsed_logs.append(f"🔄 {line.strip()}")
    return jsonify({'logs': parsed_logs})

@app.route('/rename_and_move', methods=['POST'])
def rename_and_move():
    data = request.json
    old = data['old']
    new = data['new']

    old_path = os.path.join(TEMP_DIR, old)
    new_path = os.path.join(ANDROID_DOWNLOAD_PATH, new)

    try:
        if os.path.exists(new_path):
            shutil.rmtree(new_path)
        shutil.move(old_path, new_path)
        return jsonify({
            'status': 'success',
            'message': f'Saved to {new_path}',
            'url': f"file://{new_path}/index.html"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051))
    app.run(host='0.0.0.0', port=port)
