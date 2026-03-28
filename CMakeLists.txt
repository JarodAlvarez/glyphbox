cmake_minimum_required(VERSION 3.20)
project(glyphbox C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Platform option: DESKTOP (default), PI_HDMI, PI_SPI
#
# Desktop build (default):
#   cmake -B build && cmake --build build
#
# Raspberry Pi build (run on the Pi):
#   cmake -B build -DPLATFORM=PI_HDMI && cmake --build build
#
set(PLATFORM "DESKTOP" CACHE STRING "Target platform")
set_property(CACHE PLATFORM PROPERTY STRINGS DESKTOP PI_HDMI PI_SPI)
add_compile_definitions(PLATFORM_${PLATFORM})

# ── Platform-specific compiler flags ──────────────────────────────────────────
if(PLATFORM STREQUAL "PI_HDMI" OR PLATFORM STREQUAL "PI_SPI")
    # Build directly on the Pi so -march=native tunes for the installed CPU
    # (Cortex-A72 on Pi 4, Cortex-A76 on Pi 5, etc.)
    add_compile_options(-march=native -O2)
endif()

# Build type flags
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g)
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O2)
endif()

# Find SDL2
find_package(SDL2 QUIET)
if(NOT SDL2_FOUND)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SDL2 REQUIRED sdl2)
endif()

# Find LuaJIT
find_package(PkgConfig REQUIRED)
pkg_check_modules(LUAJIT REQUIRED luajit)

# ZBar — only required on DESKTOP.
# Aztec scanning is handled entirely by Python (zxing-cpp) on all platforms;
# ZBar is not referenced in any C source file.  Pi installations typically
# don't have libzbar-dev, so skip the hard dependency there.
if(PLATFORM STREQUAL "DESKTOP")
    pkg_check_modules(ZBAR zbar)   # soft: warn but don't abort if missing
endif()

# Source files
set(SOURCES
    src/main.c
    src/runtime.c
    src/renderer.c
    src/audio.c
    src/input.c
    src/cart.c
    src/lua_api.c
)

add_executable(glyphbox ${SOURCES})

# Include dirs
target_include_directories(glyphbox PRIVATE
    ${SDL2_INCLUDE_DIRS}
    ${LUAJIT_INCLUDE_DIRS}
    src/
)
if(ZBAR_FOUND)
    target_include_directories(glyphbox PRIVATE ${ZBAR_INCLUDE_DIRS})
endif()

# Link directories from pkg-config
target_link_directories(glyphbox PRIVATE
    ${SDL2_LIBRARY_DIRS}
    ${LUAJIT_LIBRARY_DIRS}
)
if(ZBAR_FOUND)
    target_link_directories(glyphbox PRIVATE ${ZBAR_LIBRARY_DIRS})
endif()

# Link libraries
target_link_libraries(glyphbox
    ${SDL2_LIBRARIES}
    ${LUAJIT_LIBRARIES}
    z
    m
)
if(ZBAR_FOUND)
    target_link_libraries(glyphbox ${ZBAR_LIBRARIES})
endif()

# macOS-specific frameworks
if(APPLE)
    target_link_libraries(glyphbox
        "-framework CoreAudio"
        "-framework AudioUnit"
        "-framework CoreFoundation"
    )
endif()

# Compiler flags from pkg-config
target_compile_options(glyphbox PRIVATE
    ${SDL2_CFLAGS_OTHER}
    ${LUAJIT_CFLAGS_OTHER}
)
if(ZBAR_FOUND)
    target_compile_options(glyphbox PRIVATE ${ZBAR_CFLAGS_OTHER})
endif()
