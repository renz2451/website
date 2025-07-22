from flask import Flask, render_template, request, jsonify, send_from_directory
import os, subprocess, shutil, threading

app = Flask(__name__)
# Base directory where files will be saved on the server
SERVER_DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
# Directory you want to appear as "/storage/emulated/0/Download/" in the web interface
WEB_DOWNLOAD_DIR = '/storage/emulated/0/Download/'
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')

os.makedirs(SERVER_DOWNLOAD_DIR, exist_ok=True)
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

    domain = url.replace("http://", "").replace("https://", "").split('/')[0]
    dump_path = os.path.join(SERVER_DOWNLOAD_DIR, domain)
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
    old_path = os.path.join(SERVER_DOWNLOAD_DIR, old)
    new_path = os.path.join(SERVER_DOWNLOAD_DIR, new)

    try:
        shutil.move(old_path, new_path)
        return jsonify({
            'status': 'success',
            'url': f"{WEB_DOWNLOAD_DIR}{new}/index.html"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Serve files from the actual download directory but make them appear to be in the Android path
@app.route('/storage/emulated/0/Download/<path:filename>')
def download_file(filename):
    return send_from_directory(SERVER_DOWNLOAD_DIR, filename)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5051))
    app.run(host='0.0.0.0', port=port)
