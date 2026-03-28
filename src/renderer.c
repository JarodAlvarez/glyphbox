/* renderer.c — 1-bit 128x128 framebuffer and SDL2 blit pipeline */
#include "renderer.h"
#include "font.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define FB_W 128
#define FB_H 128
#define FB_BYTES (FB_W * FB_H / 8)  /* 2048 */

static uint8_t fb[FB_BYTES];
static SDL_Renderer *sdl_renderer;
static SDL_Texture  *fb_texture;

/* Sprite sheet: 128 tiles x 8x8 pixels x 1bpp = 1024 bytes.
   Tile N, row R, col C: sprites[(N*8 + R)*8 + C]  (0 or 1, pre-expanded) */
static uint8_t sprites[128 * 8 * 8];

/* Tilemap: 16x16 tile indices stored as uint16 LE pairs = 512 bytes raw.
   Pre-parsed into a flat uint16 array for fast lookup. */
static uint16_t tilemap[16 * 16];

void renderer_init(SDL_Renderer *r) {
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");  /* must precede texture creation */
    sdl_renderer = r;
    SDL_RenderSetLogicalSize(r, FB_W, FB_H);          /* lock viewport to 128×128; SDL2 letterboxes */
    fb_texture = SDL_CreateTexture(r,
        SDL_PIXELFORMAT_RGBA8888,
        SDL_TEXTUREACCESS_STREAMING,
        FB_W, FB_H);
    memset(fb, 0, FB_BYTES);
    memset(sprites, 0, sizeof(sprites));
    memset(tilemap, 0, sizeof(tilemap));
}

void renderer_frame(void) {
    void *pixels;
    int pitch;
    SDL_LockTexture(fb_texture, NULL, &pixels, &pitch);
    uint32_t *p = (uint32_t *)pixels;
    for (int y = 0; y < FB_H; y++) {
        for (int x = 0; x < FB_W; x++) {
            int i = y * FB_W + x;
            int bit = (fb[i >> 3] >> (i & 7)) & 1;
            p[y * (pitch / 4) + x] = bit ? 0xFFFFFFFF : 0x000000FF;
        }
    }
    SDL_UnlockTexture(fb_texture);
    SDL_RenderCopy(sdl_renderer, fb_texture, NULL, NULL);
}

void renderer_cls(int c) {
    memset(fb, c ? 0xFF : 0x00, FB_BYTES);
}

void renderer_pset(int x, int y, int c) {
    if (x < 0 || x >= FB_W || y < 0 || y >= FB_H) return;
    int i = y * FB_W + x;
    if (c) fb[i >> 3] |=  (1 << (i & 7));
    else   fb[i >> 3] &= ~(1 << (i & 7));
}

int renderer_pget(int x, int y) {
    if (x < 0 || x >= FB_W || y < 0 || y >= FB_H) return 0;
    int i = y * FB_W + x;
    return (fb[i >> 3] >> (i & 7)) & 1;
}

void renderer_line(int x0, int y0, int x1, int y1, int c) {
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    while (1) {
        renderer_pset(x0, y0, c);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

void renderer_rect(int x, int y, int w, int h, int c) {
    renderer_line(x,       y,       x+w-1, y,       c);
    renderer_line(x+w-1,  y,       x+w-1, y+h-1,   c);
    renderer_line(x+w-1,  y+h-1,   x,     y+h-1,   c);
    renderer_line(x,      y+h-1,   x,     y,        c);
}

void renderer_rectf(int x, int y, int w, int h, int c) {
    for (int row = y; row < y + h; row++)
        for (int col = x; col < x + w; col++)
            renderer_pset(col, row, c);
}

void renderer_circ(int x, int y, int r, int c) {
    int px = 0, py = r, d = 1 - r;
    while (px <= py) {
        renderer_pset(x+px, y+py, c); renderer_pset(x-px, y+py, c);
        renderer_pset(x+px, y-py, c); renderer_pset(x-px, y-py, c);
        renderer_pset(x+py, y+px, c); renderer_pset(x-py, y+px, c);
        renderer_pset(x+py, y-px, c); renderer_pset(x-py, y-px, c);
        if (d < 0) d += 2 * px + 3;
        else { d += 2 * (px - py) + 5; py--; }
        px++;
    }
}

void renderer_circf(int x, int y, int r, int c) {
    for (int row = -r; row <= r; row++) {
        int half = (int)(r * r - row * row);
        int span = 0;
        /* integer sqrt via loop — avoid floating point */
        while ((span + 1) * (span + 1) <= half) span++;
        for (int col = -span; col <= span; col++)
            renderer_pset(x + col, y + row, c);
    }
}

void renderer_spr(int id, int x, int y, int fx, int fy) {
    if (id < 0 || id >= 128) return;
    for (int row = 0; row < 8; row++) {
        int sr = fy ? (7 - row) : row;
        for (int col = 0; col < 8; col++) {
            int sc = fx ? (7 - col) : col;
            int px = sprites[(id * 8 + sr) * 8 + sc];
            if (px) renderer_pset(x + col, y + row, 1);
        }
    }
}

void renderer_map(int cx, int cy, int x, int y, int w, int h) {
    for (int ty = 0; ty < h; ty++) {
        for (int tx = 0; tx < w; tx++) {
            int mx = cx + tx, my = cy + ty;
            if (mx < 0 || mx >= 16 || my < 0 || my >= 16) continue;
            int tile = tilemap[my * 16 + mx];
            renderer_spr(tile, x + tx * 8, y + ty * 8, 0, 0);
        }
    }
}

void renderer_print(const char *str, int x, int y, int c) {
    int cx = x;
    for (int i = 0; str[i]; i++) {
        unsigned char ch = (unsigned char)str[i];
        if (ch < 32 || ch > 126) { cx += 6; continue; }
        int gi = ch - 32;
        for (int row = 0; row < 7; row++)
            for (int col = 0; col < 5; col++)
                if (font_data[gi][row][col])
                    renderer_pset(cx + col, y + row, c);
        cx += 6;
    }
}

void renderer_invert(void) {
    for (int i = 0; i < FB_BYTES; i++) fb[i] ^= 0xFF;
}

void renderer_set_sprites(const uint8_t *data) {
    /* data is the raw 1024-byte sprite sheet: 128 tiles, each 8 rows of 1 byte.
       Each byte encodes 8 pixels MSB first. Expand to sprites[]. */
    for (int tile = 0; tile < 128; tile++) {
        for (int row = 0; row < 8; row++) {
            uint8_t byte = data[tile * 8 + row];
            for (int col = 0; col < 8; col++) {
                sprites[(tile * 8 + row) * 8 + col] = (byte >> (7 - col)) & 1;
            }
        }
    }
}

void renderer_set_tilemap(const uint8_t *data) {
    /* data is 512 bytes: 16x16 uint16 LE indices */
    for (int i = 0; i < 256; i++) {
        tilemap[i] = (uint16_t)(data[i * 2] | (data[i * 2 + 1] << 8));
    }
}

void renderer_debug_ascii(void) {
    for (int y = 0; y < FB_H; y++) {
        for (int x = 0; x < FB_W; x++)
            putchar(renderer_pget(x, y) ? '#' : '.');
        putchar('\n');
    }
}
