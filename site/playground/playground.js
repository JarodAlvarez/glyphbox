/* GLYPHBOX Playground: edit Lua and sprites, run them in the real console runtime (WASM). */
(() => {
'use strict';

const ASSET_BYTES = 2304;          // sprites 1024 + tilemap 512 + sfx 512 + music 256
const STORE_KEY = 'glyphbox-playground-v1';

const HELLO = `-- HELLO GLYPHBOX
-- Arrows move the ball. Z or Space plays a note.
-- Press Ctrl+Enter (Cmd+Enter on a Mac) to run.

function _init()
  x, y = 64, 64
end

function _update()
  if btn(BTN_L) then x = x - 2 end
  if btn(BTN_R) then x = x + 2 end
  if btn(BTN_U) then y = y - 2 end
  if btn(BTN_D) then y = y + 2 end
  x = clamp(x, 6, 121)
  y = clamp(y, 22, 105)
  if btnp(BTN_A) then sfx(0, 60, 8, 0, 6) end
end

function _draw()
  cls(0)
  print("HELLO GLYPHBOX", 22, 6, 1)
  rect(0, 16, 128, 96, 1)
  circf(x, y, 5, 1)
  spr(0, 4, 116)
  hint(70, 116) print("BEEP", 89, 116, 1)
end
`;

/* ── State ─────────────────────────────────────────────────────────────── */
const state = { code: HELLO, assets: new Uint8Array(ASSET_BYTES), example: 'hello', tile: 0 };
// default sprite 0: a small smiley so spr(0, ...) shows something
[0x3c, 0x42, 0xa5, 0x81, 0xa5, 0x99, 0x42, 0x3c].forEach((b, i) => state.assets[i] = b);

function save() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      code: state.code, example: state.example, tile: state.tile,
      assets: btoa(String.fromCharCode(...state.assets)),
    }));
  } catch (e) { /* storage blocked: the playground still works, it just won't remember */ }
}
function restore() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
    if (!s) return;
    state.code = s.code ?? state.code;
    state.example = s.example ?? state.example;
    state.tile = s.tile ?? 0;
    if (s.assets) state.assets = Uint8Array.from(atob(s.assets), c => c.charCodeAt(0)).slice(0, ASSET_BYTES);
  } catch (e) { /* ignore */ }
}
restore();

/* ── Output log ────────────────────────────────────────────────────────── */
const logEl = document.getElementById('log');
let lastLine = '', repeat = 0;
function log(text, cls) {
  if (text === lastLine) {            // the runtime repeats a failing _update every frame
    repeat++;
    const last = logEl.lastElementChild;
    if (last) last.dataset.n = repeat, last.textContent = `${text}  (×${repeat + 1})`;
    return;
  }
  lastLine = text; repeat = 0;
  const line = document.createElement('div');
  if (cls) line.className = cls;
  line.textContent = text.replace(/^GLYPHBOX( \[[^\]]*\])?: ?/, '');
  logEl.appendChild(line);
  while (logEl.childNodes.length > 200) logEl.removeChild(logEl.firstChild);
  logEl.scrollTop = logEl.scrollHeight;
}
document.getElementById('clear-log').onclick = () => { logEl.textContent = ''; lastLine = ''; };

/* ── Runtime (Emscripten Module; glyphbox.js loads after this file) ───── */
let ready = false, pendingRun = false;
window.GlyphboxScanner = {        // the runtime asks for a scan from the splash: run the code instead
  start() { runGame(); }, stop() {}, showScanButton() {},
};
window.Module = {
  // same version string as the glyphbox.js tag, so a new build is never mixed with a cached .wasm
  locateFile: (f, dir) => dir + f + (document.querySelector('script[src*="glyphbox.js"]')?.src.split('?')[1] ? '?' + document.querySelector('script[src*="glyphbox.js"]').src.split('?')[1] : ''),
  canvas: document.getElementById('canvas'),
  print: t => { if (t && !/^(Scanning|═)/.test(t)) log(t); },
  printErr: t => { if (!t) return; const err = /error|attempt|expected|nil/i.test(t); if (err || !/^warning/i.test(t)) log(t, err ? 'err' : ''); },
  onRuntimeInitialized() { ready = true; setTimeout(() => document.title = 'GLYPHBOX Playground', 0); log('Console ready. Press RUN or Ctrl+Enter.'); if (pendingRun) runGame(); },
};

