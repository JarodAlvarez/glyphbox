/* main.c — SDL2 init; main loop; 30fps frame timing
 *
 * Three platform targets:
 *   PLATFORM_DESKTOP  — default; fork()s qr-decode.py for scanning
 *   PLATFORM_PI_HDMI  — Raspberry Pi KMS/DRM; fullscreen + picamera2
 *   PLATFORM_WEB      — Emscripten/WASM; scanning handled by JS/ZXing-js
 */
#include "renderer.h"
#include "audio.h"
#include "input.h"
#include "cart.h"
#include "lua_api.h"
#include "runtime.h"

#include <SDL2/SDL.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

#ifdef PLATFORM_WEB
/* Emscripten — no POSIX fork/exec/FIFO; main loop is callback-based */
#  include <emscripten.h>
#  include <emscripten/html5.h>
#else
/* Native — POSIX subprocess scanning */
#  include <unistd.h>     /* fork, execvp, _exit */
#  include <sys/wait.h>   /* waitpid, WNOHANG, WIFEXITED, WEXITSTATUS */
#  include <libgen.h>     /* dirname */
#  include <signal.h>     /* kill, SIGTERM */
#  include <fcntl.h>      /* open, O_RDONLY, O_NONBLOCK */
#  include <sys/stat.h>   /* mkfifo */
#endif

#define WIN_W 512
#define WIN_H 512

/* ── Console state machine ───────────────────────────────────────────────── */
typedef enum { STATE_STARTUP, STATE_SPLASH, STATE_SCANNING, STATE_CART_LOADED, STATE_RUNNING } ConsoleState;

static SDL_Window   *window       = NULL;
static SDL_Renderer *sdl_renderer = NULL;
static int           running      = 1;
static uint32_t      frame_counter = 0;
static int           splash_hold  = 0;

/* Shared across native and web paths */
static Cart         *g_cart       = NULL;
static ConsoleState  g_state      = STATE_STARTUP;
static int           startup_frame = 0;

/* ── Native-only: subprocess scanning & FIFO camera preview ─────────────── */
#ifndef PLATFORM_WEB

#define CAM_FIFO_PATH  "/tmp/glyphbox_cam.fifo"
#define CAM_W          128
#define CAM_H          128
#define CAM_HEADER     8
#define CAM_FRAME_SZ   (CAM_HEADER + CAM_W * CAM_H)

static pid_t        scan_pid      = -1;
static const char   scan_out[]   = "/tmp/glyphbox_scan.gbcart";
static char         decoder_path[PATH_MAX];

static int          cam_fifo_fd   = -1;
static SDL_Texture *cam_texture   = NULL;
static uint8_t      cam_recv[CAM_FRAME_SZ * 2];
static int          cam_recv_used = 0;
static int          cam_has_frame = 0;

static void find_decoder_path(const char *argv0) {
    char tmp[PATH_MAX];
    if (!realpath(argv0, tmp)) {
        snprintf(decoder_path, PATH_MAX, "../tools/qr-decode.py");
        return;
    }
    char tmp2[PATH_MAX];
    strncpy(tmp2, tmp, PATH_MAX - 1);
    tmp2[PATH_MAX - 1] = '\0';
    char *dir = dirname(tmp2);
    snprintf(decoder_path, PATH_MAX, "%s/../tools/qr-decode.py", dir);
}

static void cam_try_process_frames(void) {
    while (cam_recv_used >= CAM_HEADER) {
        int magic = -1;
        for (int i = 0; i <= cam_recv_used - 4; i++) {
            if (cam_recv[i]   == 'G' && cam_recv[i+1] == 'C' &&
                cam_recv[i+2] == 'A' && cam_recv[i+3] == 'M') {
                magic = i; break;
            }
        }
        if (magic < 0) {
            int keep = (cam_recv_used >= 3) ? 3 : cam_recv_used;
            memmove(cam_recv, cam_recv + cam_recv_used - keep, (size_t)keep);
            cam_recv_used = keep;
            return;
        }
        if (magic > 0) {
            memmove(cam_recv, cam_recv + magic, (size_t)(cam_recv_used - magic));
            cam_recv_used -= magic;
        }
        if (cam_recv_used < CAM_FRAME_SZ) return;

        uint16_t fw = (uint16_t)(cam_recv[4] | (cam_recv[5] << 8));
        uint16_t fh = (uint16_t)(cam_recv[6] | (cam_recv[7] << 8));
        if (fw == CAM_W && fh == CAM_H && cam_texture) {
            static uint32_t pixels[CAM_W * CAM_H];
            const uint8_t *src = cam_recv + CAM_HEADER;
            for (int i = 0; i < CAM_W * CAM_H; i++) {
                uint32_t y = src[i];
                pixels[i] = (y << 24) | (y << 16) | (y << 8) | 0xFF;
            }
            SDL_UpdateTexture(cam_texture, NULL, pixels, CAM_W * 4);
            cam_has_frame = 1;
        }
        memmove(cam_recv, cam_recv + CAM_FRAME_SZ,
                (size_t)(cam_recv_used - CAM_FRAME_SZ));
        cam_recv_used -= CAM_FRAME_SZ;
    }
}

