/* Play page: the console, its game library, and camera scanning of printed cards. */
(() => {
'use strict';

const LIB = '../playground/examples/';
const ASSET_BYTES = 2304;
let library = [], ready = false, pending = null;

const statusEl = () => document.getElementById('gb-scanner-status');

window.Module = {
  canvas: document.getElementById('canvas'),
  locateFile: (f, dir) => dir + f + '?' + (document.querySelector('script[src*="glyphbox.js"]').src.split('?')[1] || ''),
  print: () => {}, printErr: t => { if (/error/i.test(t)) console.warn(t); },
  onRuntimeInitialized() {
    ready = true;
    setTimeout(() => document.title = 'Play GLYPHBOX', 0);
    if (pending) { const p = pending; pending = null; p(); }
  },
};
const whenReady = fn => ready ? fn() : (pending = fn);

/* Run a game from source with a 2,304-byte asset block, through the
   console's CART LOADED screen (quick = 0). */
function runSource(src, assets, title) {
  const M = window.Module, s = new TextEncoder().encode(src);
  const sp = M._malloc(s.length + 1), ap = M._malloc(ASSET_BYTES);
  M.HEAPU8.set(s, sp); M.HEAPU8[sp + s.length] = 0; M.HEAPU8.set(assets, ap);
  const ok = M.ccall('web_load_source', 'number', ['number','number','number','number','string','number'],
                     [sp, s.length, ap, ASSET_BYTES, title, 0]);
  M._free(sp); M._free(ap);
  document.getElementById('canvas').focus();
  return ok;
}

async function play(game) {
  const [src, bin] = await Promise.all([
    fetch(LIB + game.id + '.lua').then(r => r.text()),
    fetch(LIB + game.id + '.bin').then(r => r.arrayBuffer()),
  ]);
  whenReady(() => {
    if (window.GlyphboxScanner) GlyphboxScanner.stop();
    runSource(src, new Uint8Array(bin), game.title);
  });
}

/* A scanned .gbcart holds LuaJIT bytecode, which the browser's Lua can't
   run. If its title is a library game, run the published source with the
   cart's own sprites, map and sound instead. */
window.GlyphboxPlay = {
  onCart(cart) {
    const title = new TextDecoder().decode(cart.slice(4, 20)).replace(/\0.*$/s, '').trim();
    const game = library.find(g => g.title === title);
    const compressed = (cart[0x1e] | cart[0x1f] << 8) & 0x0002;
    const codeEnd = compressed ? 0x24 + (cart[0x20] | cart[0x21] << 8) : 0x1020;
    const assets = cart.slice(codeEnd, codeEnd + ASSET_BYTES);
    if (game && assets.length === ASSET_BYTES) {
      fetch(LIB + game.id + '.lua').then(r => r.text()).then(src => runSource(src, assets, game.title));
      return true;
    }
    const M = window.Module;
    M.ccall('web_load_cart', null, ['number','number'], [0, 0]);     // back to the splash
    const msg = `${title || 'This cart'} can only run on a GLYPHBOX console for now. The browser can play the library games.`;
    setTimeout(() => { const el = statusEl(); if (el) el.textContent = msg; document.getElementById('gb-scanner-overlay').style.display = 'block'; }, 0);
    return true;
  },
};

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
