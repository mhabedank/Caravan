/* main.cc — a board run: the export's test windows through the model on a LILYGO LoRa32.
 *
 * For each window the board's answer, the host's and the expected one, on the OLED and on the
 * serial port (115200 baud), then a summary and a run record to paste into
 * docs/board-runs/<date>-lora32.md. The output format is contracts/board-output.md of feature 009.
 *
 * Model-agnostic: everything about the model comes from the export's files in src/model/ —
 * model_data.h (the array and its named positions), resolver.h (its operators) and
 * test_windows.h (the windows and the host's answers). To run your own model, export it with
 * export.test_windows above 0 and copy its four files; nothing here changes.
 *
 * No timing is shown or printed: a latency figure belongs to a benchmark that follows a public
 * protocol, not to a demonstration (feature 009, FR-006).
 */
#include <cinttypes>
#include <cmath>
#include <cstdio>

#include "board_pins.h"
#include "esp_idf_version.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "model_data.h"
#include "oled.h"
#include "resolver.h"
#include "soc/rtc.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "test_windows.h"

#ifndef CARAVAN_FIRMWARE
#define CARAVAN_FIRMWARE "examples/lora32"
#endif
#ifndef CARAVAN_TFLM_COMPONENT
#define CARAVAN_TFLM_COMPONENT "esp-tflite-micro (version in src/idf_component.yml)"
#endif

using namespace caravan_windows;

namespace {

/* Working memory for the interpreter. The export's floor for the example is about 10 KB; this is
 * a starting value with room to spare. The board reports what the runtime actually used
 * ("arena: used ... measured"): set this from that figure with a margin if you need the RAM. */
constexpr int kArenaBytes = 48 * 1024;
alignas(16) uint8_t g_arena[kArenaBytes];

constexpr int kHoldMs = 1500;

/* A failure is printed every five seconds, so a serial monitor opened late still sees it. */
[[noreturn]] void Halt(const char* message) {
  OledClear();
  OledLine(0, "ERROR");
  OledLine(1, message);
  OledLine(7, "details: serial");
  OledShow();
  for (;;) {
    std::printf("%s\n", message);
    vTaskDelay(pdMS_TO_TICKS(5000));
  }
}

int CpuMhz() {
  rtc_cpu_freq_config_t config;
  rtc_clk_cpu_freq_get_config(&config);
  return static_cast<int>(config.freq_mhz);
}

bool Agrees(float board, float host) {
  if (kOutputType == kNumber) return std::fabs(board - host) <= kScoreStep;
  return board == host;
}

}  // namespace

