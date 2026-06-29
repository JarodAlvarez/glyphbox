#ifndef GLYPHBOX_INPUT_H
#define GLYPHBOX_INPUT_H

#define BTN_U     0
#define BTN_D     1
#define BTN_L     2
#define BTN_R     3
#define BTN_A     4
#define BTN_COUNT 5

void input_init(void);
void input_update(void);
void input_shutdown(void);
int  input_btn(int b);
int  input_btnp(int b);
int  input_btnr(int b);

/* 1 on the frame triangle is first pressed — opens/closes the menu. */
int  input_triangle_tapped(void);

/* Hotplug callbacks — call from main.c event loop.
   joystick_idx  : event.cdevice.which from SDL_CONTROLLERDEVICEADDED
   instance_id   : event.cdevice.which from SDL_CONTROLLERDEVICEREMOVED  */
void input_controller_added(int joystick_idx);
void input_controller_removed(int instance_id);

#endif /* GLYPHBOX_INPUT_H */
