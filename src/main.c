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

/* ── Menu overlay ─────────────────────────────────────────────────────────
   Triangle is the single menu button: opens/closes an overlay with volume
   control, exit-to-splash, and shutdown.  Available from any state except
   STATE_STARTUP (triangle there just skips the boot animation, as before). */
typedef enum { MENU_VOLUME, MENU_EXIT, MENU_SHUTDOWN, MENU_CONSOLE } MenuAction;
static int        menu_active   = 0;
static int        menu_cursor   = 0;
static MenuAction menu_rows[4];
static int        menu_debug    = 0;   /* hidden EXIT TO CONSOLE row unlocked */
static int        menu_seq_pos  = 0;   /* progress through the unlock sequence */
static int        menu_row_count = 0;
static int           startup_frame = 0;

/* ── Native-only: subprocess scanning & FIFO camera preview ─────────────── */
#ifndef PLATFORM_WEB

#define CAM_FIFO_PATH  "/tmp/glyphbox_cam.fifo"
#define SCAN_PKT_SZ    10     /* 'GSCN' pos total cur rsvd mask(uint16 LE) */
#define SCAN_POS_NONE  255    /* scanner has no view of the card slot      */

/* Scan screen geometry: a 54×68 card slides down between two rails */
#define SCAN_CARD_X      37
#define SCAN_CARD_W      54
#define SCAN_CARD_H      68
#define SCAN_CARD_OUT_Y  (-56)   /* fully out of view (clipped at y=14)      */
#define SCAN_CARD_IN_Y   30      /* seated against the stop                  */

static pid_t        scan_pid      = -1;
static const char   scan_out[]   = "/tmp/glyphbox_scan.gbcart";
static char         decoder_path[PATH_MAX];

static int          cam_fifo_fd   = -1;
static uint8_t      cam_recv[SCAN_PKT_SZ * 16];
static int          cam_recv_used = 0;

/* Latest status from the scanner, plus animation state for draw_scan() */
static int          scan_ready    = 0;    /* first packet seen: camera is up */
static int          scan_pos      = SCAN_POS_NONE;
static int          scan_total    = 0;
static int          scan_cur      = 255;
static unsigned     scan_mask     = 0;
static int          scan_card_y   = 0;    /* eased on-screen card position   */
static int          scan_ok_card  = 0;    /* card number just captured       */
static int          scan_ok_hold  = 0;    /* frames left of the "OK" banner  */
static uint32_t     scan_frame    = 0;

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

static void scan_read_status(void) {
    if (cam_fifo_fd < 0) return;
    for (;;) {
        ssize_t n = read(cam_fifo_fd, cam_recv + cam_recv_used,
                         sizeof(cam_recv) - (size_t)cam_recv_used);
        if (n <= 0) break;
        cam_recv_used += (int)n;

        int i = 0;
        while (cam_recv_used - i >= SCAN_PKT_SZ) {
            const uint8_t *p = cam_recv + i;
            if (p[0] != 'G' || p[1] != 'S' || p[2] != 'C' || p[3] != 'N') {
                i++;                       /* resync on the magic */
                continue;
            }
            unsigned mask = (unsigned)(p[8] | (p[9] << 8));
            unsigned fresh = mask & ~scan_mask;
            if (fresh) {
                int idx = 0;
                while (!(fresh & (1u << idx))) idx++;
                scan_ok_card = idx + 1;
                scan_ok_hold = 45;
                audio_scan_ok_play();
            }
            scan_pos   = p[4];
            scan_total = p[5];
            scan_cur   = p[6];
            scan_mask  = mask;
            scan_ready = 1;
            i += SCAN_PKT_SZ;
        }
        memmove(cam_recv, cam_recv + i, (size_t)(cam_recv_used - i));
        cam_recv_used -= i;
    }
}

