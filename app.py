from flask import Flask, request, jsonify, render_template
import os, subprocess, time, shutil, threading, zipfile, ftplib

app = Flask(__name__)
BASE_DIR = os.path.join(os.getcwd(), 'downloads')
LOG_FILE = os.path.join(os.getcwd(), 'logs', 'latest.log')
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ✅ Replace these with your x10hosting FTP credentials
FTP_HOST = "ftp.my-angge.x10.bz"
FTP_USER = "fknmbldh_my-angge"
FTP_PASS = "my-angge"
FTP_UPLOAD_DIR = "/public_html/downloads"

def run_wget(command):
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        process.wait()

def zip_directory(source_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zipf.write(full_path, rel_path)

def upload_to_ftp(local_path, remote_filename):
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_UPLOAD_DIR)
        with open(local_path, 'rb') as file:
            ftp.storbinary(f"STOR {remote_filename}", file)

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

    def do_dump():
        run_wget(cmd)
        zip_path = os.path.join(BASE_DIR, f"{domain}.zip")
        zip_directory(os.path.join(dump_path, domain), zip_path)
        try:
            upload_to_ftp(zip_path, f"{domain}.zip")
        except Exception as e:
            print("FTP upload failed:", str(e))

    threading.Thread(target=do_dump, daemon=True).start()
    return jsonify({
        'status': 'started',
        'message': f'Dumping {url}, will be uploaded soon...',
        'download_link': f"https://my-angge.x10.bz/downloads/{domain}.zip"
    })

@app.route('/logs')
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({'logs': []})
    with open(LOG_FILE, 'r') as file:
        lines = file.readlines()

    parsed_logs = []
    for line in lines[-30:]:
        parsed_logs.append(f"🔄 {line.strip()}")
    return jso
nify({'logs': parsed_logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
