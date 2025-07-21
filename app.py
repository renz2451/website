from flask import Flask, render_template, request, jsonify, send_file
import os, subprocess, shutil, threading, tempfile

app = Flask(__name__)
BASE_DIR = '/storage/emulated/0/Download/webdumps'
os.makedirs(BASE_DIR, exist_ok=True)
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
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
    temp_dir = tempfile.mkdtemp()
    
    cmd = [
        "wget", "--mirror", "--convert-links", "--adjust-extension",
        "--page-requisites", "--no-parent", "--verbose",
        f"--wait={wait}", f"--directory-prefix={temp_dir}"
    ]
    if depth != "0":
        cmd += ["-l", depth]
    if rate != "unlimited":
        cmd += ["--limit-rate", rate]
    cmd.append(url)

    threading.Thread(target=run_wget, args=(cmd,), daemon=True).start()
    return jsonify({'status': 'started', 'default_name': domain, 'temp_path': temp_dir})

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

@app.route('/rename_and_download', methods=['POST'])
def rename_and_download():
    data = request.json
    new = data['new']
    temp_path = data['temp_path']
    new_path = os.path.join(BASE_DIR, new)

    try:
        shutil.move(temp_path, new_path)
        zip_name = new_path + ".zip"
        shutil.make_archive(new_path, 'zip', new_path)
        return jsonify({'status': 'success', 'url': f"/download_zip/{new}.zip"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download_zip/<path:filename>')
def download_zip(filename):
    file_path = os.path.join(BASE_DIR, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051))
    app.run(host='0.0.0.0', port=port)
        