static void start_webcam_scan(void) {
    unlink(CAM_FIFO_PATH);
    mkfifo(CAM_FIFO_PATH, 0600);
    cam_fifo_fd   = open(CAM_FIFO_PATH, O_RDONLY | O_NONBLOCK);
    cam_recv_used = 0;
    scan_ready    = 0;
    scan_pos      = SCAN_POS_NONE;
    scan_total    = 0;
    scan_cur      = 255;
    scan_mask     = 0;
    scan_card_y   = SCAN_CARD_OUT_Y;
    scan_ok_hold  = 0;
    scan_frame    = 0;

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
    scan_read_status();   /* also covers mid-game scans driven from Lua */
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
    cam_recv_used = 0;
}

#else  /* PLATFORM_WEB — stubs so the rest of the file compiles cleanly */

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

/* ── Shared UI chrome ────────────────────────────────────────────────────── */

static void ui_print_centred(const char *str, int y, int c) {
    renderer_print(str, (128 - ((int)strlen(str) * 6 - 1)) / 2, y, c);
}

/* Inverted title bar with the nested-squares logo mark at the right */
static void ui_header(const char *title) {
    renderer_rectf(0, 0, 128, 13, 1);
    renderer_print(title, 6, 3, 0);
    renderer_rect(113, 2, 9, 9, 0);
    renderer_rect(115, 4, 5, 5, 0);
    renderer_pset(117, 6, 0);
}

/* A button hint followed by its label */
static int ui_hint_width(const char *label) {
    return HINT_W + 4 + (int)strlen(label) * 6 - 1;
}

static void ui_hint(int which, const char *label, int x, int y) {
    renderer_button_hint(which, x, y, 1);
    renderer_print(label, x + HINT_W + 4, y, 1);
}

/* Footer rule with a button hint at the left and, optionally, the right */
static void ui_footer(int lwhich, const char *llabel,
                      int rwhich, const char *rlabel) {
    renderer_rectf(0, 112, 128, 1, 1);
    ui_hint(lwhich, llabel, 4, 117);
    if (rlabel)
        ui_hint(rwhich, rlabel, 124 - ui_hint_width(rlabel), 117);
}

/* Splash intro: after the boot animation the logo slides up from the centre
   of the screen while the copyright and footer rise in from the bottom.
   splash_intro counts frames into that move; at SPLASH_INTRO_FRAMES the
   screen is at rest (also the value when the splash is reached any other way). */
#define SPLASH_INTRO_FRAMES 12
#define SPLASH_LOGO_RISE    14      /* boot logo sits this far below the splash logo */
#define SPLASH_FOOTER_RISE  36      /* copyright + footer start this far down        */
static int splash_intro = SPLASH_INTRO_FRAMES;

static void draw_splash(void) {
    renderer_cls(0);

    /* Ease-out: remaining travel shrinks with the square of the time left */
    int left = SPLASH_INTRO_FRAMES - splash_intro;
    int den  = SPLASH_INTRO_FRAMES * SPLASH_INTRO_FRAMES;
    int ly   = 14 + SPLASH_LOGO_RISE   * left * left / den;   /* logo top   */
    int fy   =      SPLASH_FOOTER_RISE * left * left / den;   /* footer dy  */
    int rest = (left == 0);
    if (!rest) splash_intro++;

    /* ── Logo: 2 rings + centre square ────────────────────────────────────
     * Both rings 4px thick.  Gap between rings: 4px.  Gap to centre: 4px.
     * Centre: 8×8 solid.  Total icon: 40×40px.
     * Each ring = rectf fill (colour 1) + rectf cutout (colour 0).          */
    renderer_rectf(44, ly,      40, 40, 1);   /* outer ring fill  (40×40)   */
    renderer_rectf(48, ly +  4, 32, 32, 0);   /* outer ring cutout          */
    renderer_rectf(52, ly +  8, 24, 24, 1);   /* inner ring fill  (24×24)   */
    renderer_rectf(56, ly + 12, 16, 16, 0);   /* inner ring cutout          */
    renderer_rectf(60, ly + 16,  8,  8, 1);   /* centre square    ( 8×8)    */

    /* ── Dot separator: 5 × 4px dots, aligned with outer ring inner edge ── */
    /* Outer ring cutout spans x=48..79 (32px). 5 dots × 4px + 4 gaps × 3px = 32px. */
    for (int i = 0; i < 5; i++)
        renderer_rectf(48 + i * 7, ly + 46, 4, 4, 1);

    /* ── Wordmark ── */
    renderer_print("GLYPHBOX", 40, ly + 54, 1);

    /* ── Copyright ── */
    renderer_print("(C) Gureedo 2026", 16, 94 + fy, 1);

    /* ── Footer: the scan prompt flashes once everything is at rest ── */
    int flash_on = !rest || (frame_counter % 30) < 15;
    renderer_rectf(0, 112 + fy, 128, 1, 1);
#ifdef PLATFORM_WEB
    if (flash_on) renderer_print("TAP TO SCAN CARD", 16, 117 + fy, 1);
#else
    if (flash_on) ui_hint(HINT_ACTION, "SCAN CARD", 4, 117 + fy);
    ui_hint(HINT_MENU, "MENU", 124 - ui_hint_width("MENU"), 117 + fy);
#endif
}

