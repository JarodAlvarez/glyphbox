#ifndef GLYPHBOX_AUDIO_H
#define GLYPHBOX_AUDIO_H

#include <stddef.h>
#include <stdint.h>

void audio_init(void);
void audio_shutdown(void);
void audio_sfx(int ch, int note, int vol, int wave, int dur);
void audio_sfx_pat(int id);
void audio_music(int id);
void audio_frame_tick(void);
void audio_set_sfx_data(const uint8_t *data, size_t len);
void audio_set_music_data(const uint8_t *data, size_t len);

/* System jingle — plays independently of cart audio channels.
   Call audio_jingle_play() when entering the cart-loaded splash screen.
   Poll audio_jingle_active() to know when the jingle has finished. */
void audio_jingle_play(void);
int  audio_jingle_active(void);

#endif /* GLYPHBOX_AUDIO_H */
