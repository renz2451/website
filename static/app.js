let logInterval = null;
let tempPath = '';

document.getElementById('dumpForm').onsubmit = async function(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    url: form.url.value,
    depth: form.depth.value || '0',
    rate: form.rate.value || 'unlimited',
    wait: form.wait.value || '1'
  };

  document.getElementById('logs').innerText = '⏳ Starting dump...';
  const res = await fetch('/dump', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const result = await res.json();
  if (result.status === 'started') {
    tempPath = result.temp_path;
    logInterval = setInterval(fetchLogs, 1000);
  } else {
    document.getElementById('logs').innerText = '❌ Error: ' + result.message;
  }
};

async function fetchLogs() {
  const res = await fetch('/logs');
  const data = await res.json();
  const logDiv = document.getElementById('logs');
  logDiv.innerHTML = data.logs.join('<br>');

  if (data.logs.some(l => l.includes('FINISHED')) || data.logs.some(l => l.includes('100%'))) {
    clearInterval(logInterval);
    promptRenameAndDownload();
  }
}

function promptRenameAndDownload() {
  const rename = prompt("✅ Dump completed! Enter filename for download:", "my_dump");
  if (!rename) return;

  fetch('/rename_and_download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temp_path: tempPath, new_name: rename })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        document.getElementById('logs').innerHTML += `<br><br>✅ Download ready: <a href="${data.url}" target="_blank">Download ZIP</a>`;
      } else {
        document.getElementById('logs').innerHTML += `<br>❌ ${data.message}`;
      }
    });
}
