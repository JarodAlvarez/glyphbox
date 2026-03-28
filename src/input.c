/* input.c — button state machine: keyboard + USB/2.4GHz gamepad (SDL2) */
#include "input.h"
#include <string.h>
#include <SDL2/SDL.h>

/* ── Constants ────────────────────────────────────────────────────────────── */

#define MAX_CONTROLLERS 4

/* Analog stick dead-zone.  SDL2 axis range is −32768…32767.
   8000 ≈ 24% — comfortable for a d-pad substitute without phantom inputs. */
#define AXIS_DEADZONE   8000

/* ── State ────────────────────────────────────────────────────────────────── */

static uint8_t cur[BTN_COUNT];
static uint8_t prev[BTN_COUNT];

typedef struct {
    SDL_GameController *gc;
    SDL_JoystickID      id;   /* instance ID, used to match removal events */
} ControllerSlot;

static ControllerSlot slots[MAX_CONTROLLERS];
static int            num_slots = 0;

/* ── Internal helpers ─────────────────────────────────────────────────────── */

static void open_controller(int joystick_idx) {
    if (num_slots >= MAX_CONTROLLERS) return;
    if (!SDL_IsGameController(joystick_idx)) return;

    SDL_GameController *gc = SDL_GameControllerOpen(joystick_idx);
    if (!gc) return;

    SDL_Joystick *joy = SDL_GameControllerGetJoystick(gc);
    slots[num_slots].gc = gc;
    slots[num_slots].id = SDL_JoystickInstanceID(joy);
    num_slots++;

    SDL_Log("GLYPHBOX: controller connected: %s",
            SDL_GameControllerName(gc));
}

static void close_controller(int instance_id) {
    for (int i = 0; i < num_slots; i++) {
        if (slots[i].id == instance_id) {
            SDL_Log("GLYPHBOX: controller disconnected: %s",
                    SDL_GameControllerName(slots[i].gc));
            SDL_GameControllerClose(slots[i].gc);
            /* Shift remaining slots down */
            slots[i] = slots[--num_slots];
            slots[num_slots].gc = NULL;
            slots[num_slots].id = 0;
            return;
        }
    }
}

/* ── Public API ───────────────────────────────────────────────────────────── */

void input_init(void) {
    memset(cur,   0, sizeof(cur));
    memset(prev,  0, sizeof(prev));
    memset(slots, 0, sizeof(slots));
    num_slots = 0;

    /* Open any controllers already connected at startup */
    int n = SDL_NumJoysticks();
    for (int i = 0; i < n; i++)
        open_controller(i);
}

void input_update(void) {
    memcpy(prev, cur, BTN_COUNT);

    /* ── Keyboard ──────────────────────────────────────────────────────── */
    const uint8_t *ks = SDL_GetKeyboardState(NULL);
    cur[BTN_U] = ks[SDL_SCANCODE_UP]    || ks[SDL_SCANCODE_W];
    cur[BTN_D] = ks[SDL_SCANCODE_DOWN]  || ks[SDL_SCANCODE_S];
    cur[BTN_L] = ks[SDL_SCANCODE_LEFT]  || ks[SDL_SCANCODE_A];
    cur[BTN_R] = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_D];
    cur[BTN_A] = ks[SDL_SCANCODE_Z]     || ks[SDL_SCANCODE_SPACE];

    /* ── Gamepad(s) — OR with keyboard so either device works ──────────── */
    for (int i = 0; i < num_slots; i++) {
        SDL_GameController *gc = slots[i].gc;
        if (!gc) continue;

        /* D-pad */
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_DPAD_UP))
            cur[BTN_U] = 1;
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_DPAD_DOWN))
            cur[BTN_D] = 1;
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_DPAD_LEFT))
            cur[BTN_L] = 1;
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_DPAD_RIGHT))
            cur[BTN_R] = 1;

        /* Face buttons → BTN_A.  Map both A and B so either confirms.     */
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_A) ||
            SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_B))
            cur[BTN_A] = 1;

        /* Left analog stick with dead-zone (supplement to d-pad) */
        Sint16 ax = SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_LEFTX);
        Sint16 ay = SDL_GameControllerGetAxis(gc, SDL_CONTROLLER_AXIS_LEFTY);
        if (ax < -AXIS_DEADZONE) cur[BTN_L] = 1;
        if (ax >  AXIS_DEADZONE) cur[BTN_R] = 1;
        if (ay < -AXIS_DEADZONE) cur[BTN_U] = 1;
        if (ay >  AXIS_DEADZONE) cur[BTN_D] = 1;
    }
}

void input_shutdown(void) {
    for (int i = 0; i < num_slots; i++) {
        if (slots[i].gc) {
            SDL_GameControllerClose(slots[i].gc);
            slots[i].gc = NULL;
            slots[i].id = 0;
        }
    }
    num_slots = 0;
    memset(cur,  0, sizeof(cur));
    memset(prev, 0, sizeof(prev));
}

/* Hotplug — called from the main.c event loop */
void input_controller_added(int joystick_idx) {
    open_controller(joystick_idx);
}

void input_controller_removed(int instance_id) {
    close_controller(instance_id);
}

int input_btn(int b)  { return cur[b]; }
int input_btnp(int b) { return  cur[b] && !prev[b]; }
int input_btnr(int b) { return !cur[b] &&  prev[b]; }

/* ── Start + Select eject combo ───────────────────────────────────────────
   Hold both buttons for RESET_HOLD_FRAMES consecutive frames (1 second at
   30 fps) to eject the current cart and return to the splash screen.
   Returns 1 exactly once when the threshold is crossed, 0 otherwise.      */
#define RESET_HOLD_FRAMES 30

static int reset_combo_held = 0;

int input_reset_combo(void) {
    int held = 0;
    for (int i = 0; i < num_slots; i++) {
        SDL_GameController *gc = slots[i].gc;
        if (!gc) continue;
        if (SDL_GameControllerGetButton(gc, SDL_CONTROLLER_BUTTON_START))
            { held = 1; break; }
    }
    if (held) {
        reset_combo_held++;
        if (reset_combo_held == RESET_HOLD_FRAMES) {
            reset_combo_held = 0;
            return 1;
        }
    } else {
        reset_combo_held = 0;
    }
    return 0;
}
