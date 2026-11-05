// GLYPHBOX system UI, ported 1:1 from src/renderer.c and src/main.c.
// A Screen is a 128x128 1-bit framebuffer drawn to a <canvas> at integer scale.
// Needs font.js (GB_FONT) loaded first.

class Screen {
  constructor(canvas, opts = {}) {
    this.cv = canvas;
    this.W = opts.w || 128; this.H = opts.h || 128;
    this.fb = new Uint8Array(this.W * this.H);
    canvas.width = this.W; canvas.height = this.H;
    this.ctx = canvas.getContext('2d');
    this.img = this.ctx.createImageData(this.W, this.H);
    this.ink = opts.ink || [240, 240, 236];
    this.paper = opts.paper || [8, 8, 8];
  }
  cls(c = 0) { this.fb.fill(c); }
  pset(x, y, c) { if (x >= 0 && y >= 0 && x < this.W && y < this.H) this.fb[y * this.W + x] = c; }
  rectf(x, y, w, h, c) { for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) this.pset(i, j, c); }
  rect(x, y, w, h, c) {
    this.rectf(x, y, w, 1, c); this.rectf(x, y + h - 1, w, 1, c);
    this.rectf(x, y, 1, h, c); this.rectf(x + w - 1, y, 1, h, c);
  }
  print(s, x, y, c, scale = 1) {
    let cx = x;
    for (const ch of s) {
      const code = ch.charCodeAt(0);
      if (code >= 32 && code <= 126) {
        const g = GB_FONT[code - 32];
        for (let r = 0; r < 7; r++) for (let col = 0; col < 5; col++)
          if (g[r] & (16 >> col)) this.rectf(cx + col * scale, y + r * scale, scale, scale, c);
      }
      cx += 6 * scale;
    }
  }
  invert() { for (let i = 0; i < this.fb.length; i++) this.fb[i] ^= 1; }
  // renderer_button_hint: two 7x7 discs, menu left, action right; the one to press is filled
  hint(which, x, y, c) {
    const inset = [2, 1, 0, 0, 0, 1, 2];
    for (let b = 0; b < 2; b++) {
      const bx = x + b * 8;
      const filled = b === 0 ? which === 'menu' : which === 'action';
      for (let r = 0; r < 7; r++) {
        const i = inset[r], w = 7 - 2 * i;
        if (filled || r === 0 || r === 6) this.rectf(bx + i, y + r, w, 1, c);
        else { this.pset(bx + i, y + r, c); this.pset(bx + i + w - 1, y + r, c); }
      }
    }
  }
  flush() {
    const d = this.img.data;
    for (let i = 0; i < this.fb.length; i++) {
      const p = this.fb[i] ? this.ink : this.paper;
      d[i * 4] = p[0]; d[i * 4 + 1] = p[1]; d[i * 4 + 2] = p[2]; d[i * 4 + 3] = 255;
    }
    this.ctx.putImageData(this.img, 0, 0);
  }

  // ── Shared chrome (main.c) ──
  centred(s, y, c) { this.print(s, Math.floor((128 - (s.length * 6 - 1)) / 2), y, c); }
  header(title) {
    this.rectf(0, 0, 128, 13, 1);
    this.print(title, 6, 3, 0);
    this.mark(113, 1, 1, 4, 0);
  }
  hintW(label) { return 15 + 4 + label.length * 6 - 1; }
  hintLabel(which, label, x, y) { this.hint(which, x, y, 1); this.print(label, x + 19, y, 1); }
  footer(lw, ll, rw, rl) {
    this.rectf(0, 112, 128, 1, 1);
    this.hintLabel(lw, ll, 4, 117);
    if (rl) this.hintLabel(rw, rl, 124 - this.hintW(rl), 117);
  }
  // draw_logo_mark(): official 9x11 grid, u px per unit; parts = boot reveal stage
  mark(x0, y0, u, parts = 4, c = 1) {
    if (parts >= 1) { this.rectf(x0, y0, 9 * u, 9 * u, c); this.rectf(x0 + u, y0 + u, 7 * u, 7 * u, 1 - c); }
    if (parts >= 2) { this.rectf(x0 + 2 * u, y0 + 2 * u, 5 * u, 5 * u, c); this.rectf(x0 + 3 * u, y0 + 3 * u, 3 * u, 3 * u, 1 - c); }
    if (parts >= 3) this.rectf(x0 + 4 * u, y0 + 4 * u, u, u, c);
    if (parts >= 4) for (let i = 0; i < 5; i++) this.rectf(x0 + 2 * i * u, y0 + 10 * u, u, u, c);
  }
  // draw_logo(): 45x55 mark at x=41, pixel wordmark 8px below the dots (LOGO_WORD_DY = 63)
  logo(ly, parts = 5) {
    this.mark(41, ly, 5, Math.min(parts, 4));
    if (parts >= 5) this.print('GLYPHBOX', 40, ly + 63, 1);
  }

  // ── Screens ──
  startup(f) {                     // LOGO_BOOT_Y = 29
    this.cls(0);
    const parts = f >= 26 ? 5 : f >= 21 ? 4 : f >= 16 ? 3 : f >= 11 ? 2 : f >= 6 ? 1 : 0;
    if (parts) this.logo(29, parts);
    if (f === 26 || f === 27) this.invert();
  }
  splash(intro, frame) {           // intro: 0..12 frames into the slide-up
    this.cls(0);
    const left = 12 - Math.min(intro, 12), den = 144;
    const ly = 11 + Math.floor(18 * left * left / den), fy = Math.floor(36 * left * left / den);
    const rest = left === 0;
    this.logo(ly);
    this.print('(C) Gureedo 2026', 16, 94 + fy, 1);
    const on = !rest || (frame % 30) < 15;
    this.rectf(0, 112 + fy, 128, 1, 1);
    if (on) this.hintLabel('action', 'SCAN CARD', 4, 117 + fy);
    this.hintLabel('menu', 'MENU', 124 - this.hintW('MENU'), 117 + fy);
  }
  menu(rows, cursor, vol = 7) {
    this.cls(0); this.header('MENU');
    let y = 22;
    rows.forEach((label, i) => {
      const sel = cursor === i, isVol = label === 'VOLUME', h = isVol ? 26 : 13, ink = sel ? 0 : 1;
      if (sel) this.rectf(4, y - 3, 120, h, 1);
      this.print(label, 10, y, ink);
      if (isVol) {
        for (let s = 0; s < 10; s++)
          s < vol ? this.rectf(10 + s * 11, y + 11, 9, 7, ink) : this.rect(10 + s * 11, y + 11, 9, 7, ink);
        y += 32;
      } else y += 16;
    });
    this.footer('action', 'OK', 'menu', 'BACK');
  }
  cartLoaded(title, author, t) {
    this.cls(0); this.header('CART LOADED');
    if (title.length <= 10) this.print(title, Math.floor((128 - (title.length * 12 - 2)) / 2), 44, 1, 2);
    else this.centred(title, 48, 1);
    if (author) this.centred('BY ' + author, 66, 1);
    for (let i = 0; i < 5; i++)
      t > 6 + i * 9 ? this.rectf(46 + i * 8, 90, 4, 4, 1) : this.rectf(47 + i * 8, 91, 2, 2, 1);
  }
  scanCard(cy) {
    const cx = 37, W = 54, H = 68;
    this.rectf(cx, cy, W, H, 1); this.rectf(cx + 2, cy, 6, H, 0);
    const bx = cx + 12, by = cy + 6;
    for (let y = 0; y < 18; y++) for (let x = 0; x < 18; x++)
      if ((x * 7 + y * 13 + x * y) % 5 < 2) this.rectf(bx + x * 2, by + y * 2, 2, 2, 0);
    this.rectf(bx + 11, by + 11, 14, 14, 1); this.rectf(bx + 12, by + 12, 12, 12, 0);
    this.rectf(bx + 14, by + 14, 8, 8, 1); this.rectf(bx + 16, by + 16, 4, 4, 0);
    for (let k = 0; k < 4; k++) this.rectf(cx + 24 + k, cy + 54 + k, 8 - 2 * k, 1, 0);
  }
  // st: {cardY, msg, total, mask, cur, flash}
  scan(st) {
    this.cls(0);
    for (let k = 0; k < 54; k += 4) this.rectf(37 + k, 30, 2, 1, 1);
    for (let k = 0; k < 68; k += 4) { this.rectf(37, 30 + k, 1, 2, 1); this.rectf(90, 30 + k, 1, 2, 1); }
    this.scanCard(st.cardY);
    this.rectf(0, 0, 128, 14, 0);
    this.rectf(30, 14, 3, 86, 1); this.rectf(95, 14, 3, 86, 1); this.rectf(26, 100, 76, 3, 1);
    if (st.msg.startsWith('R')) this.print(st.msg, 38, 3, 1);
    else this.print(st.msg, Math.floor((128 - st.msg.length * 6) / 2) + 1, 3, 1);
    const n = st.total, x0 = Math.floor((128 - (n * 8 - 4)) / 2);
    for (let i = 0; i < n; i++) {
      const x = x0 + i * 8;
      if (st.mask & (1 << i)) this.rectf(x, 119, 4, 4, 1);
      else if (i === st.cur) { this.rectf(x, 119, 4, 4, 1); this.rectf(x + 1, 120, 2, 2, 0); }
      else this.rectf(x + 1, 120, 2, 2, 1);
    }
    if (st.flash) this.invert();
  }
}

