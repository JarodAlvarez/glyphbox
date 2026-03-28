cmake_minimum_required(VERSION 3.20)
project(glyphbox_web C)

set(CMAKE_C_STANDARD 99)

# ── Emscripten guard ──────────────────────────────────────────────────────────
# This build MUST be configured with emcmake:
#
#   cd glyphbox/
#   emcmake cmake -B build-web web/ -DCMAKE_BUILD_TYPE=Release
#   cmake --build build-web
#
# Output: build-web/glyphbox.html  glyphbox.js  glyphbox.wasm
#
if(NOT EMSCRIPTEN)
    message(FATAL_ERROR
        "This CMakeLists.txt is for the Emscripten/WebAssembly build only.\n"
        "Configure with:  emcmake cmake -B build-web web/\n"
        "For native builds use the root CMakeLists.txt instead.")
endif()

add_compile_definitions(PLATFORM_WEB)

# ── Lua 5.4 source ────────────────────────────────────────────────────────────
# We bundle Lua 5.4 (standard C) rather than LuaJIT because LuaJIT's JIT
# engine is x86/ARM assembly and cannot compile to WebAssembly.
# Lua 5.4 API is a superset of what GLYPHBOX uses.
#
# Setup (one-time):
#   curl -L https://www.lua.org/ftp/lua-5.4.7.tar.gz | tar xz -C web/
#   mv web/lua-5.4.7/src web/lua54
#   rm -rf web/lua-5.4.7
#
set(LUA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/lua54")
if(NOT EXISTS "${LUA_DIR}/lua.h")
    message(FATAL_ERROR
        "Lua 5.4 source not found at web/lua54/\n"
        "Run from the repo root:\n"
        "  curl -L https://www.lua.org/ftp/lua-5.4.7.tar.gz | tar xz -C web/\n"
        "  mv web/lua-5.4.7/src web/lua54 && rm -rf web/lua-5.4.7")
endif()

set(LUA_SOURCES
    ${LUA_DIR}/lapi.c     ${LUA_DIR}/lcode.c    ${LUA_DIR}/lctype.c
    ${LUA_DIR}/ldebug.c   ${LUA_DIR}/ldo.c      ${LUA_DIR}/ldump.c
    ${LUA_DIR}/lfunc.c    ${LUA_DIR}/lgc.c      ${LUA_DIR}/linit.c
    ${LUA_DIR}/llex.c     ${LUA_DIR}/lmem.c     ${LUA_DIR}/lobject.c
    ${LUA_DIR}/lopcodes.c ${LUA_DIR}/lparser.c  ${LUA_DIR}/lstate.c
    ${LUA_DIR}/lstring.c  ${LUA_DIR}/ltable.c   ${LUA_DIR}/ltm.c
    ${LUA_DIR}/lundump.c  ${LUA_DIR}/lvm.c      ${LUA_DIR}/lzio.c
    ${LUA_DIR}/lauxlib.c
    ${LUA_DIR}/lbaselib.c ${LUA_DIR}/lcorolib.c ${LUA_DIR}/ldblib.c
    ${LUA_DIR}/liolib.c   ${LUA_DIR}/lmathlib.c ${LUA_DIR}/loadlib.c
    ${LUA_DIR}/loslib.c   ${LUA_DIR}/lstrlib.c  ${LUA_DIR}/ltablib.c
    ${LUA_DIR}/lutf8lib.c
)

# ── GLYPHBOX source files ─────────────────────────────────────────────────────
set(SRC "${CMAKE_CURRENT_SOURCE_DIR}/../src")
set(GLYPHBOX_SOURCES
    ${SRC}/main.c
    ${SRC}/runtime.c
    ${SRC}/renderer.c
    ${SRC}/audio.c
    ${SRC}/input.c
    ${SRC}/cart.c
    ${SRC}/lua_api.c
)

add_executable(glyphbox ${GLYPHBOX_SOURCES} ${LUA_SOURCES})

target_include_directories(glyphbox PRIVATE
    ${LUA_DIR}
    ${SRC}
)

# USE_SDL=2 and USE_ZLIB=1 must be passed at compile time so Emscripten
# can supply the SDL2/SDL.h and zlib.h headers from its built-in ports.
target_compile_options(glyphbox PRIVATE
    "-sUSE_SDL=2"
    "-sUSE_ZLIB=1"
)

# ── Emscripten link flags ─────────────────────────────────────────────────────
set(EM_FLAGS
    # Built-in Emscripten ports (no system install needed)
    "-s USE_SDL=2"
    "-s USE_ZLIB=1"

    # WASM output
    "-s WASM=1"
    "-s ALLOW_MEMORY_GROWTH=1"

    # Export the JS-callable cart loader + standard runtime helpers
    "-s EXPORTED_FUNCTIONS=[\"_main\",\"_web_load_cart\"]"
    "-s EXPORTED_RUNTIME_METHODS=[\"ccall\",\"cwrap\"]"

    # Replace the blocking main loop with emscripten_set_main_loop (set in main.c)
    # ASYNCIFY is NOT needed because we use the callback-based loop.

    # Custom HTML shell (adds scanner UI around the canvas)
    "--shell-file ${CMAKE_CURRENT_SOURCE_DIR}/shell.html"

    # Optimise for size+speed in release builds
    "$<$<CONFIG:Release>:-O2>"
    "$<$<CONFIG:Debug>:-g>"
)

string(JOIN " " EM_FLAGS_STR ${EM_FLAGS})
set_target_properties(glyphbox PROPERTIES
    OUTPUT_NAME "glyphbox"
    SUFFIX      ".html"
    LINK_FLAGS  "${EM_FLAGS_STR}"
)