static void draw_cart_loaded(Cart *c) {
    /* Frames since this screen appeared: restart whenever a frame was drawn
       by something else in between.                                        */
    static uint32_t prev_frame = 0;
    static int      t          = 0;
    if (frame_counter != prev_frame + 1) t = 0;
    prev_frame = frame_counter;
    t++;

    renderer_cls(0);
    ui_header("CART LOADED");

    if (c && c->title[0]) {
        int len = (int)strlen(c->title);
        if (len <= 10)   /* fits at double size */
            renderer_print_scaled(c->title, (128 - (len * 12 - 2)) / 2, 44, 1, 2);
        else
            ui_print_centred(c->title, 48, 1);
    }
    if (c && c->author[0]) {
        char by[16];
        snprintf(by, sizeof by, "BY %s", c->author);
        ui_print_centred(by, 66, 1);
    }

    /* Logo dot row fills while the jingle plays */
    for (int i = 0; i < 5; i++) {
        if (t > 6 + i * 9) renderer_rectf(48 + i * 7, 90, 4, 4, 1);
        else               renderer_rectf(49 + i * 7, 91, 2, 2, 1);
    }
}

/* Populate menu_rows[] based on the state the menu was opened from. */
static void menu_open(void) {
    menu_cursor    = 0;
    menu_row_count = 0;
    menu_seq_pos   = 0;
    menu_debug     = 0;
    menu_rows[menu_row_count++] = MENU_VOLUME;
    if (g_state == STATE_RUNNING)
        menu_rows[menu_row_count++] = MENU_EXIT;
#ifndef PLATFORM_WEB
    menu_rows[menu_row_count++] = MENU_SHUTDOWN;
#endif
    menu_active = 1;
}

#ifndef PLATFORM_WEB
/* Hidden debug unlock: with the menu open, enter U U D D L R.  Reveals an
   EXIT TO CONSOLE row that quits cleanly so systemd does not restart us. */
static void menu_debug_check(void) {
    static const int seq[6] = { BTN_U, BTN_U, BTN_D, BTN_D, BTN_L, BTN_R };
    if (menu_debug) return;
    int pressed = -1;
    for (int b = BTN_U; b <= BTN_R; b++)
        if (input_btnp(b)) { pressed = b; break; }
    if (pressed < 0) return;
    if (pressed == seq[menu_seq_pos]) {
        if (++menu_seq_pos == 6) {
            menu_debug = 1;
            menu_rows[menu_row_count++] = MENU_CONSOLE;
            menu_cursor = menu_row_count - 1;
        }
    } else {
        menu_seq_pos = (pressed == seq[0]) ? 1 : 0;
    }
}
#endif

static const char *menu_row_label(MenuAction a) {
    switch (a) {
        case MENU_VOLUME:   return "VOLUME";
        case MENU_EXIT:     return "EXIT GAME";
        case MENU_SHUTDOWN: return "SHUTDOWN";
        case MENU_CONSOLE:  return "EXIT TO CONSOLE";
    }
    return "";
}

