from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import shutil
import threading
import uuid
import zipfile

app = Flask(__name__)
BASE_TEMP = os.path.join(os.getcwd(), 'temp')
BASE_ZIP = os.path.join(os.getcwd(), 'zips')
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')

os.makedirs(BASE_TEMP, exist_ok=True)
os.makedirs(BASE_ZIP, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


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

    unique_id = str(uuid.uuid4())[:8]
    domain = url.replace("http://", "").replace("https://", "").split('/')[0]
    folder_name = f"{domain}_{unique_id}"
    dump_path = os.path.join(BASE_TEMP, folder_name)
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
    for line in lines[-50:]:
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


@app.route('/rename_and_download', methods=['POST'])
def rename_and_download():
    data = request.json
    old = data['old']
    new = data['new']
    old_path = os.path.join(BASE_TEMP, old)
    new_path = os.path.join(BASE_ZIP, new)

    if not os.path.exists(old_path):
        return jsonify({'status': 'error', 'message': 'Dump not found'})

    try:
        zip_file = f"{new_path}.zip"
        shutil.make_archive(new_path, 'zip', old_path)
        return jsonify({
            'status': 'success',
            'url': f"/download_zip/{new}.zip"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/download_zip/<filename>')
def download_zip(filename):
    file_path = os.path.join(BASE_ZIP, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051))
    app.run(host='0.0.0.0', port=port)
