# Board runs

A board run is a model exported by Caravan, running on a physical microcontroller. The board
answers windows of the test part, and its answers are compared with the int8 model's answers on
the host ([the board guide](../guides/lora32.md)). Its record is the evidence behind every
`measured` entry on the [compatibility page](../compatibility.md).

**What a record holds:**
- the date;
- the board and its revision;
- the CPU clock;
- the firmware and the Caravan version that exported the model;
- the toolchain (ESP-IDF and the TensorFlow Lite Micro component);
- the model;
- how many windows agreed;
- the largest difference in quantization steps;
- the arena the runtime used, labeled `measured`.

It holds no timing: latency comes from a benchmark that follows a public protocol, which is
planned for a later version ([roadmap](../roadmap.md)).

## Records

None yet. The first is the owner's run of the LoRa32 guide.
