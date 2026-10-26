/* oled.h — eight lines of text on the LoRa32's SSD1306, through ESP-IDF's own driver.
 *
 * No graphics library: a 1,024-byte framebuffer, a 5x7 font, and esp_lcd's SSD1306 panel. If the
 * display does not answer (wrong revision chosen, no display), OledInit returns false and every
 * other call does nothing, so a board run carries on and reports on the serial port alone.
 */
#ifndef CARAVAN_OLED_H_
#define CARAVAN_OLED_H_

#include "board_pins.h"

constexpr int kOledColumns = 21;  /* 128 pixels / 6 per character */
constexpr int kOledRows = 8;      /* 64 pixels / 8 per page */

bool OledInit(const OledPins& pins);
void OledClear();
/* Writes text at a row, cut at kOledColumns characters. */
void OledLine(int row, const char* text);
/* Sends the framebuffer to the display. */
void OledShow();

#endif  /* CARAVAN_OLED_H_ */
