/* audio.c — 2-channel software synthesizer with SDL2 audio callback */
#include "audio.h"
#include <SDL2/SDL.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#define SAMPLE_RATE 44100
#define SCALE       28000

typedef struct {
    int    note;
    int    vol;
    int    wave;
    int    dur;
    int    attack;
    int    release;
    double phase;
    double phase_inc;
    int    env_frame;
    int    total_samples;   /* samples corresponding to dur frames */
    int    sample_pos;
} Channel;

typedef struct { uint8_t note, vol, wave, dur; } NoteEvent;
typedef struct { NoteEvent ch0[32]; NoteEvent ch1[32]; uint8_t len; } SfxPattern;
typedef struct { uint8_t sfx_ids[64]; uint8_t len; } MusicPattern;

static Channel       ch[2];
static SDL_AudioDeviceID audio_device_id;

/* ── System jingle ─────────────────────────────────────────────────────────── */
/* Plays on a dedicated third channel independent of the cart audio system.
   Triggered by main.c when a cartridge is successfully loaded.               */
typedef struct { float freq; int dur; int vol; } JNote;

/* FDS-inspired ascending fanfare: 3 quick rising notes, a held peak, then
   a gentle resolve.  Triangle wave approximates the FDS wavetable tone.     */
static const JNote JINGLE_SEQ[] = {
    { 523.25f,  5, 5 },    /* C5 — short  */
    { 659.25f,  5, 6 },    /* E5 — short  */
    { 783.99f,  5, 6 },    /* G5 — short  */
    { 1046.50f, 12, 7 },   /* C6 — held peak */
    { 0.0f,     3, 0 },    /* rest */
    { 783.99f,  8, 5 },    /* G5 — resolve / fade out */
};
#define JINGLE_LEN (int)(sizeof(JINGLE_SEQ) / sizeof(JINGLE_SEQ[0]))

static Channel jingle_ch;
static int     jingle_note_idx  = -1;  /* -1 = inactive */
static int     jingle_frame_ctr = 0;

static SfxPattern    sfx_patterns[16];
static MusicPattern  music_patterns[4];

static int  active_music = -1;
static int  music_sfx_pos = 0;
static int  music_sfx_frame = 0;

/* ── Callback ─────────────────────────────────────────────────────────────── */

static void audio_callback(void *userdata, uint8_t *stream, int len) {
    (void)userdata;
    int16_t *out = (int16_t *)stream;
    int samples = len / sizeof(int16_t);

    for (int s = 0; s < samples; s++) {
        double mix = 0.0;

        for (int i = 0; i < 2; i++) {
            if (ch[i].note == 0) continue;

            /* compute envelope amplitude */
            double amp = ch[i].vol / 7.0;
            int sp = ch[i].sample_pos;

            int attack_samples  = (int)(ch[i].attack  * (SAMPLE_RATE / 30.0));
            int release_samples = (int)(ch[i].release * (SAMPLE_RATE / 30.0));
            int dur_samples = ch[i].total_samples;

            if (dur_samples > 0) {
                if (sp >= dur_samples) {
                    ch[i].note = 0;
                    continue;
                }
                if (attack_samples > 0 && sp < attack_samples)
                    amp = (ch[i].vol / 7.0) * ((double)sp / attack_samples);
                else if (release_samples > 0 && sp >= dur_samples - release_samples) {
                    int into_release = sp - (dur_samples - release_samples);
                    amp = (ch[i].vol / 7.0) * (1.0 - (double)into_release / release_samples);
                }
            }

            /* generate waveform sample */
            double sample = 0.0;
            if (ch[i].wave == 2) {
                /* noise */
                sample = (rand() & 1) ? 1.0 : -1.0;
            } else if (ch[i].wave == 1) {
                /* triangle */
                sample = 1.0 - 4.0 * fabs(ch[i].phase - 0.5);
            } else {
                /* square */
                sample = (ch[i].phase < 0.5) ? 1.0 : -1.0;
            }

            mix += sample * amp;

            /* advance phase */
            if (ch[i].wave != 2) {
                ch[i].phase += ch[i].phase_inc;
                if (ch[i].phase >= 1.0) ch[i].phase -= 1.0;
            }
            ch[i].sample_pos++;
        }

        /* ── Jingle channel (system, independent of cart) ── */
        if (jingle_ch.note != 0) {
            double amp = jingle_ch.vol / 7.0;
            int sp  = jingle_ch.sample_pos;
            int atk = (int)(jingle_ch.attack  * (SAMPLE_RATE / 30.0));
            int rel = (int)(jingle_ch.release * (SAMPLE_RATE / 30.0));
            int dur = jingle_ch.total_samples;
            if (dur > 0 && sp >= dur) {
                jingle_ch.note = 0;
            } else {
                if (atk > 0 && sp < atk)
                    amp = (jingle_ch.vol / 7.0) * ((double)sp / atk);
                else if (rel > 0 && sp >= dur - rel)
                    amp = (jingle_ch.vol / 7.0) *
                          (1.0 - (double)(sp - (dur - rel)) / rel);
                double jsample = 1.0 - 4.0 * fabs(jingle_ch.phase - 0.5);
                mix += jsample * amp * 0.7;   /* slightly under cart level */
                jingle_ch.phase += jingle_ch.phase_inc;
                if (jingle_ch.phase >= 1.0) jingle_ch.phase -= 1.0;
                jingle_ch.sample_pos++;
            }
        }

        /* average mix of 2 cart channels + jingle, scale to int16 */
        int16_t val = (int16_t)(mix * 0.5 * SCALE);
        out[s] = val;
    }
}

