#!/usr/bin/env python3
"""
NanoLumens Dark Room Sign - Web Server
Accessible at http://darkroom-sign.local:5000
"""
from flask import Flask, jsonify, request, render_template_string
import json
import os

app = Flask(__name__)
STATE_FILE  = '/home/nano_yiweib/led-sign/state.json'
CONFIG_FILE = '/home/nano_yiweib/led-sign/config.json'

MODES = {
    'idle':        'R&D DARK ROOM',
    'testing':     'TEST IN PROGRESS / DO NOT ENTER',
    'occupied':    'OCCUPIED / OTHER TESTING',
    'unavailable': 'ROOM NOT AVAILABLE',
    'open':        'OPEN / COME ON IN',
    'break':       'ON BREAK / BACK SOON',
    'back5':       'COME BACK IN 5 MIN',
    'back10':      'COME BACK IN 10 MIN',
    'back20':      'COME BACK IN 20 MIN',
    'clock':       'CLOCK',
    'off':         'BLANK / OFF',
}

MODE_COLORS = {
    'idle':        '#3a86ff',
    'testing':     '#e63946',
    'occupied':    '#e63946',
    'unavailable': '#f4a261',
    'open':        '#2a9d8f',
    'break':       '#6c757d',
    'back5':       '#6c757d',
    'back10':      '#6c757d',
    'back20':      '#6c757d',
    'clock':       '#00b4d8',
    'off':         '#343a40',
}

QUICK_COLORS = [
    {'name': 'White',  'hex': '#ffffff'},
    {'name': 'Red',    'hex': '#ff0000'},
    {'name': 'Amber',  'hex': '#f4a261'},
    {'name': 'Green',  'hex': '#2a9d8f'},
    {'name': 'Blue',   'hex': '#3a86ff'},
    {'name': 'Cyan',   'hex': '#00d2d8'},
    {'name': 'Yellow', 'hex': '#ffbe0b'},
    {'name': 'Pink',   'hex': '#ff006e'},
]

def read_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {'mode': 'idle'}

def write_state(mode):
    with open(STATE_FILE, 'w') as f:
        json.dump({'mode': mode}, f)

def read_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except:
        return {'modes': {}}

