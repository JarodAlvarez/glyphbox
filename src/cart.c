/* cart.c — .gbcart binary parser, CRC32 validation, and save slot management */
#include "cart.h"

#include <lua.h>
#include <lauxlib.h>
#include <zlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>

/* ── Binary format offsets ────────────────────────────────────────────────── */
#define MAGIC_OFFSET      0x0000
#define TITLE_OFFSET      0x0004
#define AUTHOR_OFFSET     0x0014
#define VERSION_OFFSET    0x001C
#define FLAGS_OFFSET      0x001E
#define BYTECODE_OFFSET   0x0020
#define SPRITES_OFFSET    0x1020
#define TILEMAP_OFFSET    0x1420
#define SFX_OFFSET        0x1620
#define MUSIC_OFFSET      0x1820
#define TOTAL_BODY        0x1920   /* bytes before CRC32 */

static const uint8_t MAGIC[4] = { 0x47, 0x42, 0x43, 0x31 };  /* GBC1 */

/* ── Save directory ───────────────────────────────────────────────────────── */

static void get_save_path(Cart *cart, int slot, char *out, size_t n) {
    const char *home = getenv("HOME");
    if (!home) home = ".";
    char dir[512];
    char base[512];
    snprintf(base, sizeof(base), "%s/.glyphbox", home);
    mkdir(base, 0700);
    snprintf(dir, sizeof(dir), "%s/.glyphbox/saves", home);
    mkdir(dir, 0700);
    snprintf(out, n, "%s/%08X_%d.bin", dir, cart->crc32, slot);
}

/* ── Public API ───────────────────────────────────────────────────────────── */