// A looping reel through the real system screens: boot → splash → scan → cart loaded → menu.
function glyphReel(canvas, opts = {}) {
  const s = new Screen(canvas, opts);
  const game = opts.game || ['SUNSET RUN', 'GUREEDO'];
  const total = 4;
  let f = 0;
  const seq = [
    [50, t => s.startup(t)],
    [80, t => s.splash(t, t)],
    [150, t => {
      const per = 36, card = Math.min(Math.floor(t / per), total - 1), k = t % per;
      const mask = (1 << Math.floor(t / per)) - 1;
      const y = k < 14 ? -56 + Math.round(86 * (1 - Math.pow(1 - k / 14, 3))) : (k < 28 ? 30 : 30 - (k - 28) * 11);
      const msg = k < 14 ? 'INSERT CARD' : k < 24 ? 'READING' + '...'.slice(0, Math.floor(k / 3) % 4) : `CARD ${card + 1}/${total} OK`;
      s.scan({ cardY: y, msg, total, mask: k >= 24 ? mask | (1 << card) : mask, cur: card, flash: k === 24 || k === 25 });
    }],
    [60, t => s.cartLoaded(game[0], game[1], t)],
    [70, t => s.menu(['VOLUME', 'EXIT GAME', 'SHUTDOWN'], t < 35 ? 0 : 1, 7)],
  ];
  const len = seq.reduce((a, b) => a + b[0], 0);
  function tick() {
    let t = f % len;
    for (const [d, fn] of seq) { if (t < d) { fn(t); break; } t -= d; }
    s.flush(); f++;
  }
  tick();
  setInterval(tick, 1000 / 30);
  return s;
}

