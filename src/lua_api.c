/* lua_api.c — LuaJIT VM setup, sandbox, and full GLYPHBOX API registration */
#include "lua_api.h"
#include "renderer.h"
#include "input.h"
#include "audio.h"
#include "cart.h"

#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <SDL2/SDL.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static lua_State *L          = NULL;
static Cart      *active_cart = NULL;
static uint32_t   frame_count = 0;

/* ── Graphics ─────────────────────────────────────────────────────────────── */

static int l_cls(lua_State *L2) {
    renderer_cls(lua_tointeger(L2, 1));
    return 0;
}
static int l_pset(lua_State *L2) {
    renderer_pset(luaL_checkinteger(L2, 1),
                  luaL_checkinteger(L2, 2),
                  luaL_checkinteger(L2, 3));
    return 0;
}
static int l_pget(lua_State *L2) {
    lua_pushinteger(L2, renderer_pget(luaL_checkinteger(L2, 1),
                                      luaL_checkinteger(L2, 2)));
    return 1;
}
static int l_line(lua_State *L2) {
    renderer_line(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                  luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4),
                  luaL_checkinteger(L2, 5));
    return 0;
}
static int l_rect(lua_State *L2) {
    renderer_rect(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                  luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4),
                  luaL_checkinteger(L2, 5));
    return 0;
}
static int l_rectf(lua_State *L2) {
    renderer_rectf(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                   luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4),
                   luaL_checkinteger(L2, 5));
    return 0;
}
static int l_circ(lua_State *L2) {
    renderer_circ(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                  luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4));
    return 0;
}
static int l_circf(lua_State *L2) {
    renderer_circf(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                   luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4));
    return 0;
}
static int l_spr(lua_State *L2) {
    int id = luaL_checkinteger(L2, 1);
    int x  = luaL_checkinteger(L2, 2);
    int y  = luaL_checkinteger(L2, 3);
    int fx = (int)lua_toboolean(L2, 4);
    int fy = (int)lua_toboolean(L2, 5);
    renderer_spr(id, x, y, fx, fy);
    return 0;
}
static int l_map(lua_State *L2) {
    renderer_map(luaL_checkinteger(L2, 1), luaL_checkinteger(L2, 2),
                 luaL_checkinteger(L2, 3), luaL_checkinteger(L2, 4),
                 luaL_checkinteger(L2, 5), luaL_checkinteger(L2, 6));
    return 0;
}
static int l_print(lua_State *L2) {
    renderer_print(luaL_checkstring(L2, 1),
                   luaL_checkinteger(L2, 2),
                   luaL_checkinteger(L2, 3),
                   luaL_checkinteger(L2, 4));
    return 0;
}
static int l_invert(lua_State *L2) {
    (void)L2;
    renderer_invert();
    return 0;
}

/* ── Input ────────────────────────────────────────────────────────────────── */

static int l_btn(lua_State *L2) {
    lua_pushboolean(L2, input_btn(luaL_checkinteger(L2, 1)));
    return 1;
}
static int l_btnp(lua_State *L2) {
    lua_pushboolean(L2, input_btnp(luaL_checkinteger(L2, 1)));
    return 1;
}
static int l_btnr(lua_State *L2) {
    lua_pushboolean(L2, input_btnr(luaL_checkinteger(L2, 1)));
    return 1;
}

/* ── Audio ────────────────────────────────────────────────────────────────── */

static int l_sfx(lua_State *L2) {
    int ch   = luaL_checkinteger(L2, 1);
    int note = luaL_checkinteger(L2, 2);
    int vol  = (int)luaL_optinteger(L2, 3, 7);
    int wave = (int)luaL_optinteger(L2, 4, 0);
    int dur  = (int)luaL_optinteger(L2, 5, -1);
    audio_sfx(ch, note, vol, wave, dur);
    return 0;
}
static int l_sfx_pat(lua_State *L2) {
    audio_sfx_pat(luaL_checkinteger(L2, 1));
    return 0;
}
static int l_music(lua_State *L2) {
    int id = lua_isnoneornil(L2, 1) ? -1 : (int)luaL_checkinteger(L2, 1);
    audio_music(id);
    return 0;
}

/* ── Math & Utility ───────────────────────────────────────────────────────── */

static int l_rnd(lua_State *L2) {
    int n = luaL_checkinteger(L2, 1);
    lua_pushinteger(L2, (n > 0) ? (rand() % n) : 0);
    return 1;
}
static int l_mid(lua_State *L2) {
    lua_Number a = luaL_checknumber(L2, 1);
    lua_Number b = luaL_checknumber(L2, 2);
    lua_Number c = luaL_checknumber(L2, 3);
    lua_Number m;
    if (a <= b && a <= c) m = (b <= c) ? b : c;
    else if (b <= a && b <= c) m = (a <= c) ? a : c;
    else m = (a <= b) ? a : b;
    lua_pushnumber(L2, m);
    return 1;
}
static int l_clamp(lua_State *L2) {
    lua_Number v  = luaL_checknumber(L2, 1);
    lua_Number lo = luaL_checknumber(L2, 2);
    lua_Number hi = luaL_checknumber(L2, 3);
    lua_pushnumber(L2, v < lo ? lo : v > hi ? hi : v);
    return 1;
}
static int l_flr(lua_State *L2) {
    lua_pushinteger(L2, (lua_Integer)floor(luaL_checknumber(L2, 1)));
    return 1;
}
static int l_abs(lua_State *L2) {
    lua_pushnumber(L2, fabs(luaL_checknumber(L2, 1)));
    return 1;
}
static int l_sin(lua_State *L2) {
    lua_pushnumber(L2, sin(luaL_checknumber(L2, 1) * 2.0 * M_PI));
    return 1;
}
static int l_cos(lua_State *L2) {
    lua_pushnumber(L2, cos(luaL_checknumber(L2, 1) * 2.0 * M_PI));
    return 1;
}
static int l_time(lua_State *L2) {
    lua_pushnumber(L2, SDL_GetTicks() / 1000.0);
    return 1;
}
static int l_frame(lua_State *L2) {
    lua_pushinteger(L2, (lua_Integer)frame_count);
    return 1;
}