Cart *cart_load_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "GLYPHBOX: cannot open cartridge: %s\n", path);
        return NULL;
    }

    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    rewind(f);

    /* Minimum: must at least contain header through flags field + CRC32 */
    if (sz < (long)(FLAGS_OFFSET + 2 + 4)) {
        fprintf(stderr, "GLYPHBOX: cartridge too small: %ld bytes\n", sz);
        fclose(f);
        return NULL;
    }

    uint8_t *buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        fprintf(stderr, "GLYPHBOX: read error\n");
        free(buf); fclose(f); return NULL;
    }
    fclose(f);

    /* Check magic */
    if (memcmp(buf + MAGIC_OFFSET, MAGIC, 4) != 0) {
        fprintf(stderr, "GLYPHBOX: invalid magic bytes\n");
        free(buf); return NULL;
    }

    /* Verify CRC32 */
    uint32_t stored_crc = (uint32_t)buf[sz-4]
                        | ((uint32_t)buf[sz-3] << 8)
                        | ((uint32_t)buf[sz-2] << 16)
                        | ((uint32_t)buf[sz-1] << 24);
    uint32_t computed   = (uint32_t)crc32(0, buf, (uInt)(sz - 4));
    if (stored_crc != computed) {
        fprintf(stderr, "GLYPHBOX: CRC32 mismatch (stored 0x%08X, computed 0x%08X)\n",
                stored_crc, computed);
        free(buf); return NULL;
    }

    Cart *c = (Cart *)calloc(1, sizeof(Cart));
    if (!c) { free(buf); return NULL; }

    /* Header */
    memcpy(c->title,  buf + TITLE_OFFSET,   16); c->title[16]  = '\0';
    memcpy(c->author, buf + AUTHOR_OFFSET,  8);  c->author[8]  = '\0';
    c->version = (uint16_t)(buf[VERSION_OFFSET] | (buf[VERSION_OFFSET+1] << 8));
    c->flags   = (uint16_t)(buf[FLAGS_OFFSET]   | (buf[FLAGS_OFFSET+1]   << 8));
    c->crc32   = stored_crc;

    /* ── Bytecode loading: v0.4 compressed vs. v0.2 legacy ─────────────────── */
    size_t sprites_off, tilemap_off, sfx_off, music_off;

    if (c->flags & FLAG_COMPRESSED_BYTECODE) {
        /* v0.4: two uint16 LE fields at 0x0020/0x0022, compressed data at 0x0024 */
        if ((size_t)sz < 0x0026) {
            fprintf(stderr, "GLYPHBOX: cart too small for v0.4 size fields\n");
            free(buf); free(c); return NULL;
        }
        size_t stored_len = (size_t)buf[0x0020] | ((size_t)buf[0x0021] << 8);
        size_t uncomp_len = (size_t)buf[0x0022] | ((size_t)buf[0x0023] << 8);

        if (stored_len == 0 || uncomp_len == 0) {
            fprintf(stderr, "GLYPHBOX: v0.4 cart has zero bytecode length\n");
            free(buf); free(c); return NULL;
        }
        /* Verify the cart is large enough to hold all sections */
        size_t needed = 0x0024 + stored_len + 1024 + 512 + 512 + 256 + 4;
        if ((size_t)sz < needed) {
            fprintf(stderr, "GLYPHBOX: v0.4 cart truncated (need %zu, have %ld)\n",
                    needed, sz);
            free(buf); free(c); return NULL;
        }

        uint8_t *decomp = (uint8_t *)malloc(uncomp_len);
        if (!decomp) { free(buf); free(c); return NULL; }

        uLongf dest_len = (uLongf)uncomp_len;
        int zr = uncompress(decomp, &dest_len,
                            buf + 0x0024, (uLong)stored_len);
        if (zr != Z_OK) {
            fprintf(stderr, "GLYPHBOX: zlib decompression failed: %s\n", zError(zr));
            free(decomp); free(buf); free(c); return NULL;
        }

        c->bytecode              = decomp;
        c->bytecode_len          = (size_t)dest_len;
        c->bytecode_compressed_len = stored_len;

        /* Assets follow immediately after compressed bytecode */
        sprites_off = 0x0024 + stored_len;
        tilemap_off = sprites_off + 1024;
        sfx_off     = tilemap_off + 512;
        music_off   = sfx_off    + 512;

    } else {
        /* v0.2 legacy: uint32 LE length prefix at 0x0020, data at 0x0024,
           zero-padded to 4096 bytes, assets at fixed offsets.              */
        if ((size_t)sz < (size_t)(TOTAL_BODY + 4)) {
            fprintf(stderr, "GLYPHBOX: legacy cart too small: %ld bytes\n", sz);
            free(buf); free(c); return NULL;
        }
        size_t bc_max = SPRITES_OFFSET - BYTECODE_OFFSET;  /* 4096 */
        uint32_t bc_actual = (uint32_t)buf[BYTECODE_OFFSET]
                           | ((uint32_t)buf[BYTECODE_OFFSET+1] << 8)
                           | ((uint32_t)buf[BYTECODE_OFFSET+2] << 16)
                           | ((uint32_t)buf[BYTECODE_OFFSET+3] << 24);
        if (bc_actual == 0 || bc_actual + 4 > bc_max) {
            /* Fallback: no length prefix — pass full section minus prefix */
            bc_actual = (uint32_t)(bc_max - 4);
        }
        c->bytecode_len            = bc_actual;
        c->bytecode_compressed_len = 0;
        c->bytecode = (uint8_t *)malloc(bc_actual);
        if (!c->bytecode) { free(buf); free(c); return NULL; }
        memcpy(c->bytecode, buf + BYTECODE_OFFSET + 4, bc_actual);

        sprites_off = SPRITES_OFFSET;
        tilemap_off = TILEMAP_OFFSET;
        sfx_off     = SFX_OFFSET;
        music_off   = MUSIC_OFFSET;
    }

    /* ── Fixed-size asset sections ──────────────────────────────────────────── */
    if ((size_t)sz >= sprites_off + 1024)
        memcpy(c->sprites,    buf + sprites_off, 1024);
    if ((size_t)sz >= tilemap_off + 512)
        memcpy(c->tilemap,    buf + tilemap_off, 512);
    if ((size_t)sz >= sfx_off + 512)
        memcpy(c->sfx_data,   buf + sfx_off,     512);
    if ((size_t)sz >= music_off + 256)
        memcpy(c->music_data, buf + music_off,   256);

    free(buf);
    return c;
}

void cart_free(Cart *cart) {
    if (!cart) return;
    free(cart->bytecode);
    free(cart);
}

void cart_save(Cart *cart, int slot, const uint8_t *data, size_t len) {
    if (!cart || slot < 0 || slot > 3) return;
    if (len > 64) len = 64;
    char path[512];
    get_save_path(cart, slot, path, sizeof(path));
    FILE *f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "GLYPHBOX: save failed: %s\n", path);
        return;
    }
    fwrite(data, 1, len, f);
    fclose(f);
}

void cart_load_save_lua(lua_State *Lua, Cart *cart, int slot) {
    if (!cart || slot < 0 || slot > 3) { lua_pushnil(Lua); return; }
    char path[512];
    get_save_path(cart, slot, path, sizeof(path));
    FILE *f = fopen(path, "rb");
    if (!f) { lua_pushnil(Lua); return; }
    uint8_t buf[64];
    size_t n = fread(buf, 1, 64, f);
    fclose(f);
    lua_pushlstring(Lua, (const char *)buf, n);
}
