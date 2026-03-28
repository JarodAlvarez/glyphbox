#ifndef GLYPHBOX_CART_H
#define GLYPHBOX_CART_H

#include <stddef.h>
#include <stdint.h>

struct lua_State;

/* Cartridge flags (bit field in header at 0x001E) */
#define FLAG_COMPRESSED_BYTECODE 0x0002   /* v0.4: bytecode is zlib-compressed */

typedef struct {
    char     title[17];
    char     author[9];
    uint16_t version;
    uint16_t flags;
    uint8_t *bytecode;
    size_t   bytecode_len;
    size_t   bytecode_compressed_len;  /* 0 when uncompressed */
    uint8_t  sprites[1024];
    uint8_t  tilemap[512];
    uint8_t  sfx_data[512];
    uint8_t  music_data[256];
    uint32_t crc32;
} Cart;

Cart *cart_load_file(const char *path);
void  cart_free(Cart *cart);
void  cart_save(Cart *cart, int slot, const uint8_t *data, size_t len);
void  cart_load_save_lua(struct lua_State *L, Cart *cart, int slot);

#endif /* GLYPHBOX_CART_H */
