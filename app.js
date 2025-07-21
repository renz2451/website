let logInterval = null;
let defaultFolder = '';

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
    defaultFolder = result.default_name;
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

  if (data.logs.some(l => l.includes('FINISHED')) || data.logs.length > 0 && data.logs[data.logs.length - 1].includes('100%')) {
    clearInterval(logInterval);
    showRenamePrompt();
  }
}

function showRenamePrompt() {
  const newName = prompt(`✅ Dump completed!\n\nRename folder before saving to /sdcard/Download?`, defaultFolder);
  const rename = newName || defaultFolder;

  fetch('/rename_and_move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old: defaultFolder, new: rename })
  }).then(res => res.json()).then(data => {
    if (data.status === 'success') {
      document.getElementById('logs').innerHTML += `<br><br>✅ Saved to /sdcard/Download/${rename}<br><a href="${data.url}">Open index.html</a>`;
    } else {
      document.getElementById('logs').innerHTML += `<br>❌ Error saving: ${data.message}`;
    }
  });
}