extern "C" void app_main(void) {
  char line[96];
  const bool oled = OledInit(kOledPins);

  std::printf("caravan board run\n");
  std::printf("model: %s %s\n", kModelName, kModelVersion);
  std::printf("board: lora32 rev=%s clock_mhz=%d\n", kRevision, CpuMhz());
  if (!oled) std::printf("oled: not found on SDA %d / SCL %d; serial only\n", kOledPins.sda,
                         kOledPins.scl);

  const tflite::Model* model = tflite::GetModel(g_model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Halt("error: model schema version differs from the runtime's; re-export the model");
  }
  static auto resolver = CaravanResolver();
  static tflite::MicroInterpreter interpreter(model, resolver, g_arena, kArenaBytes);
  if (interpreter.AllocateTensors() != kTfLiteOk) {
    std::snprintf(line, sizeof(line),
                  "error: arena too small (kArenaBytes=%d); raise kArenaBytes in src/main.cc",
                  kArenaBytes);
    Halt(line);
  }
  const size_t arena_used = interpreter.arena_used_bytes();
  std::printf("arena: used %u of %d bytes (measured, lora32)\n",
              static_cast<unsigned>(arena_used), kArenaBytes);

  TfLiteTensor* output = interpreter.output(kOutputPosition);
  if (output == nullptr || output->type != kTfLiteFloat32 ||
      output->bytes != sizeof(float) * kOutputCount) {
    Halt("error: output does not match test_windows.h; re-export and copy model/ again");
  }

  int agreed = 0;
  long worst_steps = 0;
  for (int i = 0; i < kCount; ++i) {
    const char* failed = nullptr;
    if (!FillWindow(interpreter, i, &failed)) {
      std::snprintf(line, sizeof(line),
                    "error: input %s does not match test_windows.h (type or size); re-export and "
                    "copy model/ again",
                    failed != nullptr ? failed : "?");
      Halt(line);
    }
    if (interpreter.Invoke() != kTfLiteOk) {
      std::snprintf(line, sizeof(line), "error: inference failed on window %d", i + 1);
      Halt(line);
    }

    const float* scores = output->data.f;
    long steps = 0;
    for (int k = 0; k < kOutputCount; ++k) {
      const long diff = std::lround(std::fabs(scores[k] - kHostScores[i][k]) / kScoreStep);
      if (diff > steps) steps = diff;
    }
    if (steps > worst_steps) worst_steps = steps;
    const float decision = Decide(scores);
    const bool agree = Agrees(decision, kHostDecision[i]);
    if (agree) ++agreed;

    char board_name[24];
    char host_name[24];
    char expected_name[24];
    DecisionName(decision, board_name);
    DecisionName(kHostDecision[i], host_name);
    DecisionName(kExpected[i], expected_name);
    std::printf("window %d/%d: board=%s host=%s expected=%s %s max_diff_steps=%ld%s\n", i + 1,
                kCount, board_name, host_name, expected_name, agree ? "agree" : "DISAGREE",
                steps, steps > 1 ? " over_one_step" : "");

    OledClear();
    std::snprintf(line, sizeof(line), "%s %s", kModelName, kModelVersion);
    OledLine(0, line);
    std::snprintf(line, sizeof(line), "window %2d/%d", i + 1, kCount);
    OledLine(1, line);
    std::snprintf(line, sizeof(line), "board : %s", board_name);
    OledLine(2, line);
    std::snprintf(line, sizeof(line), "host  : %s", host_name);
    OledLine(3, line);
    std::snprintf(line, sizeof(line), "expect: %s", expected_name);
    OledLine(4, line);
    std::snprintf(line, sizeof(line), "%s  diff %ld step%s", agree ? "AGREE" : "DISAGREE", steps,
                  steps == 1 ? "" : "s");
    OledLine(5, line);
    std::snprintf(line, sizeof(line), "arena %u B meas.", static_cast<unsigned>(arena_used));
    OledLine(6, line);
    std::snprintf(line, sizeof(line), "agreed so far %d/%d", agreed, i + 1);
    OledLine(7, line);
    OledShow();
    vTaskDelay(pdMS_TO_TICKS(kHoldMs));
  }

  std::printf("summary: agreed %d/%d, max_diff_steps %ld\n", agreed, kCount, worst_steps);
  std::printf("--- board run record ---\n");
  std::printf("date: <fill in>\n");
  std::printf("board: lora32\n");
  std::printf("revision: %s (check the label printed on your board)\n", kRevision);
  std::printf("clock_mhz: %d\n", CpuMhz());
  std::printf("firmware: %s, model exported by %s\n", CARAVAN_FIRMWARE, kExportedBy);
  std::printf("toolchain: esp-idf %s, %s\n", esp_get_idf_version(), CARAVAN_TFLM_COMPONENT);
  std::printf("model: %s %s\n", kModelName, kModelVersion);
  std::printf("windows: %d\n", kCount);
  std::printf("agreed: %d\n", agreed);
  std::printf("max_score_diff_steps: %ld\n", worst_steps);
  std::printf("arena_used_bytes: %u (measured)\n", static_cast<unsigned>(arena_used));
  std::printf("--- end ---\n");

  OledClear();
  std::snprintf(line, sizeof(line), "%s %s", kModelName, kModelVersion);
  OledLine(0, line);
  std::snprintf(line, sizeof(line), "DONE %d windows", kCount);
  OledLine(1, line);
  std::snprintf(line, sizeof(line), "agreed %d/%d", agreed, kCount);
  OledLine(2, line);
  std::snprintf(line, sizeof(line), "max diff %ld step%s", worst_steps, worst_steps == 1 ? "" : "s");
  OledLine(3, line);
  std::snprintf(line, sizeof(line), "arena %u B meas.", static_cast<unsigned>(arena_used));
  OledLine(4, line);
  OledLine(6, "details: serial");
  OledLine(7, "115200 baud");
  OledShow();

  for (;;) vTaskDelay(pdMS_TO_TICKS(60000));
}