static void start_webcam_scan(void) {
    unlink(CAM_FIFO_PATH);
    mkfifo(CAM_FIFO_PATH, 0600);
    cam_fifo_fd   = open(CAM_FIFO_PATH, O_RDONLY | O_NONBLOCK);
    cam_recv_used = 0;
    cam_has_frame = 0;

    if (!cam_texture) {
        cam_texture = SDL_CreateTexture(sdl_renderer,
            SDL_PIXELFORMAT_RGBA8888, SDL_TEXTUREACCESS_STREAMING,
            CAM_W, CAM_H);
        if (cam_texture)
            SDL_SetTextureBlendMode(cam_texture, SDL_BLENDMODE_NONE);
    }

    pid_t pid = fork();
    if (pid == 0) {
        char *args[] = {
            "python3",
            decoder_path,
#ifdef PLATFORM_PI_HDMI
            "--pi-camera",
#else
            "--webcam",
#endif
            "--headless",
            "--cam-fifo", (char *)CAM_FIFO_PATH,
            "-o", (char *)scan_out,
            NULL
        };
        execvp("python3", args);
        _exit(1);
    }
    if (pid > 0) scan_pid = pid;
    else fprintf(stderr, "GLYPHBOX: fork failed\n");
}

static int poll_scan(void) {
    if (scan_pid < 0) return -1;
    int status;
    pid_t r = waitpid(scan_pid, &status, WNOHANG);
    if (r == 0) return 0;
    scan_pid = -1;
    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) return 1;
    return -1;
}

static void abort_scan(void) {
    if (scan_pid > 0) {
        kill(scan_pid, SIGTERM);
        waitpid(scan_pid, NULL, 0);
        scan_pid = -1;
    }
    if (cam_fifo_fd >= 0) { close(cam_fifo_fd); cam_fifo_fd = -1; }
    unlink(CAM_FIFO_PATH);
    if (cam_texture) { SDL_DestroyTexture(cam_texture); cam_texture = NULL; }
    cam_recv_used = 0;
    cam_has_frame = 0;
}

#else  /* PLATFORM_WEB — stubs so the rest of the file compiles cleanly */

static int  cam_has_frame = 0;
static void start_webcam_scan(void) {
    /* Signal JS to activate its camera scanner overlay */
    EM_ASM( GlyphboxScanner.start(); );
}
static int  poll_scan(void)  { return 0; }   /* JS drives the cart load */
static void abort_scan(void) {
    EM_ASM( GlyphboxScanner.stop(); );
}

#endif /* PLATFORM_WEB */

/* ── Cart loading ────────────────────────────────────────────────────────── */
static Cart *load_cart(const char *path) {
    Cart *c = cart_load_file(path);
    if (!c) { fprintf(stderr, "GLYPHBOX: failed to load: %s\n", path); return NULL; }
    lua_api_set_cart(c);
    renderer_set_sprites(c->sprites);
    renderer_set_tilemap(c->tilemap);
    audio_set_sfx_data(c->sfx_data,    sizeof(c->sfx_data));
    audio_set_music_data(c->music_data, sizeof(c->music_data));
    if (lua_api_load(c->bytecode, c->bytecode_len, c->title) != 0) {
        cart_free(c); return NULL;
    }
    lua_api_call_init();
    return c;
}