/* ── Public API ───────────────────────────────────────────────────────────── */

/* Load note at JINGLE_SEQ[idx] into jingle_ch (call with audio device locked). */
static void _jingle_load(int idx) {
    const JNote *n = &JINGLE_SEQ[idx];
    SDL_LockAudioDevice(audio_device_id);
    memset(&jingle_ch, 0, sizeof(jingle_ch));
    if (n->freq > 0.0f) {
        jingle_ch.note          = 1;           /* non-zero = active */
        jingle_ch.vol           = n->vol;
        jingle_ch.wave          = 1;           /* triangle — FDS-like */
        jingle_ch.attack        = 1;           /* 1-frame ramp-in */
        jingle_ch.release       = 2;           /* 2-frame ramp-out */
        jingle_ch.phase_inc     = (double)n->freq / SAMPLE_RATE;
        jingle_ch.total_samples = (int)(n->dur * (SAMPLE_RATE / 30.0));
    }
    /* freq == 0 → rest; note stays 0 (silence) */
    SDL_UnlockAudioDevice(audio_device_id);
}

void audio_jingle_play(void) {
    jingle_note_idx  = 0;
    jingle_frame_ctr = 0;
    _jingle_load(0);
}

int audio_jingle_active(void) {
    return jingle_note_idx >= 0;
}

void audio_init(void) {
    memset(ch, 0, sizeof(ch));
    memset(&jingle_ch, 0, sizeof(jingle_ch));
    memset(sfx_patterns,   0, sizeof(sfx_patterns));
    memset(music_patterns, 0, sizeof(music_patterns));

    SDL_AudioSpec want = {
        .freq     = SAMPLE_RATE,
        .format   = AUDIO_S16SYS,
        .channels = 1,
        /* Pi/ALSA needs a larger buffer to avoid underruns when the CPU is
           busy with camera processing.  2048 samples ≈ 46 ms headroom,
           enough to survive a zxing decode pass without a dropout.
           Desktop stays at 512 samples (~11 ms) for low input-to-audio lag. */
#ifdef PLATFORM_PI_HDMI
        .samples  = 2048,
#else
        .samples  = 512,
#endif
        .callback = audio_callback,
        .userdata = NULL
    };
    SDL_AudioSpec got;
    audio_device_id = SDL_OpenAudioDevice(NULL, 0, &want, &got, 0);
    if (audio_device_id == 0) {
        fprintf(stderr, "GLYPHBOX: audio init failed: %s\n", SDL_GetError());
        return;
    }
    SDL_PauseAudioDevice(audio_device_id, 0);
}

void audio_shutdown(void) {
    if (audio_device_id) SDL_CloseAudioDevice(audio_device_id);
}

void audio_sfx(int c_idx, int note, int vol, int wave, int dur) {
    if (c_idx < 0 || c_idx > 1) return;
    SDL_LockAudioDevice(audio_device_id);
    ch[c_idx].note      = note;
    ch[c_idx].vol       = vol;
    ch[c_idx].wave      = wave;
    ch[c_idx].dur       = dur;
    ch[c_idx].attack    = 0;
    ch[c_idx].release   = 0;
    ch[c_idx].phase     = 0.0;
    ch[c_idx].sample_pos = 0;
    if (note > 0) {
        double freq = 440.0 * pow(2.0, (note - 69) / 12.0);
        ch[c_idx].phase_inc = freq / SAMPLE_RATE;
    }
    /* dur in frames; -1 = hold */
    ch[c_idx].total_samples = (dur < 0) ? -1 : (int)(dur * (SAMPLE_RATE / 30.0));
    SDL_UnlockAudioDevice(audio_device_id);
}

