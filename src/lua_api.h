#ifndef GLYPHBOX_LUA_API_H
#define GLYPHBOX_LUA_API_H

#include <stddef.h>
#include <stdint.h>
#include "cart.h"

void lua_api_init(void);
void lua_api_shutdown(void);
void lua_api_unload(void);   /* reset VM between cart loads — shutdown + re-init */
int  lua_api_load(const uint8_t *bytecode, size_t len, const char *title);
void lua_api_call_init(void);
void lua_api_call_update(void);
void lua_api_call_draw(void);
void lua_api_set_cart(Cart *cart);

#endif /* GLYPHBOX_LUA_API_H */