// Draw a single static screen. kind: 'splash' | 'menu' | 'cart' | 'scan' | 'startup'
function glyphStill(canvas, kind, arg = {}, opts = {}) {
  const s = new Screen(canvas, opts);
  if (kind === 'splash') s.splash(12, 0);
  else if (kind === 'menu') s.menu(arg.rows || ['VOLUME', 'EXIT GAME', 'SHUTDOWN'], arg.cursor || 0, arg.vol ?? 7);
  else if (kind === 'cart') s.cartLoaded(arg.title, arg.author, 99);
  else if (kind === 'scan') s.scan({ cardY: 30, msg: 'READING..', total: 4, mask: 3, cur: 2 });
  else if (kind === 'startup') s.startup(40);
  s.flush();
  return s;
}

// Console-font text as an element: <canvas data-px="TEXT" data-scale="3">, ink = CSS color.
function glyphText(root = document) {
  root.querySelectorAll('[data-px]').forEach(el => {
    const txt = el.dataset.px, sc = +(el.dataset.scale || 2);
    const w = txt.length * 6 - 1, h = 7;
    el.width = w * sc; el.height = h * sc;
    el.style.width = w * sc + 'px'; el.style.height = h * sc + 'px';
    const ctx = el.getContext('2d');
    ctx.fillStyle = getComputedStyle(el).color;
    let cx = 0;
    for (const ch of txt) {
      const g = GB_FONT[ch.charCodeAt(0) - 32] || GB_FONT[0];
      for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++)
        if (g[r] & (16 >> c)) ctx.fillRect((cx + c) * sc, r * sc, sc, sc);
      cx += 6;
    }
  });
}