/* ── Web cart loader — called from JS after ZXing assembles all chunks ───── */
#ifdef PLATFORM_WEB
EMSCRIPTEN_KEEPALIVE
void web_load_cart(const uint8_t *data, int len) {
    /* len == 0 → cancel signal from JS scanner (user pressed Cancel) */
    if (len <= 0) { g_state = STATE_SPLASH; return; }

    /* Write the assembled .gbcart bytes into the Emscripten virtual FS,
       then go through the normal load path so every subsystem is set up
       identically to the native build.                                   */
    FILE *f = fopen("/tmp/web_scan.gbcart", "wb");
    if (!f) { fprintf(stderr, "GLYPHBOX: web_load_cart: fopen failed\n"); return; }
    fwrite(data, 1, (size_t)len, f);
    fclose(f);

    if (g_cart) { cart_free(g_cart); g_cart = NULL; lua_api_unload(); }

    g_cart = load_cart("/tmp/web_scan.gbcart");
    if (g_cart) {
        audio_jingle_play();
        splash_hold = 30;
        g_state = STATE_CART_LOADED;
    } else {
        g_state = STATE_SPLASH;
    }
}
#endif

/* ── Screen drawing ──────────────────────────────────────────────────────── */

/* Dreamcast-style boot animation: logo elements reveal in sync with the
   ascending startup chime.  Frame offsets match STARTUP_SEQ note boundaries:
     f < 6:  black screen (bass hit plays)
     f >= 6:  outer ring  (C4 note)
     f >= 11: inner ring  (G4 note)
     f >= 16: centre square (C5 note)
     f >= 21: dot row     (E5 note)
     f >= 26: wordmark    (G5 held) + 2-frame flash   */
static void draw_startup(int f) {
    renderer_cls(0);

    if (f >= 6) {
        renderer_rectf(44, 28, 40, 40, 1);   /* outer ring fill */
        renderer_rectf(48, 32, 32, 32, 0);   /* outer ring cutout */
    }
    if (f >= 11) {
        renderer_rectf(52, 36, 24, 24, 1);   /* inner ring fill */
        renderer_rectf(56, 40, 16, 16, 0);   /* inner ring cutout */
    }
    if (f >= 16)
        renderer_rectf(60, 44,  8,  8, 1);   /* centre square */

    if (f >= 21)
        for (int i = 0; i < 5; i++)
            renderer_rectf(48 + i * 7, 74, 4, 4, 1);  /* dot row */

    if (f >= 26)
        renderer_print("GLYPHBOX", 40, 82, 1);

    /* 2-frame white flash the moment the wordmark appears */
    if (f == 26 || f == 27)
        renderer_invert();
}

static void draw_splash(void) {
    renderer_cls(0);

    /* ── Logo: 2 rings + centre square, centred at (64, 48) ───────────────
     * Both rings 4px thick.  Gap between rings: 4px.  Gap to centre: 4px.
     * Centre: 8×8 solid.  Total icon: 40×40px.
     * Each ring = rectf fill (colour 1) + rectf cutout (colour 0).          */
    renderer_rectf(44, 28, 40, 40, 1);   /* outer ring fill  (40×40)        */
    renderer_rectf(48, 32, 32, 32, 0);   /* outer ring cutout — 4px ring    */
    renderer_rectf(52, 36, 24, 24, 1);   /* inner ring fill  (24×24)        */
    renderer_rectf(56, 40, 16, 16, 0);   /* inner ring cutout — 4px ring    */
    renderer_rectf(60, 44,  8,  8, 1);   /* centre square    ( 8×8 solid)   */

    /* ── Dot separator: 5 × 4px dots, aligned with outer ring inner edge ── */
    /* Outer ring cutout spans x=48..79 (32px). 5 dots × 4px + 4 gaps × 3px = 32px. */
    for (int i = 0; i < 5; i++)
        renderer_rectf(48 + i * 7, 74, 4, 4, 1);

    /* ── Wordmark ── */
    renderer_print("GLYPHBOX", 40, 82, 1);

    /* ── Prompt ── */
#ifdef PLATFORM_WEB
    renderer_print("TAP TO SCAN CARD", 16, 96, 1);
#else
    //renderer_print("INSERT CARTRIDGE", 16, 96, 1);
#endif
    if ((frame_counter % 30) >= 15)
        renderer_print("A: SCAN CARD", 28, 108, 1);

    /* ── Copyright ── */
    renderer_print("(C) Gureedo 2026", 16, 118, 1);
}