static void draw_menu(void) {
    renderer_cls(0);
    ui_header("MENU");

    int y = 22;
    for (int i = 0; i < menu_row_count; i++) {
        MenuAction a   = menu_rows[i];
        int        sel = (menu_cursor == i);
        int        h   = (a == MENU_VOLUME) ? 26 : 13;
        int        ink = sel ? 0 : 1;

        /* Selected row is a solid bar with the text knocked out */
        if (sel) renderer_rectf(4, y - 3, 120, h, 1);
        renderer_print(menu_row_label(a), 10, y, ink);

        if (a == MENU_VOLUME) {
            int steps = (int)(audio_get_volume() * 10.0f + 0.5f);  /* 0–10 */
            for (int s = 0; s < 10; s++) {
                if (s < steps) renderer_rectf(10 + s * 11, y + 11, 9, 7, ink);
                else           renderer_rect (10 + s * 11, y + 11, 9, 7, ink);
            }
            y += 32;
        } else {
            y += 16;
        }
    }

    ui_footer(HINT_ACTION, "OK", HINT_MENU, "BACK");
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

#ifndef PLATFORM_WEB
/* Native scan screen: a drawn card that follows the real one into the slot.
   Everything goes through the 1-bit framebuffer; the scanner only sends
   status (see scan_read_status).                                           */
static void scan_print_centred(const char *str, int y) {
    renderer_print(str, (128 - (int)strlen(str) * 6) / 2 + 1, y, 1);
}

static void draw_scan_card(int cy) {
    const int cx = SCAN_CARD_X;
    renderer_rectf(cx, cy, SCAN_CARD_W, SCAN_CARD_H, 1);
    renderer_rectf(cx + 2, cy, 6, SCAN_CARD_H, 0);        /* title strip   */

    /* Aztec block: scattered modules around a bullseye */
    int bx = cx + 12, by = cy + 6;
    for (int y = 0; y < 18; y++)
        for (int x = 0; x < 18; x++)
            if ((x * 7 + y * 13 + x * y) % 5 < 2)
                renderer_rectf(bx + x * 2, by + y * 2, 2, 2, 0);
    renderer_rectf(bx + 11, by + 11, 14, 14, 1);
    renderer_rectf(bx + 12, by + 12, 12, 12, 0);
    renderer_rectf(bx + 14, by + 14,  8,  8, 1);
    renderer_rectf(bx + 16, by + 16,  4,  4, 0);

    /* Insert arrow on the leading edge */
    for (int k = 0; k < 4; k++)
        renderer_rectf(cx + 24 + k, cy + 54 + k, 8 - 2 * k, 1, 0);
}

static void draw_scan(void) {
    renderer_cls(0);

    /* ── Where the card should be ── */
    int target = SCAN_CARD_OUT_Y;
    if (scan_pos == SCAN_POS_NONE) {
        /* No slot view (desktop webcam): loop an insert hint, or hold the
           card seated while one is being read.                            */
        int t = (int)(scan_frame % 75);
        int hint = SCAN_CARD_OUT_Y +
                   (SCAN_CARD_IN_Y - SCAN_CARD_OUT_Y) * (t < 45 ? t : 45) / 45;
        scan_card_y = (scan_cur != 255 || scan_ok_hold > 0) ? SCAN_CARD_IN_Y : hint;
        target = scan_card_y;
    } else if (scan_ready) {
        target = SCAN_CARD_OUT_Y +
                 (SCAN_CARD_IN_Y - SCAN_CARD_OUT_Y) * scan_pos / 100;
    }
    /* Ease toward the target so sparse scanner updates still move smoothly */
    int d = target - scan_card_y;
    if (d > 0)      scan_card_y += (d + 2) / 3;
    else if (d < 0) scan_card_y -= (-d + 2) / 3;

    /* ── Seat outline, card, then mask everything above the slot mouth ── */
    for (int k = 0; k < SCAN_CARD_W; k += 4)
        renderer_rectf(SCAN_CARD_X + k, SCAN_CARD_IN_Y, 2, 1, 1);
    for (int k = 0; k < SCAN_CARD_H; k += 4) {
        renderer_rectf(SCAN_CARD_X, SCAN_CARD_IN_Y + k, 1, 2, 1);
        renderer_rectf(SCAN_CARD_X + SCAN_CARD_W - 1, SCAN_CARD_IN_Y + k, 1, 2, 1);
    }
    draw_scan_card(scan_card_y);
    renderer_rectf(0, 0, 128, 14, 0);

    renderer_rectf(30, 14, 3, 86, 1);     /* left rail  */
    renderer_rectf(95, 14, 3, 86, 1);     /* right rail */
    renderer_rectf(26, 100, 76, 3, 1);    /* stop       */

    /* ── Status line ── */
    int seated  = (scan_pos != SCAN_POS_NONE && scan_pos >= 90);
    int partial = (scan_pos != SCAN_POS_NONE && scan_pos >= 8 && !seated);
    int known   = (scan_cur < 16 && (scan_mask & (1u << scan_cur)));
    char msg[24];
    if (!scan_ready) {
        snprintf(msg, sizeof msg, "CAMERA STARTING");
    } else if (scan_ok_hold > 0) {
        if (scan_total) snprintf(msg, sizeof msg, "CARD %d/%d OK", scan_ok_card, scan_total);
        else            snprintf(msg, sizeof msg, "CARD %d OK", scan_ok_card);
    } else if (known && scan_total) {
        snprintf(msg, sizeof msg, "CARD %d/%d OK", scan_cur + 1, scan_total);
    } else if (seated) {
        snprintf(msg, sizeof msg, "READING%.*s", (int)(scan_frame / 10 % 4), "...");
    } else if (partial) {
        snprintf(msg, sizeof msg, "PUSH CARD IN");
    } else if (scan_mask) {
        snprintf(msg, sizeof msg, "INSERT NEXT CARD");
    } else {
        snprintf(msg, sizeof msg, "INSERT CARD");
    }
    if (msg[0] == 'R') renderer_print(msg, 38, 3, 1);   /* fixed so dots don't jitter */
    else               scan_print_centred(msg, 3);

    /* ── Pip row: one per card (filled = read), or a loader while waiting ── */
    if (scan_total > 0) {
        int n  = scan_total > 15 ? 15 : scan_total;
        int x0 = (128 - (n * 8 - 4)) / 2;
        for (int i = 0; i < n; i++) {
            int x = x0 + i * 8;
            if (scan_mask & (1u << i)) {
                renderer_rectf(x, 119, 4, 4, 1);
            } else if (i == scan_cur) {
                renderer_rectf(x, 119, 4, 4, 1);
                renderer_rectf(x + 1, 120, 2, 2, 0);
            } else {
                renderer_rectf(x + 1, 120, 2, 2, 1);
            }
        }
    } else if (!scan_ready) {
        int lit = (int)(scan_frame / 6 % 5);
        for (int i = 0; i < 5; i++) {
            if (i == lit) renderer_rectf(46 + i * 8, 119, 4, 4, 1);
            else          renderer_rectf(47 + i * 8, 120, 2, 2, 1);
        }
    }

    /* Two-frame flash as a card is captured, like the boot wordmark */
    if (scan_ok_hold > 43) renderer_invert();
    if (scan_ok_hold > 0) scan_ok_hold--;
    scan_frame++;
}
#endif

/* ── Volume preference — persisted to ~/.glyphbox/volume ─────────────────── */
static void volume_pref_load(void) {
    const char *home = getenv("HOME");
    if (!home) return;
    char path[256];
    snprintf(path, sizeof(path), "%s/.glyphbox/volume", home);
    FILE *f = fopen(path, "r");
    if (!f) return;
    float v = 1.0f;
    fscanf(f, "%f", &v);
    fclose(f);
    audio_set_volume(v);
}

static void volume_pref_save(void) {
    const char *home = getenv("HOME");
    if (!home) return;
    char path[256];
    snprintf(path, sizeof(path), "%s/.glyphbox/volume", home);
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "%f\n", audio_get_volume());
    fclose(f);
}

