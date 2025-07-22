from flask import Flask, render_template, request, jsonify
import os, subprocess, threading
from io import BytesIO
import zipfile

app = Flask(__name__)
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def run_wget(url, depth, rate, wait):
    with open(LOG_FILE, "w") as log_file:
        cmd = [
            "wget", "--mirror", "--convert-links", "--adjust-extension",
            "--page-requisites", "--no-parent", "--verbose",
            f"--wait={wait}"
        ]
        if depth != "0":
            cmd += ["-l", depth]
        if rate != "unlimited":
            cmd += ["--limit-rate", rate]
        cmd.append(url)

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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

    # Run wget in a temporary directory
    temp_dir = os.path.join(os.getcwd(), 'temp_download')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Store the original working directory
    original_dir = os.getcwd()
    
    try:
        # Change to temp directory
        os.chdir(temp_dir)
        
        # Start the download process
        threading.Thread(target=run_wget, args=(url, depth, rate, wait), daemon=True).start()
        
        domain = url.replace("http://", "").replace("https://", "").split('/')[0]
        return jsonify({'status': 'started', 'domain': domain})
    finally:
        # Change back to original directory
        os.chdir(original_dir)

@app.route('/download', methods=['GET'])
def download():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'status': 'error', 'message': 'Domain not specified'})
    
    temp_dir = os.path.join(os.getcwd(), 'temp_download')
    domain_path = os.path.join(temp_dir, domain)
    
    if not os.path.exists(domain_path):
        return jsonify({'status': 'error', 'message': 'Download not ready or failed'})
    
    # Create zip in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(domain_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, domain_path)
                zipf.write(file_path, arcname)
    memory_file.seek(0)
    
    # Clean up
    shutil.rmtree(domain_path)
    
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=f'{domain}.zip',
        mimetype='application/zip'
    )

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5051))
    app.run(host='0.0.0.0', port=port)