static void draw_cart_loaded(Cart *c) {
    renderer_cls(0);
    renderer_rect(2, 2, 124, 124, 1);
    renderer_print("GLYPHBOX", 40, 8, 1);
    renderer_rectf(4, 18, 120, 1, 1);
    if (c && c->title[0]) {
        int len = (int)strlen(c->title);
        int tx  = (128 - len * 6) / 2;
        renderer_print(c->title, tx < 4 ? 4 : tx, 42, 1);
    }
    renderer_rectf(4, 54, 120, 1, 1);
    renderer_print("CART LOADED", 31, 64, 1);
    static const char * const dots[3] = { ".  ", ".. ", "..." };
    renderer_print(dots[(frame_counter / 6) % 3], 55, 80, 1);
}

static void draw_splash_scan(void) {
    renderer_cls(0);
    renderer_print("GLYPHBOX", 40, 20, 1);
    int scan_y = (int)(frame_counter * 2) % 128;
    renderer_rectf(0, scan_y,     128, 2, 1);
    if (scan_y >= 2) renderer_rectf(0, scan_y - 2, 128, 1, 1);
#ifdef PLATFORM_WEB
    renderer_print("POINT CAMERA AT", 16, 90, 1);
    renderer_print("CARD REAR FACE", 20, 100, 1);
#else
    renderer_print("SCANNING CARD...", 16, 90, 1);
    renderer_print("CAMERA STARTING...", 12, 100, 1);
#endif
}

/* ── One game-loop tick (extracted so Emscripten can use it as callback) ─── */
static uint32_t last_tick = 0;

static void game_loop_tick(void) {
    /* ── Events ── */
    SDL_Event e;
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_QUIT) running = 0;
        if (e.type == SDL_CONTROLLERDEVICEADDED)
            input_controller_added(e.cdevice.which);
        if (e.type == SDL_CONTROLLERDEVICEREMOVED)
            input_controller_removed(e.cdevice.which);
        if (e.type == SDL_KEYDOWN && e.key.keysym.sym == SDLK_ESCAPE) {
            if (g_state == STATE_STARTUP) {
                g_state = STATE_SPLASH;
            } else if (g_state == STATE_RUNNING || g_state == STATE_CART_LOADED) {
                audio_music(-1);
                cart_free(g_cart); g_cart = NULL;
                lua_api_unload();
                g_state = STATE_SPLASH;
            } else if (g_state == STATE_SCANNING) {
                abort_scan();
                g_state = STATE_SPLASH;
            } else {
                running = 0;
            }
        }
    }

    /* ── Input ── */
    input_update();

    /* ── State machine ── */
    if (g_state == STATE_STARTUP) {
        if (startup_frame == 0) audio_startup_play();
        draw_startup(startup_frame);
        startup_frame++;
        /* Transition to splash once chime finishes (and we've played at least
           30 frames so the logo is fully visible before cutting away)        */
        if (!audio_startup_active() && startup_frame > 30)
            g_state = STATE_SPLASH;
    }
    else if (g_state == STATE_SPLASH) {
        draw_splash();
        if (input_btnp(BTN_A)) {
            start_webcam_scan();
            g_state = STATE_SCANNING;
        }
    }
    else if (g_state == STATE_SCANNING) {
#ifndef PLATFORM_WEB
        /* Native: drain FIFO for camera preview frames */
        if (cam_fifo_fd >= 0) {
            uint8_t tmp[CAM_FRAME_SZ];
            for (;;) {
                ssize_t n = read(cam_fifo_fd, tmp, sizeof(tmp));
                if (n <= 0) break;
                if (cam_recv_used + (int)n > (int)sizeof(cam_recv))
                    cam_recv_used = 0;
                memcpy(cam_recv + cam_recv_used, tmp, (size_t)n);
                cam_recv_used += (int)n;
                cam_try_process_frames();
            }
        }
        if (!cam_has_frame) draw_splash_scan();

        int result = poll_scan();
        if (result == 1) {
            g_cart = load_cart(scan_out);
            abort_scan();
            if (g_cart) {
                audio_jingle_play();
                splash_hold = 30;
                g_state = STATE_CART_LOADED;
            } else {
                g_state = STATE_SPLASH;
            }
        } else if (result == -1) {
            abort_scan();
            g_state = STATE_SPLASH;
        }
#else
        /* Web: JS scanner overlay is active; just show the pixel art animation.
           State transitions happen when JS calls web_load_cart().            */
        draw_splash_scan();
#endif
    }
    else if (g_state == STATE_CART_LOADED) {
        draw_cart_loaded(g_cart);
        if (audio_jingle_active()) {
            splash_hold = 30;
        } else if (splash_hold > 0) {
            splash_hold--;
        } else {
            g_state = STATE_RUNNING;
        }
    }
    else { /* STATE_RUNNING */
        if (input_reset_combo()) {
            audio_music(-1);
            cart_free(g_cart); g_cart = NULL;
            lua_api_unload();
            g_state = STATE_SPLASH;
#ifdef PLATFORM_WEB
            EM_ASM( GlyphboxScanner.showScanButton(); );
#endif
        }
        lua_api_call_update();
        lua_api_call_draw();
    }

    /* ── Audio tick ── */
    audio_frame_tick();

    /* ── Render ── */
    SDL_RenderClear(sdl_renderer);