// The UI's small marks, as inline SVG strings (same pixel geometry).
const GB_MARK = `<svg viewBox="0 0 9 9" shape-rendering="crispEdges" class="gb-mark"><path fill="none" stroke="currentColor" d="M.5 .5h8v8h-8zM2.5 2.5h4v4h-4z"/><rect x="4" y="4" width="1" height="1" fill="currentColor"/></svg>`;
function GB_HINT(which) {
  const disc = (ox, filled) => filled
    ? `<path fill="currentColor" d="M${ox+2} 0h3v1h1v1h1v3h-1v1h-1v1h-3v-1h-1v-1h-1v-3h1v-1h1z"/>`
    : `<path fill="currentColor" fill-rule="evenodd" d="M${ox+2} 0h3v1h1v1h1v3h-1v1h-1v1h-3v-1h-1v-1h-1v-3h1v-1h1zM${ox+2} 1v1h-1v3h1v1h3v-1h1v-3h-1v-1z"/>`;
  return `<svg viewBox="0 0 15 7" shape-rendering="crispEdges" class="gb-hint">${disc(0, which === 'menu')}${disc(8, which === 'action')}</svg>`;
}

// Original carts and their real card counts (card-print.py, Nov 2026).
const GB_GAMES = [['SUNSET RUN', 8], ['GLYPH GOLF', 8], ['GLYPH FIGHTERS', 8], ['BUKO BUKO', 8],
                  ['PUZZLE LEAGUE', 4], ['DUNGEON', 2], ['TENNIS', 4], ['CHESS', 8]];

// The actual logo, from draw_splash(): 40×40 mark (two 4px rings + 8px centre)
// over the 5-dot row (4px dots, 7px step, 6px below the mark). Optional wordmark.
function GB_LOGO(opts = {}) {
  const word = opts.wordmark;
  let d = 'M0 0h40v40h-40zM4 4v32h32v-32zM8 8h24v24h-24zM12 12v16h16v-16zM16 16h8v8h-8z';
  for (let i = 0; i < 5; i++) d += `M${4 + i * 7} 46h4v4h-4z`;
  let w = '';
  if (word) {
    let cx = -4;
    for (const ch of 'GLYPHBOX') {
      const g = GB_FONT[ch.charCodeAt(0) - 32];
      for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++)
        if (g[r] & (16 >> c)) w += `M${cx + c} ${54 + r}h1v1h-1z`;
      cx += 6;
    }
  }
  const vb = word ? '-4 0 48 61' : '0 0 40 50';
  return `<svg viewBox="${vb}" shape-rendering="crispEdges" class="gb-logo${word ? ' word' : ' gb-mark'}"><path fill="currentColor" fill-rule="evenodd" d="${d}${w}"/></svg>`;
}
