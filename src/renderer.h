#ifndef GLYPHBOX_RENDERER_H
#define GLYPHBOX_RENDERER_H

#include <stdint.h>
#include <SDL2/SDL.h>

void renderer_init(SDL_Renderer *r);
void renderer_frame(void);
void renderer_cls(int c);
void renderer_pset(int x, int y, int c);
int  renderer_pget(int x, int y);
void renderer_line(int x0, int y0, int x1, int y1, int c);
void renderer_rect(int x, int y, int w, int h, int c);
void renderer_rectf(int x, int y, int w, int h, int c);
void renderer_circ(int x, int y, int r, int c);
void renderer_circf(int x, int y, int r, int c);
void renderer_spr(int id, int x, int y, int fx, int fy);
void renderer_map(int cx, int cy, int x, int y, int w, int h);
void renderer_print(const char *str, int x, int y, int c);
void renderer_invert(void);
void renderer_set_sprites(const uint8_t *data);
void renderer_set_tilemap(const uint8_t *data);
void renderer_debug_ascii(void);

#endif /* GLYPHBOX_RENDERER_H */