/* ── Cartridge memory ─────────────────────────────────────────────────────── */

static int l_peek(lua_State *L2) {
    int addr = luaL_checkinteger(L2, 1);
    if (active_cart && addr >= 0 && (size_t)addr < active_cart->bytecode_len)
        lua_pushinteger(L2, active_cart->bytecode[addr]);
    else
        lua_pushnil(L2);
    return 1;
}
static int l_save(lua_State *L2) {
    if (!active_cart) return 0;
    int slot = luaL_checkinteger(L2, 1);
    size_t len;
    const char *data = luaL_checklstring(L2, 2, &len);
    cart_save(active_cart, slot, (const uint8_t *)data, len);
    return 0;
}
static int l_load(lua_State *L2) {
    if (!active_cart) { lua_pushnil(L2); return 1; }
    int slot = luaL_checkinteger(L2, 1);
    cart_load_save_lua(L2, active_cart, slot);
    return 1;
}

/* ── Registration & lifecycle ─────────────────────────────────────────────── */

#define REG(name, fn) lua_pushcfunction(L, fn); lua_setglobal(L, name)

void lua_api_init(void) {
    L = luaL_newstate();

    luaopen_base(L);
    luaopen_math(L);
    luaopen_table(L);
    luaopen_string(L);

    /* Remove dangerous globals */
    const char *remove[] = {
        "io", "os", "package", "require", "dofile",
        "load", "loadfile", "loadstring", "debug",
        "collectgarbage", "newproxy", NULL
    };
    for (int i = 0; remove[i]; i++) {
        lua_pushnil(L);
        lua_setglobal(L, remove[i]);
    }

    /* Button constants */
    lua_pushinteger(L, 0); lua_setglobal(L, "BTN_U");
    lua_pushinteger(L, 1); lua_setglobal(L, "BTN_D");
    lua_pushinteger(L, 2); lua_setglobal(L, "BTN_L");
    lua_pushinteger(L, 3); lua_setglobal(L, "BTN_R");
    lua_pushinteger(L, 4); lua_setglobal(L, "BTN_A");

    REG("cls",     l_cls);
    REG("pset",    l_pset);
    REG("pget",    l_pget);
    REG("line",    l_line);
    REG("rect",    l_rect);
    REG("rectf",   l_rectf);
    REG("circ",    l_circ);
    REG("circf",   l_circf);
    REG("spr",     l_spr);
    REG("map",     l_map);
    REG("print",   l_print);
    REG("invert",  l_invert);

    REG("btn",     l_btn);
    REG("btnp",    l_btnp);
    REG("btnr",    l_btnr);

    REG("sfx",     l_sfx);
    REG("sfx_pat", l_sfx_pat);
    REG("music",   l_music);

    REG("rnd",     l_rnd);
    REG("mid",     l_mid);
    REG("clamp",   l_clamp);
    REG("flr",     l_flr);
    REG("abs",     l_abs);
    REG("sin",     l_sin);
    REG("cos",     l_cos);
    REG("time",    l_time);
    REG("frame",   l_frame);

    REG("peek",    l_peek);
    REG("save",    l_save);
    REG("load",    l_load);
}

void lua_api_shutdown(void) {
    if (L) { lua_close(L); L = NULL; }
}

void lua_api_unload(void) {
    /* Close the current VM, then re-init a clean one ready for the next cart. */
    lua_api_shutdown();
    active_cart = NULL;
    frame_count = 0;
    lua_api_init();
}

void lua_api_set_cart(Cart *cart) {
    active_cart = cart;
}

int lua_api_load(const uint8_t *bytecode, size_t len, const char *title) {
    frame_count = 0;
    int r = luaL_loadbuffer(L, (const char *)bytecode, len, title);
    if (r != 0) {
        fprintf(stderr, "GLYPHBOX [%s]: load error: %s\n",
                title, lua_tostring(L, -1));
        lua_pop(L, 1);
        return -1;
    }
    r = lua_pcall(L, 0, 0, 0);
    if (r != 0) {
        fprintf(stderr, "GLYPHBOX [%s]: exec error: %s\n",
                title, lua_tostring(L, -1));
        lua_pop(L, 1);
        return -1;
    }
    return 0;
}

static void call_lua_fn(const char *name) {
    lua_getglobal(L, name);
    if (lua_isfunction(L, -1)) {
        if (lua_pcall(L, 0, 0, 0) != 0) {
            fprintf(stderr, "GLYPHBOX: %s error: %s\n", name, lua_tostring(L, -1));
            lua_pop(L, 1);
        }
    } else {
        lua_pop(L, 1);
    }
}

void lua_api_call_init(void)   { call_lua_fn("_init"); }
void lua_api_call_update(void) { call_lua_fn("_update"); frame_count++; }
void lua_api_call_draw(void)   { call_lua_fn("_draw"); }
