/* board_pins.h — the OLED wiring of the LILYGO LoRa32 revisions, in one place.
 *
 * The PlatformIO environment picks the block: `pio run -e lora32` (the default) or
 * `pio run -e lora32-v1`, which defines CARAVAN_LORA32_V1. docs/guides/lora32.md says how to tell
 * the revisions apart. Sources: LILYGO's schematics T3_V1.3, T3_V1.6.1 and the LilyGo-LoRa-Series
 * repository, read 2026-10-26 (feature 009, research R5).
 *
 * Every revision has an SSD1306 128x64 OLED on I2C at address 0x3C.
 */
#ifndef CARAVAN_BOARD_PINS_H_
#define CARAVAN_BOARD_PINS_H_

struct OledPins {
  int sda;
  int scl;
  int reset;   /* -1: no reset line, the OLED resets at power-on */
  int supply;  /* -1: always powered; otherwise a GPIO driven low to power it */
  int address;
};

#ifdef CARAVAN_LORA32_V1
/* V1.0, the oldest: ESP32 chip in the open, PRG and RST buttons, no SD slot.
 * The OLED needs its reset line pulsed. GPIO21 as the OLED supply comes from Meshtastic's pin map
 * (VEXT, active low); no LILYGO schematic of V1.0 confirms it, and driving it low is harmless if
 * it is unconnected. */
constexpr OledPins kOledPins = {4, 15, 16, 21, 0x3C};
constexpr const char* kRevision = "V1.0";
#else
/* V1.3, V1.6 / V2.0, V2.1 (T3 1.6 and 1.6.1), and T3 V3.0.
 * No reset line: the OLED resets at power-on. GPIO16 is deliberately not used: on the
 * ESP32-PICO-D4 of the 1.6.x revisions it is the flash chip select, although some third-party pin
 * maps call it the OLED reset. Driving it would stop the board. */
constexpr OledPins kOledPins = {21, 22, -1, -1, 0x3C};
constexpr const char* kRevision = "V1.3/V1.6/V2.x";
#endif

#endif  /* CARAVAN_BOARD_PINS_H_ */