function runGame() {
  if (!ready) { pendingRun = true; log('Starting the console…'); return; }
  pendingRun = false;
  const M = window.Module;
  const src = new TextEncoder().encode(editor ? editor.getValue() : state.code);
  const sp = M._malloc(src.length + 1), ap = M._malloc(ASSET_BYTES);
  M.HEAPU8.set(src, sp); M.HEAPU8[sp + src.length] = 0;
  M.HEAPU8.set(state.assets, ap);
  logEl.textContent = ''; lastLine = '';
  const ok = M.ccall('web_load_source', 'number',
    ['number', 'number', 'number', 'number', 'string', 'number'],
    [sp, src.length, ap, ASSET_BYTES, exampleTitle(), 1]);
  M._free(sp); M._free(ap);
  log(ok ? 'Running.' : 'Could not start: see the error above.', ok ? '' : 'err');
  document.getElementById('canvas').focus();
}
document.getElementById('run').onclick = runGame;

/* ── Code editor ───────────────────────────────────────────────────────── */
const editor = CodeMirror.fromTextArea(document.getElementById('code'), {
  mode: 'lua', lineNumbers: true, indentUnit: 2, tabSize: 2, smartIndent: true,
  matchBrackets: true, lineWrapping: false,
  extraKeys: {
    'Ctrl-Enter': runGame, 'Cmd-Enter': runGame, 'Ctrl-S': runGame, 'Cmd-S': runGame,
    Tab: cm => cm.replaceSelection('  '),
  },
});
editor.setValue(state.code);
let saveTimer;
editor.on('change', (cm, ch) => {
  state.code = editor.getValue();
  if (ch.origin !== 'setValue') state.dirty = true;
  clearTimeout(saveTimer); saveTimer = setTimeout(() => { save(); estimate(); }, 400);
});
addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && (e.key === 'Enter' || e.key === 's')) { e.preventDefault(); runGame(); }
});

/* ── Tabs ──────────────────────────────────────────────────────────────── */
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#tabs li').forEach(li => li.classList.toggle('sel', li.contains(b)));
  const tab = b.dataset.tab;
  document.getElementById('pane-code').hidden = tab !== 'code';
  document.getElementById('pane-sprites').hidden = tab !== 'sprites';
  document.getElementById('filename').textContent = tab === 'code' ? 'game.lua' : 'sprites.txt';
  if (tab === 'code') editor.refresh(); else drawSprites();
  glyphText(document.getElementById('tabs'));
});

/* ── Sprite editor ─────────────────────────────────────────────────────── */
const sheet = document.getElementById('sheet'), sctx = sheet.getContext('2d');
const tileCv = document.getElementById('tile'), tctx = tileCv.getContext('2d');
const INK = '#f0f0ec', PAPER = '#080808';
const px = (t, x, y) => (state.assets[t * 8 + y] >> (7 - x)) & 1;
const setPx = (t, x, y, v) => {
  const i = t * 8 + y, m = 1 << (7 - x);
  state.assets[i] = v ? state.assets[i] | m : state.assets[i] & ~m;
};
function drawSprites() {
  sctx.fillStyle = PAPER; sctx.fillRect(0, 0, 128, 64);
  sctx.fillStyle = INK;
  // the selected tile is drawn inverted, like a selected menu row
  for (let t = 0; t < 128; t++) {
    const ox = (t % 16) * 8, oy = Math.floor(t / 16) * 8, sel = t === state.tile;
    for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++)
      if (px(t, x, y) ^ sel) sctx.fillRect(ox + x, oy + y, 1, 1);
  }

  tctx.clearRect(0, 0, 8, 8);
  tctx.fillStyle = INK;
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) if (px(state.tile, x, y)) tctx.fillRect(x, y, 1, 1);
  const id = String(state.tile).padStart(3, '0');
  document.getElementById('tile-id').textContent = `SPRITE ${id}`;
  document.getElementById('tile-use').textContent = `spr(${state.tile}, x, y)`;
}
tileCv.style.backgroundSize = `${288 / 8}px ${288 / 8}px`;
sheet.onclick = e => {
  const r = sheet.getBoundingClientRect();
  const tx = Math.floor((e.clientX - r.left) / r.width * 16), ty = Math.floor((e.clientY - r.top) / r.height * 8);
  state.tile = Math.max(0, Math.min(127, ty * 16 + tx)); drawSprites(); save();
};
let painting = null;
function tileAt(e) {
  const r = tileCv.getBoundingClientRect();
  return [Math.floor((e.clientX - r.left) / r.width * 8), Math.floor((e.clientY - r.top) / r.height * 8)];
}
tileCv.addEventListener('pointerdown', e => {
  const [x, y] = tileAt(e); if (x < 0 || y < 0 || x > 7 || y > 7) return;
  painting = px(state.tile, x, y) ? 0 : 1; setPx(state.tile, x, y, painting);
  tileCv.setPointerCapture(e.pointerId); drawSprites();
});
tileCv.addEventListener('pointermove', e => {
  if (painting === null) return;
  const [x, y] = tileAt(e); if (x < 0 || y < 0 || x > 7 || y > 7) return;
  setPx(state.tile, x, y, painting); drawSprites();
});
tileCv.addEventListener('pointerup', () => { painting = null; save(); estimate(); });
document.querySelectorAll('#tile-tools button').forEach(b => b.onclick = () => {
  const t = state.tile, rows = [...state.assets.slice(t * 8, t * 8 + 8)];
  const rev = v => parseInt(v.toString(2).padStart(8, '0').split('').reverse().join(''), 2);
  const out = { clear: rows.map(() => 0), invert: rows.map(v => v ^ 0xff), fliph: rows.map(rev), flipv: rows.reverse() }[b.dataset.op];
  out.forEach((v, i) => state.assets[t * 8 + i] = v);
  drawSprites(); save(); estimate();
});

