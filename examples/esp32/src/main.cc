/* main.cc — a board run: the export's test windows through the model on a generic ESP32.
 *
 * For each window the board's answer, the host's and the expected one, on the serial port
 * (115200 baud), then a summary and a run record to paste into a board-run note.
 *
 * Model-agnostic: everything about the model comes from the export's files in src/model/ —
 * model_data.h (the array and its named positions), resolver.h (its operators) and
 * test_windows.h (the windows and the host's answers). To run your own model, export it with
 * export.test_windows above 0 and copy its four files; nothing here changes.
 *
 * Serial only, and no display: this is written for whatever ESP32 board you happen to have, and
 * the one thing every one of them has is a serial port.
 *
 * No timing is shown or printed: a latency figure belongs to a benchmark that follows a public
 * protocol, not to a demonstration.
 */
#include <cinttypes>
#include <cmath>
#include <cstdio>

#include "esp_idf_version.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "model_data.h"
#include "resolver.h"
#include "soc/rtc.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "test_windows.h"

#ifndef CARAVAN_FIRMWARE
#define CARAVAN_FIRMWARE "examples/esp32"
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

/* A failure is printed every five seconds, so a serial monitor opened late still sees it. */
[[noreturn]] void Halt(const char* message) {
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

  std::printf("caravan board run\n");
  std::printf("model: %s %s\n", kModelName, kModelVersion);
  std::printf("board: esp32 clock_mhz=%d\n", CpuMhz());

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
  std::printf("arena: used %u of %d bytes (measured, esp32)\n",
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
  }

  std::printf("summary: agreed %d/%d, max_diff_steps %ld\n", agreed, kCount, worst_steps);
  std::printf("--- board run record ---\n");
  std::printf("date: <fill in>\n");
  std::printf("board: esp32 (<fill in the board you used>)\n");
  std::printf("clock_mhz: %d\n", CpuMhz());
  std::printf("firmware: %s, model exported by %s\n", CARAVAN_FIRMWARE, kExportedBy);
  std::printf("toolchain: esp-idf %s, %s\n", esp_get_idf_version(), CARAVAN_TFLM_COMPONENT);
  std::printf("model: %s %s\n", kModelName, kModelVersion);
  std::printf("windows: %d\n", kCount);
  std::printf("agreed: %d\n", agreed);
  std::printf("max_score_diff_steps: %ld\n", worst_steps);
  std::printf("arena_used_bytes: %u (measured)\n", static_cast<unsigned>(arena_used));
  std::printf("--- end ---\n");

  for (;;) vTaskDelay(pdMS_TO_TICKS(60000));
}