def write_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dark Room Sign</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0d1117; color: #e6edf3;
      min-height: 100vh; padding: 24px;
    }
    header { text-align: center; margin-bottom: 32px; }
    header h1 { font-size: 24px; font-weight: 700; }
    header p { font-size: 13px; color: #8b949e; margin-top: 4px; }
    #current {
      text-align: center; background: #161b22;
      border: 1px solid #30363d; border-radius: 10px;
      padding: 16px; margin-bottom: 28px;
      font-size: 13px; color: #8b949e;
    }
    #current span { font-weight: 700; font-size: 16px; color: #e6edf3; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; justify-content: center; }
    .tab {
      padding: 8px 20px; border-radius: 8px;
      border: 1px solid #30363d; background: #161b22;
      color: #8b949e; cursor: pointer; font-size: 13px; font-weight: 600;
    }
    .tab.active { background: #2e74b5; color: white; border-color: #2e74b5; }
    .panel { display: none; }
    .panel.active { display: block; }
    .grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px; max-width: 900px; margin: 0 auto;
    }
    .btn {
      display: block; width: 100%; padding: 18px 16px;
      border: none; border-radius: 10px; font-size: 13px;
      font-weight: 600; color: white; cursor: pointer;
      text-align: left; line-height: 1.4;
      transition: opacity 0.15s, transform 0.1s;
    }
    .btn:hover { opacity: 0.85; transform: translateY(-1px); }
    .btn .key {
      display: inline-block; background: rgba(255,255,255,0.2);
      border-radius: 4px; padding: 1px 6px;
      font-size: 11px; margin-bottom: 6px;
    }
    .btn.active { outline: 3px solid white; }
    .config-grid {
      display: grid; grid-template-columns: 1fr;
      gap: 16px; max-width: 700px; margin: 0 auto;
    }
    .config-card {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 10px; padding: 16px;
    }
    .config-card h3 {
      font-size: 13px; font-weight: 700;
      margin-bottom: 14px; display: flex;
      align-items: center; gap: 8px;
    }
    .key-badge {
      background: #30363d; border-radius: 4px;
      padding: 2px 8px; font-size: 11px; color: #8b949e;
    }
    .field-row {
      display: grid; grid-template-columns: 100px 1fr;
      gap: 8px; align-items: center; margin-bottom: 10px;
    }
    .field-row label { font-size: 12px; color: #8b949e; }
    .field-row input[type=text] {
      background: #0d1117; border: 1px solid #30363d;
      border-radius: 6px; color: #e6edf3;
      padding: 6px 10px; font-size: 13px; width: 100%;
    }
    .field-row input[type=text]:focus { outline: none; border-color: #2e74b5; }
    .color-row {
      display: grid; grid-template-columns: 100px 1fr;
      gap: 8px; align-items: flex-start; margin-bottom: 10px;
    }
    .color-row label { font-size: 12px; color: #8b949e; padding-top: 6px; }
    .color-controls { display: flex; flex-direction: column; gap: 6px; }
    .swatches { display: flex; gap: 6px; flex-wrap: wrap; }
    .swatch {
      width: 24px; height: 24px; border-radius: 4px;
      cursor: pointer; border: 2px solid transparent;
      transition: border-color 0.1s;
    }
    .swatch:hover { border-color: white; }
    .swatch.selected { border-color: white; }
    .hex-row { display: flex; gap: 6px; align-items: center; }
    .hex-preview {
      width: 24px; height: 24px; border-radius: 4px;
      border: 1px solid #30363d; flex-shrink: 0;
    }
    .hex-input {
      background: #0d1117; border: 1px solid #30363d;
      border-radius: 6px; color: #e6edf3;
      padding: 4px 8px; font-size: 12px;
      width: 90px; font-family: monospace;
    }
    .hex-input:focus { outline: none; border-color: #2e74b5; }
    .flash-row {
      display: grid; grid-template-columns: 100px 1fr;
      gap: 8px; align-items: center; margin-bottom: 10px;
    }
    .flash-row label { font-size: 12px; color: #8b949e; }
    .toggle {
      display: flex; align-items: center; gap: 8px;
    }
    .toggle input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; }
    .toggle span { font-size: 12px; color: #8b949e; }
    .save-btn {
      margin-top: 12px; padding: 8px 20px;
      background: #2e74b5; border: none; border-radius: 6px;
      color: white; font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .save-btn:hover { background: #1f5a9e; }
    #status {
      text-align: center; margin-top: 24px;
      font-size: 12px; color: #8b949e; height: 20px;
    }
    footer { text-align: center; margin-top: 40px; font-size: 11px; color: #484f58; }
  </style>
</head>
<body>
  <header>
    <h1>R&D Dark Room Sign</h1>
    <p>NanoLumens — darkroom-sign.local</p>
  </header>
  <div id="current">
    Current mode: <span id="current-mode">loading...</span>
  </div>
  <div class="tabs">
    <button class="tab active" onclick="showTab('control', this)">Control</button>
    <button class="tab" onclick="showTab('config', this)">Edit Messages</button>
  </div>
  <div id="control" class="panel active">
    <div class="grid" id="grid"></div>
  </div>
  <div id="config" class="panel">
    <div class="config-grid" id="config-grid"></div>
  </div>
  <div id="status"></div>
  <footer>Changes apply instantly to both displays &bull; v2.0-dev</footer>

  <script>
    const MODES  = {{ modes|tojson }};
    const COLORS = {{ colors|tojson }};
    const QUICK  = {{ quick_colors|tojson }};
    const KEY_LABELS = {
      idle:'0', testing:'2', occupied:'3', unavailable:'4',
      open:'5', break:'6', back5:'7', back10:'8', back20:'9',
      clock:'1', off:'Enter'
    };
    const ORDER = ['clock','testing','occupied','unavailable','open','break','back5','back10','back20','idle','off'];
    const EDITABLE = ['testing','occupied','unavailable','open','break','back5','back10','back20','idle'];

    let currentMode = null;

    function showTab(tab, el) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById(tab).classList.add('active');
      el.classList.add('active');
      if (tab === 'config') buildConfigGrid();
    }

    function setStatus(msg, duration=2500) {
      const el = document.getElementById('status');
      el.textContent = msg;
      if (duration) setTimeout(() => el.textContent = '', duration);
    }

    function refreshCurrent() {
      fetch('/api/state').then(r => r.json()).then(data => {
        currentMode = data.mode;
        document.getElementById('current-mode').textContent = MODES[data.mode] || data.mode;
        document.querySelectorAll('.btn').forEach(b => {
          b.classList.toggle('active', b.dataset.mode === data.mode);
        });
      });
    }

    function buildGrid() {
      const grid = document.getElementById('grid');
      ORDER.forEach(mode => {
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.dataset.mode = mode;
        btn.style.background = COLORS[mode];
        btn.innerHTML = `<span class="key">${KEY_LABELS[mode]}</span><span class="label">${MODES[mode]}</span>`;
        btn.addEventListener('click', () => {
          fetch('/api/mode/' + mode, {method:'POST'})
            .then(r => r.json())
            .then(() => { setStatus('Updated to: ' + MODES[mode]); refreshCurrent(); })
            .catch(() => setStatus('Error — check Pi connection'));
        });
        grid.appendChild(btn);
      });
    }

    // -- Color picker helpers --------------------------------------------------
    function makeColorPicker(fieldId, initialHex) {
      const wrap = document.createElement('div');
      wrap.className = 'color-controls';

      // Swatches
      const swatches = document.createElement('div');
      swatches.className = 'swatches';
      QUICK.forEach(c => {
        const s = document.createElement('div');
        s.className = 'swatch' + (c.hex === initialHex ? ' selected' : '');
        s.style.background = c.hex;
        s.title = c.name;
        s.addEventListener('click', () => {
          wrap.querySelectorAll('.swatch').forEach(x => x.classList.remove('selected'));
          s.classList.add('selected');
          document.getElementById(fieldId).value = c.hex;
          document.getElementById(fieldId + '-preview').style.background = c.hex;
        });
        swatches.appendChild(s);
      });
      wrap.appendChild(swatches);

      // Hex input
      const hexRow = document.createElement('div');
      hexRow.className = 'hex-row';
      const preview = document.createElement('div');
      preview.className = 'hex-preview';
      preview.id = fieldId + '-preview';
      preview.style.background = initialHex;
      const hexIn = document.createElement('input');
      hexIn.type = 'text';
      hexIn.className = 'hex-input';
      hexIn.id = fieldId;
      hexIn.value = initialHex;
      hexIn.maxLength = 7;
      hexIn.placeholder = '#ffffff';
      hexIn.addEventListener('input', () => {
        const v = hexIn.value;
        if (/^#[0-9a-fA-F]{6}$/.test(v)) {
          preview.style.background = v;
          wrap.querySelectorAll('.swatch').forEach(s => {
            s.classList.toggle('selected', s.style.background === v || rgbToHex(s.style.background) === v.toLowerCase());
          });
        }
      });
      hexRow.appendChild(preview);
      hexRow.appendChild(hexIn);
      wrap.appendChild(hexRow);
      return wrap;
    }

    function rgbToHex(rgb) {
      const m = rgb.match(/\d+/g);
      if (!m) return rgb;
      return '#' + m.slice(0,3).map(x => parseInt(x).toString(16).padStart(2,'0')).join('');
    }

    function buildConfigGrid() {
      fetch('/api/config').then(r => r.json()).then(data => {
        const modes = data.modes || {};
        const grid = document.getElementById('config-grid');
        grid.innerHTML = '';

        EDITABLE.forEach(mode => {
          const cfg = modes[mode] || {};
          const card = document.createElement('div');
          card.className = 'config-card';

          const h3 = document.createElement('h3');
          h3.innerHTML = `<span class="key-badge">Key ${KEY_LABELS[mode]}</span> ${MODES[mode]}`;
          card.appendChild(h3);

          // Line 1 text
          card.appendChild(makeFieldRow('Line 1', `l1-${mode}`, cfg.line1 || ''));
          // Line 2 text
          card.appendChild(makeFieldRow('Line 2', `l2-${mode}`, cfg.line2 || ''));

          // Line 1 color
          const cr1 = document.createElement('div');
          cr1.className = 'color-row';
          const lb1 = document.createElement('label'); lb1.textContent = 'Line 1 color';
          cr1.appendChild(lb1);
          cr1.appendChild(makeColorPicker(`c1-${mode}`, cfg.color1 || '#ffffff'));
          card.appendChild(cr1);

          // Line 2 color
          const cr2 = document.createElement('div');
          cr2.className = 'color-row';
          const lb2 = document.createElement('label'); lb2.textContent = 'Line 2 color';
          cr2.appendChild(lb2);
          cr2.appendChild(makeColorPicker(`c2-${mode}`, cfg.color2 || '#ffffff'));
          card.appendChild(cr2);

          // Border color
          const cr3 = document.createElement('div');
          cr3.className = 'color-row';
          const lb3 = document.createElement('label'); lb3.textContent = 'Border color';
          cr3.appendChild(lb3);
          cr3.appendChild(makeColorPicker(`cb-${mode}`, cfg.border_color || '#ffffff'));
          card.appendChild(cr3);

          // Flash toggle
          const fr = document.createElement('div');
          fr.className = 'flash-row';
          const fbl = document.createElement('label'); fbl.textContent = 'Flash';
          const tog = document.createElement('div'); tog.className = 'toggle';
          const cb = document.createElement('input');
          cb.type = 'checkbox'; cb.id = `fl-${mode}`; cb.checked = cfg.flash || false;
          const sp = document.createElement('span');
          sp.textContent = 'Flash line 2 and border on/off';
          tog.appendChild(cb); tog.appendChild(sp);
          fr.appendChild(fbl); fr.appendChild(tog);
          card.appendChild(fr);

          // Save button
          const btn = document.createElement('button');
          btn.className = 'save-btn';
          btn.textContent = 'Save';
          btn.addEventListener('click', () => saveMode(mode));
          card.appendChild(btn);

          grid.appendChild(card);
        });
      });
    }

    function makeFieldRow(label, id, value) {
      const row = document.createElement('div');
      row.className = 'field-row';
      const lb = document.createElement('label'); lb.textContent = label;
      const inp = document.createElement('input');
      inp.type = 'text'; inp.id = id; inp.value = value; inp.maxLength = 30;
      row.appendChild(lb); row.appendChild(inp);
      return row;
    }

    function saveMode(mode) {
      const line1        = document.getElementById(`l1-${mode}`).value.toUpperCase();
      const line2        = document.getElementById(`l2-${mode}`).value.toUpperCase();
      const color1       = document.getElementById(`c1-${mode}`).value;
      const color2       = document.getElementById(`c2-${mode}`).value;
      const border_color = document.getElementById(`cb-${mode}`).value;
      const flash        = document.getElementById(`fl-${mode}`).checked;

      fetch('/api/config/' + mode, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({line1, line2, color1, color2, border_color, flash})
      })
      .then(r => r.json())
      .then(() => setStatus('Saved! Press the mode button or numpad key to see changes.'))
      .catch(() => setStatus('Error saving — check Pi connection'));
    }

    buildGrid();
    refreshCurrent();
    setInterval(refreshCurrent, 3000);
  </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML, modes=MODES, colors=MODE_COLORS, quick_colors=QUICK_COLORS)

@app.route('/api/state')
def get_state():
    return jsonify(read_state())

@app.route('/api/mode/<mode>', methods=['POST'])
def set_mode(mode):
    if mode not in MODES:
        return jsonify({'error': 'invalid mode'}), 400
    write_state(mode)
    return jsonify({'ok': True, 'mode': mode})

@app.route('/api/config')
def get_config():
    return jsonify(read_config())

@app.route('/api/config/<mode>', methods=['POST'])
def set_config(mode):
    if mode not in MODES:
        return jsonify({'error': 'invalid mode'}), 400
    data = request.get_json()
    config = read_config()
    if 'modes' not in config:
        config['modes'] = {}
    config['modes'][mode] = {
        'line1':        data.get('line1', '').strip().upper(),
        'line2':        data.get('line2', '').strip().upper(),
        'color1':       data.get('color1', '#ffffff'),
        'color2':       data.get('color2', '#ffffff'),
        'border_color': data.get('border_color', '#ffffff'),
        'flash':        bool(data.get('flash', False)),
    }
    write_config(config)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)