/* ── Card budget (estimate) ────────────────────────────────────────────── */
// Calibrated on the shipped carts: LuaJIT bytecode compresses to ~1.45x the
// deflated source. Cards double (1, 2, 4, 8) at 800 bytes each, like card-print.py.
async function deflatedSize(bytes) {
  if (!('CompressionStream' in window)) return bytes.length * 0.5;
  const cs = new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate'));
  return (await new Response(cs).arrayBuffer()).byteLength;
}
async function estimate() {
  const src = new TextEncoder().encode(state.code);
  const z = 1.45 * await deflatedSize(src) + await deflatedSize(state.assets) + 40;
  let n = 1; while (z > n * 800 && n < 16) n *= 2;
  const over = n > 8;
  document.getElementById('budget-text').textContent = over ? 'OVER 8 CARDS' : `≈ ${n} / 8 CARDS`;
  const pips = document.getElementById('pips');
  pips.classList.toggle('over', over);
  [...pips.children].forEach((p, i) => p.classList.toggle('on', i < Math.min(n, 8)));
}

/* ── Examples ──────────────────────────────────────────────────────────── */
let examples = [{ id: 'hello', title: 'HELLO' }];
function exampleTitle() { return (examples.find(x => x.id === state.example) || { title: 'PLAYGROUND' }).title; }
async function loadExample(id) {
  if (id === 'hello') {
    state.code = HELLO; state.assets = new Uint8Array(ASSET_BYTES);
    [0x3c, 0x42, 0xa5, 0x81, 0xa5, 0x99, 0x42, 0x3c].forEach((b, i) => state.assets[i] = b);
  } else {
    const [code, bin] = await Promise.all([
      fetch(`examples/${id}.lua`).then(r => r.text()),
      fetch(`examples/${id}.bin`).then(r => r.arrayBuffer()),
    ]);
    state.code = code; state.assets = new Uint8Array(bin);
  }
  state.example = id; state.tile = 0;
  editor.setValue(state.code); editor.clearHistory(); state.dirty = false;
  drawSprites(); renderExamples(); save(); estimate(); runGame();
}
function renderExamples() {
  const ul = document.getElementById('examples'); ul.innerHTML = '';
  examples.forEach(ex => {
    const li = document.createElement('li'); if (ex.id === state.example) li.className = 'cur';
    const b = document.createElement('button'); b.textContent = ex.title;
    b.onclick = () => {
      if (!state.dirty || confirm(`Load ${ex.title}? This replaces your code and sprites.`)) loadExample(ex.id);
    };
    li.appendChild(b); ul.appendChild(li);
  });
}
fetch('examples/index.json').then(r => r.json()).then(list => { examples = examples.concat(list); renderExamples(); })
  .catch(() => renderExamples());

/* ── Downloads ─────────────────────────────────────────────────────────── */
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
  a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
document.getElementById('dl-lua').onclick = () => download('game.lua', editor.getValue());
document.getElementById('dl-spr').onclick = () => {
  const tiles = [];
  for (let t = 0; t < 128; t++) {
    const rows = []; for (let y = 0; y < 8; y++) rows.push(state.assets[t * 8 + y].toString(2).padStart(8, '0'));
    tiles.push(rows.join('\n'));
  }
  download('sprites.txt', tiles.join('\n\n') + '\n');
};

/* ── Boot ──────────────────────────────────────────────────────────────── */
document.querySelectorAll('[data-logo]').forEach(el =>
  fetch(`../logo/${el.dataset.logo}.svg`).then(r => r.text()).then(t => el.innerHTML = t));
glyphText();
drawSprites();
estimate();

// for debugging from the console
window.GBPlayground = { state, runGame, loadExample };
})();
