/* GLYPHBOX site pages: logos, pixel headings, menu rows, and live examples
   that run on the page's console (the real runtime, compiled to WebAssembly). */
(() => {
'use strict';
const ROOT = window.GB_ROOT || './';
const PAGE_TITLE = document.title;          // SDL renames the page when it opens its window

document.querySelectorAll('[data-logo]').forEach(el =>
  fetch(`${ROOT}logo/${el.dataset.logo}.svg`).then(r => r.text()).then(t => el.innerHTML = t));

/* hovering a menu row moves the selection bar, like the console menu */
document.querySelectorAll('.menu').forEach(ul => {
  const rows = [...ul.children];
  rows.forEach(r => r.addEventListener('mouseenter', () => {
    rows.forEach(x => x.classList.toggle('sel', x === r)); glyphText(ul);
  }));
});
glyphText();

/* ── Live examples ───────────────────────────────────────────────────────── */
const canvas = document.getElementById('canvas');
if (!canvas) return;

const ASSETS = 2304;                       // sprites, tilemap, sfx, music
const assets = new Uint8Array(ASSETS);     // sprite 0: a smiley for the examples
[0x3c, 0x42, 0xa5, 0x81, 0xa5, 0x99, 0x42, 0x3c].forEach((b, i) => assets[i] = b);

const out = document.getElementById('out');
let ready = false, pending = null, last = null, lastLine = '';
function log(t, err) {
  if (!t || t === lastLine) return;
  lastLine = t;
  const d = document.createElement('div');
  if (err) d.className = 'err';
  d.textContent = t.replace(/^GLYPHBOX( \[[^\]]*\])?: ?/, '').replace(/^\[string "[^"]*"\]/, 'line');
  out.appendChild(d);
  out.scrollTop = out.scrollHeight;
}

window.GlyphboxScanner = { start() { if (last) runCode(last.code, last.box); }, stop() {}, showScanButton() {} };
window.Module = {
  canvas,
  locateFile: (f, dir) => dir + f + '?' + (document.querySelector('script[src*="glyphbox.js"]')?.src.split('?')[1] || ''),
  print: () => {},
  printErr: t => { if (/error|attempt|expected/i.test(t)) log(t, true); },
  onConsoleReady() {
    ready = true;
    setTimeout(() => document.title = PAGE_TITLE, 0);
    if (pending) { const p = pending; pending = null; p(); }
  },
};

function runCode(code, box) {
  if (!ready) { pending = () => runCode(code, box); out.textContent = 'Starting the console…'; return; }
  const M = window.Module, src = new TextEncoder().encode(code);
  const sp = M._malloc(src.length + 1), ap = M._malloc(ASSETS);
  M.HEAPU8.set(src, sp); M.HEAPU8[sp + src.length] = 0; M.HEAPU8.set(assets, ap);
  out.textContent = ''; lastLine = '';
  const ok = M.ccall('web_load_source', 'number', ['number','number','number','number','string','number'],
                     [sp, src.length, ap, ASSETS, 'EXAMPLE', 1]);
  M._free(sp); M._free(ap);
  if (ok) log('Running. Click the screen to use the buttons.');
  document.querySelectorAll('.try.cur').forEach(t => t.classList.remove('cur'));
  if (box) box.classList.add('cur');
  last = { code, box };
}

document.querySelectorAll('.try').forEach(box => {
  const ta = box.querySelector('textarea'), original = ta.value;
  const cm = window.CodeMirror ? CodeMirror.fromTextArea(ta, {
    mode: 'lua', lineNumbers: true, indentUnit: 2, tabSize: 2, viewportMargin: Infinity,
    extraKeys: { 'Ctrl-Enter': () => run(), 'Cmd-Enter': () => run(), Tab: c => c.replaceSelection('  ') },
  }) : null;
  const value = () => cm ? cm.getValue() : ta.value;
  const run = () => runCode(value(), box);
  box.querySelector('.try-run').onclick = run;
  box.querySelector('.try-reset').onclick = () => { cm ? cm.setValue(original) : (ta.value = original); run(); };
});

/* run the first example once the console is up, so the page starts alive */
const first = document.querySelector('.try .try-run');
if (first) pending = () => first.click();
})();
