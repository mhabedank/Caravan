/* oled.cc — see oled.h. ESP-IDF 5.5: the i2c_master bus driver and esp_lcd's SSD1306 panel, with
 * the IO settings of ESP-IDF's own i2c_oled example (feature 009, research R5). */
#include "oled.h"

#include <cstdint>
#include <cstring>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_lcd_io_i2c.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_ssd1306.h"
#include "font5x7.h"

namespace {

constexpr int kWidth = 128;
constexpr int kHeight = 64;

esp_lcd_panel_handle_t g_panel = nullptr;
/* Page layout: byte [page * 128 + x] holds the 8 pixels of column x in rows 8*page .. 8*page+7,
 * bit 0 at the top — what the SSD1306 takes in horizontal addressing mode. */
uint8_t g_frame[kWidth * kHeight / 8];

}  // namespace

bool OledInit(const OledPins& pins) {
  if (pins.supply >= 0) {
    gpio_set_direction(static_cast<gpio_num_t>(pins.supply), GPIO_MODE_OUTPUT);
    gpio_set_level(static_cast<gpio_num_t>(pins.supply), 0);
  }

  i2c_master_bus_config_t bus_config = {};
  bus_config.i2c_port = I2C_NUM_0;
  bus_config.sda_io_num = static_cast<gpio_num_t>(pins.sda);
  bus_config.scl_io_num = static_cast<gpio_num_t>(pins.scl);
  bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
  bus_config.glitch_ignore_cnt = 7;
  bus_config.flags.enable_internal_pullup = true;
  i2c_master_bus_handle_t bus = nullptr;
  if (i2c_new_master_bus(&bus_config, &bus) != ESP_OK) return false;

  /* Is anything there? Without this, a dark display and a missing one look the same. */
  if (i2c_master_probe(bus, pins.address, 50) != ESP_OK) return false;

  esp_lcd_panel_io_i2c_config_t io_config = {};
  io_config.dev_addr = static_cast<uint32_t>(pins.address);
  io_config.control_phase_bytes = 1;
  io_config.dc_bit_offset = 6;
  io_config.lcd_cmd_bits = 8;
  io_config.lcd_param_bits = 8;
  io_config.scl_speed_hz = 400000;
  esp_lcd_panel_io_handle_t io = nullptr;
  if (esp_lcd_new_panel_io_i2c_v2(bus, &io_config, &io) != ESP_OK) return false;

  esp_lcd_panel_ssd1306_config_t ssd1306_config = {};
  ssd1306_config.height = kHeight;
  esp_lcd_panel_dev_config_t panel_config = {};
  panel_config.reset_gpio_num = static_cast<gpio_num_t>(pins.reset);
  panel_config.bits_per_pixel = 1;
  panel_config.vendor_config = &ssd1306_config;
  esp_lcd_panel_handle_t panel = nullptr;
  if (esp_lcd_new_panel_ssd1306(io, &panel_config, &panel) != ESP_OK) return false;
  if (esp_lcd_panel_reset(panel) != ESP_OK) return false;
  if (esp_lcd_panel_init(panel) != ESP_OK) return false;
  if (esp_lcd_panel_disp_on_off(panel, true) != ESP_OK) return false;

  g_panel = panel;
  OledClear();
  OledShow();
  return true;
}

void OledClear() { std::memset(g_frame, 0, sizeof(g_frame)); }

void OledLine(int row, const char* text) {
  if (g_panel == nullptr || row < 0 || row >= kOledRows || text == nullptr) return;
  uint8_t* page = g_frame + row * kWidth;
  std::memset(page, 0, kWidth);
  for (int column = 0; column < kOledColumns && text[column] != '\0'; ++column) {
    int code = static_cast<unsigned char>(text[column]);
    if (code < kFontFirst || code > kFontLast) code = '?';
    const uint8_t* glyph = kFont5x7[code - kFontFirst];
    std::memcpy(page + column * (kFontWidth + 1), glyph, kFontWidth);
  }
}

void OledShow() {
  if (g_panel == nullptr) return;
  esp_lcd_panel_draw_bitmap(g_panel, 0, 0, kWidth, kHeight, g_frame);
}