/* ── One game-loop tick (extracted so Emscripten can use it as callback) ─── */
static uint32_t last_tick = 0;

static void game_loop_tick(void) {
    /* ── Events ── */
    SDL_Event e;
    int kbd_menu = 0;   /* set by ESC (desktop) or F2 (Pico BTN_B) */
    while (SDL_PollEvent(&e)) {
        if (e.type == SDL_QUIT) running = 0;
        if (e.type == SDL_CONTROLLERDEVICEADDED)
            input_controller_added(e.cdevice.which);
        if (e.type == SDL_CONTROLLERDEVICEREMOVED)
            input_controller_removed(e.cdevice.which);
        if (e.type == SDL_KEYDOWN) {
            if (e.key.keysym.sym == SDLK_ESCAPE || e.key.keysym.sym == SDLK_F2)
                kbd_menu = 1;
        }
    }

    /* ── Input ── */
    input_update();

    /* ── Triangle / BTN_B / keyboard: unified menu button ── */
    if (input_triangle_tapped() || kbd_menu) {
        if (g_state == STATE_STARTUP) {
            g_state = STATE_SPLASH;       /* skip boot animation */
        } else if (g_state == STATE_SCANNING) {
            abort_scan();
            g_state = STATE_SPLASH;       /* cancel scan immediately */
        } else if (g_state == STATE_CART_LOADED) {
            audio_music(-1);
            cart_free(g_cart); g_cart = NULL;
            lua_api_unload();
            g_state = STATE_SPLASH;       /* cancel before game starts */
        } else if (menu_active) {
            menu_active = 0;              /* close, resume */
        } else {
            menu_open();
        }
    }

    /* ── State machine ── */
    if (menu_active) {
#ifndef PLATFORM_WEB
        menu_debug_check();
#endif
        if (input_btnp(BTN_U))
            menu_cursor = (menu_cursor - 1 + menu_row_count) % menu_row_count;
        if (input_btnp(BTN_D))
            menu_cursor = (menu_cursor + 1) % menu_row_count;

        MenuAction sel = menu_rows[menu_cursor];
        if (sel == MENU_VOLUME) {
            float v = audio_get_volume();
            if (input_btnp(BTN_L)) { audio_set_volume(v - 0.1f); volume_pref_save(); }
            if (input_btnp(BTN_R)) { audio_set_volume(v + 0.1f); volume_pref_save(); }
        }
        if (input_btnp(BTN_A)) {
            if (sel == MENU_EXIT) {
                audio_music(-1);
                if (g_state == STATE_SCANNING) abort_scan();
                else { cart_free(g_cart); g_cart = NULL; lua_api_unload(); }
                g_state = STATE_SPLASH;
                menu_active = 0;
#ifdef PLATFORM_WEB
                EM_ASM( GlyphboxScanner.showScanButton(); );
#endif
            }
#ifndef PLATFORM_WEB
            else if (sel == MENU_SHUTDOWN) {
                renderer_cls(0);
                renderer_print("SHUTTING DOWN", 28, 60, 1);
                renderer_frame();
                SDL_RenderPresent(sdl_renderer);
                SDL_Delay(1500);
                system("sudo shutdown -h now");
                running = 0;
            }
            else if (sel == MENU_CONSOLE) {
                renderer_cls(0);
                renderer_print("EXITING", 44, 60, 1);
                renderer_frame();
                SDL_RenderPresent(sdl_renderer);
                SDL_Delay(500);
                running = 0;   /* clean exit: systemd Restart=on-failure won't relaunch */
            }
#endif
        }
        draw_menu();
    }
    else if (g_state == STATE_STARTUP) {
        if (startup_frame == 0) audio_startup_play();
        draw_startup(startup_frame);
        startup_frame++;
        /* Transition to splash once chime finishes (and we've played at least
           30 frames so the logo is fully visible before cutting away)        */
        if (!audio_startup_active() && startup_frame > 30) {
            splash_intro = 0;             /* slide the logo up into place */
            g_state = STATE_SPLASH;
        }
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
        scan_read_status();
        draw_scan();

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
        lua_api_call_update();
        lua_api_call_draw();
    }

    /* ── Audio tick ── */
    audio_frame_tick();

    /* ── Render ── */
    SDL_RenderClear(sdl_renderer);
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
    SDL_ShowCursor(SDL_DISABLE);

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

    runtime_init();
    renderer_init(sdl_renderer);
    audio_init();
    volume_pref_load();
    input_init();
    lua_api_init();
#ifndef PLATFORM_WEB
    lua_api_set_scan_fns(start_webcam_scan, poll_scan, scan_out);
#endif

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