void audio_sfx_pat(int id) {
    if (id < 0 || id >= 16) return;
    SfxPattern *p = &sfx_patterns[id];
    for (int j = 0; j < p->len && j < 32; j++) {
        if (p->ch0[j].note)
            audio_sfx(0, p->ch0[j].note, p->ch0[j].vol, p->ch0[j].wave, p->ch0[j].dur);
        if (p->ch1[j].note)
            audio_sfx(1, p->ch1[j].note, p->ch1[j].vol, p->ch1[j].wave, p->ch1[j].dur);
    }
}

void audio_music(int id) {
    active_music  = id;
    music_sfx_pos = 0;
    music_sfx_frame = 0;
    if (id >= 0 && id < 4) {
        MusicPattern *m = &music_patterns[id];
        if (m->len > 0) audio_sfx_pat(m->sfx_ids[0]);
    }
}

void audio_frame_tick(void) {
    /* Advance jingle note sequencer (runs independently of cart music) */
    if (jingle_note_idx >= 0) {
        jingle_frame_ctr++;
        if (jingle_frame_ctr >= JINGLE_SEQ[jingle_note_idx].dur) {
            jingle_note_idx++;
            jingle_frame_ctr = 0;
            if (jingle_note_idx >= JINGLE_LEN) {
                /* Jingle complete */
                jingle_note_idx = -1;
                SDL_LockAudioDevice(audio_device_id);
                jingle_ch.note = 0;
                SDL_UnlockAudioDevice(audio_device_id);
            } else {
                _jingle_load(jingle_note_idx);
            }
        }
    }

    if (active_music < 0 || active_music >= 4) return;
    MusicPattern *m = &music_patterns[active_music];
    if (m->len == 0) return;

    music_sfx_frame++;
    if (music_sfx_frame >= 30) {   /* advance to next SFX every ~1 second */
        music_sfx_frame = 0;
        music_sfx_pos = (music_sfx_pos + 1) % m->len;
        audio_sfx_pat(m->sfx_ids[music_sfx_pos]);
    }
}

void audio_set_sfx_data(const uint8_t *data, size_t len) {
    if (!data || len == 0) return;
    /* 16 patterns × 32 notes × 2 channels × 4 bytes = 4096 max
       But our sfx_data field in cart is 512 bytes; use compact format:
       16 patterns × (1 byte len + 32×4 bytes ch0 + 32×4 bytes ch1) would exceed.
       Use: 16 patterns × 32 bytes = 512. Each 2 bytes = one note pair (note,vol,wave,dur packed).
       Simple format: byte[i*2+0] = note, byte[i*2+1] = (vol<<4)|(wave<<2)|(dur_hi) */
    /* Parse as 16 SFX, each occupying 32 bytes (16 note-events, 2 bytes each) */
    for (int p = 0; p < 16 && (size_t)(p * 32) < len; p++) {
        const uint8_t *base = data + p * 32;
        sfx_patterns[p].len = 0;
        for (int n = 0; n < 16 && (size_t)(p * 32 + n * 2 + 1) < len; n++) {
            uint8_t note = base[n * 2];
            uint8_t packed = base[n * 2 + 1];
            uint8_t vol  = (packed >> 4) & 0x7;
            uint8_t wave = (packed >> 2) & 0x3;
            uint8_t dur  = packed & 0x3;
            sfx_patterns[p].ch0[n] = (NoteEvent){ note, vol, wave, (uint8_t)(dur + 1) };
            if (note) sfx_patterns[p].len = (uint8_t)(n + 1);
        }
    }
}

void audio_set_music_data(const uint8_t *data, size_t len) {
    if (!data || len == 0) return;
    /* 4 patterns × 64 bytes each = 256 bytes.
       Each pattern: byte[0] = number of sfx entries, bytes[1..63] = sfx ids */
    for (int p = 0; p < 4 && (size_t)(p * 64) < len; p++) {
        const uint8_t *base = data + p * 64;
        music_patterns[p].len = (base[0] < 64) ? base[0] : 63;
        for (int i = 0; i < music_patterns[p].len; i++)
            music_patterns[p].sfx_ids[i] = base[1 + i];
    }
}
