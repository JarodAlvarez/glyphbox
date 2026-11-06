/* Play page: the console, its game library, and camera scanning of printed cards. */
(() => {
'use strict';

const LIB = '../playground/examples/';   // library list
const CARTS = 'carts/';                   // the real compiled carts
let library = [], ready = false, pending = null;


window.Module = {
  canvas: document.getElementById('canvas'),
  locateFile: (f, dir) => dir + f + '?' + (document.querySelector('script[src*="glyphbox.js"]').src.split('?')[1] || ''),
  print: () => {}, printErr: t => { if (/error/i.test(t)) console.warn(t); },
  onConsoleReady() {
    ready = true;
    setTimeout(() => document.title = 'Play GLYPHBOX', 0);
    if (pending) { const p = pending; pending = null; p(); }
  },
};
const whenReady = fn => ready ? fn() : (pending = fn);

/* Load a real cart (.gbcart, LuaJIT bytecode) exactly as a scanned card
   would be: the console recompiles it for the browser and shows CART LOADED. */
function loadCart(bytes) {
  const M = window.Module, ptr = M._malloc(bytes.length);
  M.HEAPU8.set(bytes, ptr);
  M.ccall('web_load_cart', null, ['number', 'number'], [ptr, bytes.length]);
  M._free(ptr);
  document.getElementById('canvas').focus();
}

async function play(game) {
  const bytes = new Uint8Array(await fetch(CARTS + game.id + '.gbcart').then(r => r.arrayBuffer()));
  whenReady(() => {
    if (window.GlyphboxScanner) GlyphboxScanner.stop();
    loadCart(bytes);
  });
}

document.getElementById('scan').onclick = () => whenReady(() => {
  window.Module.ccall('web_begin_scan', null, [], []);
  document.getElementById('canvas').focus();
});

function pips(n) { return Array.from({ length: 8 }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join(''); }
fetch(LIB + 'index.json').then(r => r.json()).then(list => {
  library = list;
  const ul = document.getElementById('library');
  list.forEach(g => {
    const li = document.createElement('li'), b = document.createElement('button');
    b.innerHTML = `<span>${g.title}</span><span class="pips">${pips(g.cards || 0)}</span>`;
    b.onclick = () => {
      ul.querySelectorAll('li').forEach(x => x.classList.remove('cur')); li.classList.add('cur');
      play(g);
    };
    li.appendChild(b); ul.appendChild(li);
  });
});

document.querySelectorAll('[data-logo]').forEach(el =>
  fetch(`../logo/${el.dataset.logo}.svg`).then(r => r.text()).then(t => el.innerHTML = t));
glyphText();
})();