#ifndef PLATFORM_WEB
    if (g_state == STATE_SCANNING && cam_has_frame)
        SDL_RenderCopy(sdl_renderer, cam_texture, NULL, NULL);
    else
#endif
        renderer_frame();
    SDL_RenderPresent(sdl_renderer);

    frame_counter++;

#ifndef PLATFORM_WEB
    /* ── 30fps cap (native only — Emscripten handles timing via rAF) ── */
    const int FRAME_MS = 1000 / 30;
    uint32_t  now      = SDL_GetTicks();
    int       elapsed  = (int)(now - last_tick);
    if (elapsed < FRAME_MS) SDL_Delay((uint32_t)(FRAME_MS - elapsed));
    last_tick = SDL_GetTicks();
#endif
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
int main(int argc, char *argv[]) {
    const char *argv0     = (argc >= 1) ? argv[0] : "glyphbox";
    const char *cart_path = (argc >= 2) ? argv[1] : NULL;

#ifndef PLATFORM_WEB
    find_decoder_path(argv0);
#else
    (void)argv0;
#endif

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMECONTROLLER) < 0) {
        fprintf(stderr, "GLYPHBOX: SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

#ifdef PLATFORM_PI_HDMI
    window = SDL_CreateWindow("GLYPHBOX",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WIN_W, WIN_H, SDL_WINDOW_FULLSCREEN_DESKTOP);
#else
    window = SDL_CreateWindow("GLYPHBOX",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WIN_W, WIN_H, SDL_WINDOW_SHOWN);
#endif
    if (!window) {
        fprintf(stderr, "GLYPHBOX: SDL_CreateWindow failed: %s\n", SDL_GetError());
        SDL_Quit(); return 1;
    }

    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    sdl_renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!sdl_renderer)
        sdl_renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    if (!sdl_renderer) {
        fprintf(stderr, "GLYPHBOX: SDL_CreateRenderer failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window); SDL_Quit(); return 1;
    }

    SDL_RenderSetLogicalSize(sdl_renderer, 128, 128);

    runtime_init();
    renderer_init(sdl_renderer);
    audio_init();
    input_init();
    lua_api_init();

    if (cart_path) {
        /* Direct cart load — skip startup animation */
        g_cart = load_cart(cart_path);
        if (g_cart) { audio_jingle_play(); g_state = STATE_CART_LOADED; }
        else g_state = STATE_SPLASH;
    }
    /* else: g_state stays STATE_STARTUP; chime plays on first tick */

    last_tick = SDL_GetTicks();

#ifdef PLATFORM_WEB
    /* Hand control to the browser's requestAnimationFrame loop.
       The third argument (1) means Emscripten calls exit() when running=0,
       but for a web app we never want to exit, so we pass 0 (infinite loop). */
    emscripten_set_main_loop(game_loop_tick, 0, 1);
#else
    while (running) game_loop_tick();

    /* ── Cleanup (native only — browser tab close handles web cleanup) ── */
    abort_scan();
    if (g_cart) cart_free(g_cart);
    lua_api_shutdown();
    input_shutdown();
    audio_shutdown();
    runtime_shutdown();
    SDL_DestroyRenderer(sdl_renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
#endif
    return 0;
}
