from flask import Flask, render_template, request, jsonify, send_file
import os, subprocess, threading, shutil, zipfile, uuid

app = Flask(__name__)
TEMP_DIR = os.path.join(os.getcwd(), 'temp')
OUTPUT_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
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
    temp_folder = os.path.join(TEMP_DIR, unique_id)
    os.makedirs(temp_folder, exist_ok=True)

    cmd = [
        "wget", "--mirror", "--convert-links", "--adjust-extension",
        "--page-requisites", "--no-parent", "--verbose",
        f"--wait={wait}", f"--directory-prefix={temp_folder}"
    ]
    if depth != "0":
        cmd += ["-l", depth]
    if rate != "unlimited":
        cmd += ["--limit-rate", rate]
    cmd.append(url)

    threading.Thread(target=run_wget, args=(cmd,), daemon=True).start()
    return jsonify({'status': 'started', 'temp_path': unique_id})

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        parsed_logs.append(f"🔄 {line.strip()}")
    return jsonify({'logs': parsed_logs})

@app.route('/rename_and_download', methods=['POST'])
def rename_and_download():
    data = request.json
    temp_id = data['temp_path']
    new_name = data['new_name']

    temp_folder = os.path.join(TEMP_DIR, temp_id)
    final_path = os.path.join(OUTPUT_DIR, new_name)
    zip_path = final_path + ".zip"

    try:
        shutil.move(temp_folder, final_path)
        shutil.make_archive(final_path, 'zip', final_path)
        return jsonify({
            'status': 'success',
            'url': f"/download_zip/{new_name}.zip"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download_zip/<filename>')
def download_zip(filename):
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
