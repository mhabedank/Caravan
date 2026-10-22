<!--
Frozen record. Do not edit the document below this block.
-->

# Status of this record

This is the design document Caravan was started from, as it stood on **2026-10-22**, reproduced
verbatim. It is the document that `.specify/memory/constitution.md`,
`docs/research/2026-10-22-prior-art-learnings.md` and every artifact under
`specs/001-manifest-schema/` refer to as "the design document". It lived only in the conversation
that produced it until now, which left those references pointing at nothing — including a
reference from the constitution itself.

It is kept **frozen**, not maintained. A living copy would have to be re-reconciled after every
amendment and would duplicate the constitution and the feature specs, which is the drift the
project's own prior-art note warns about. Where this document and a current artifact disagree,
**the current artifact wins**, in this order: the constitution, then the feature's spec, plan and
contracts.

## What has been superseded since

Read the document with these in mind. Each is a deliberate decision recorded elsewhere, not an
oversight.

| In this document | Now | Recorded in |
|---|---|---|
| `split: [0.7, 0.15, 0.15]` as a list | named parts (`train`, `val`, `test`, `stratified`) | spec FR-018 |
| `formats: [tflite, model_cc]` | `formats: [flatbuffer, c_array]` — no vendor product names in durable identifiers | constitution amendment 8, research R8 |
| `verify: {emulator: renode}` as the default | default `none` | data model, research R13 |
| `renode: {platform: s32k144}` in the board example | no such Renode platform exists; `s32k144` and `esp32` carry `emulator: null` with evidence | research R13, `src/caravan/targets/boards/` |
| templates as an enum (`Template(str, Enum)`) | a registry; adding one edits no central list | constitution Principle VII, research R7 |
| one template object | two halves: a parameter spec in the core, a builder in the training extra | research R7 |
| the pydantic sketch in section 5.2 | the implemented schema under `src/caravan/manifest/schema/` | feature 001 |
| v0.1 as one step | cut into smaller features; 001 delivered the schema and the package skeleton | `specs/001-manifest-schema/` |
| distribution name open (`caravan-ml` vs `caravan-tinyml`) | `caravan-ml`; the bare name is held by an unrelated project | constitution 2.0.1 |
| `pydantic` for validation, implicitly with `pyyaml` | `ruamel.yaml`, because `pyyaml` publishes no wheel for the current stable Python | research R2 |
| Python CLI, framework unspecified | `argparse` from the standard library | research R1 |
| dataset declarations resolved by the framework (implied by zoo practice) | the author states what their data permits; the framework enforces the statement and marks the unstated as unverified | constitution 2.1.0 |

Open question 1 (distribution name) is resolved; 3, 4, 5 and 6 are answered by the constitution;
2 is answered by the publish gate; 7 and 8 are answered in the prior-art note, which found that
Renode models no S32K144.

---

# Caravan – Design-Dokument

**Zweck dieses Dokuments:** Vollständige, eigenständige Beschreibung des geplanten Frameworks „Caravan" – inklusive Kontext, Entscheidungen, Architektur und offener Fragen – zur Validierung durch eine externe KI-Review. Alle Informationen sind hier versammelt; es werden keine Gesprächsdetails vorausgesetzt.

---

## 1. Kontext

### 1.1 Das zugehörige Projekt: Mobility Model Zoo

„Caravan" entsteht als Werkzeug für Martins Open-Source-Projekt **Mobility Model Zoo** (https://mhabedank.github.io/mobility-model-zoo/). Der Zoo publiziert ML-Modelle für reale Mobility-Probleme in drei Themenfeldern:

- **Product Development** (z. B. JTBD-Extraktion aus Mobility-Texten)
- **Automotive Security** (kleine Modelle für CAN-Bus-Intrusion-Detection, GNSS-/V2X-Angriffserkennung, laufen auf Mikrocontrollern)
- **Condition Monitoring** (Bewegungserkennung, Maschinenüberwachung, Battery State-of-Health)

Prinzipien des Zoos: Compliance zuerst (Lizenzen, Privacy, EU AI Act – geprüft **vor** Publish), Model Cards mit bekannter Qualität und bekannten Grenzen, läuft auf eigener Hardware vom Laptop bis zur ECU. Veröffentlicht sind aktuell: pace-cnn (IMU-Aktivitätserkennung auf MCU), picket-forest (CAN-IDS auf MCU), scout-large (JTBD-Textmodell); 11 weitere geplant (u. a. picket-mlp, mode-cnn, hum-fan, hum-bearing, cell-soh, gnss-guard, v2x-guard, rough-road).

**Wichtig zur Struktur des Zoos:** Die drei Themenfelder sind **provisorisch und nicht final** – die Zahl wird deutlich wachsen, und welche Themenbereiche noch dazukommen, ist offen. Umgekehrt enthält der Zoo Modelle auf ganz unterschiedlichen Ebenen: reine Cloud-/Desktop-Modelle (z. B. JTBD-Textanalyse mit LLMs) einerseits und Embedded-/IoT-Modelle für limitierte Hardware andererseits.

**Scope von Caravan (bewusst eng gefasst):** Caravan ist **ausschließlich für die Embedded-/IoT-Modelle** da – also die Modelle, die auf Mikrocontrollern und limitierter Hardware laufen. Die Produktentwicklungs-/LLM-Modelle des Zoos (scout-large, cairn-base & Nachfolger) sind **explizit außerhalb des Rahmens** und werden separat, ohne Caravan, gebaut und veröffentlicht. Der Rahmen soll bewusst nicht zu breit gefasst werden; ein LLM-Pipeline-Baukasten ist ein anderes Projekt.

### 1.2 Problem, das Caravan löst

Ohne Standard-Pipeline bedeutet jedes neue Modell: Architektur von Hand bauen (klassisch in Jupyter-Notebooks), int8-Quantisierung, TFLite-Export, C-Array-Erzeugung, RAM/Flash prüfen, auf mehreren Boards testen, Model Card manuell pflegen. Das ist nicht reproduzierbar, nicht transparent und skaliert nicht auf 14+ Modelle.

Ziel: **Ein deklaratives Manifest pro Modell, eine standardisierte Pipeline erledigt den Rest.** Die Model Card entsteht aus echten Messwerten der Pipeline, nicht aus Handarbeit.

### 1.3 Hardware-Kontext

Vorhandene Boards: ESP32, D1 Mini. Geplante Zielmatrix:

| Board | Rolle | Anmerkung |
|---|---|---|
| NXP S32K144EVB | Automotive-MCU (ASIL-B, Cortex-M4F, CAN) | ~60–80 €, offizielles OSS SDK, Testobjekt für CAN-Modelle |
| STM32 Nucleo-H743 | Performance-Referenz (Cortex-M7) | ~25–35 € |
| ST Stellar EVB | echter Automotive-MCU mit Edge-AI-Story | ~100–200 € |
| Arduino Nano 33 BLE Sense | Sensorknoten mit IMU (LSM6DSO) | ~30 €, Standard-Plattform des TinyML-Buchs |
| ESP32 / D1 Mini | Consumer-/Nachrüst-Mobility | vorhanden, TFLM + ESP-NN |

HIL-Simulation: CAN über python-can/SocketCAN/cantools; Emulation bevorzugt über **Renode** (deklarative .repl/.resc-Plattformbeschreibungen, Robot-Framework-Tests, kann Sensordaten aus Aufzeichnungen einspeisen). QEMU nur eingeschränkt geeignet (Linux-Gäste, unvollständige MCU-Peripherie; ESP32/Xtensa schwach). Renode-Modelle existieren für STM32/nRF5/EFR32. Timing in Emulation ist nicht zyklen-genau: Emulation verifiziert „läuft/passt ins RAM/funktional korrekt", echte Latenz nur auf Hardware.

---

## 2. Positionierung & Abgrenzung (Prior Art)

Caravan = deklaratives, open-source TinyML-Pipeline-Framework **für Embedded-/IoT-Modelle auf Mikrocontrollern**: **YAML-Manifest → Training aus Architektur-Templates → int8-TFLite → C-Array → Analyse → ggf. Renode-Verifikation → Board-Benchmark → Model Card → Hugging-Face-Publish**.

Nicht-Ziel (zur Abgrenzung innerhalb des Zoos): LLM-/Text-/Produktentwicklungsmodelle (JTBD, Pain-and-Gains, cairn/scout-Serie). Diese laufen nicht über Caravan und haben eine eigene, simple Pipeline.

Abgrenzung:

| Projekt | Was es kann | Warum es nicht reicht |
|---|---|---|
| MCUNet/TinyNAS/TinyEngine (MIT Han Lab, OSS, Forschung) | Hardware-aware NAS, schnellerer Inference-Generator (1,7–3,3× vs. TFLM+CMSIS-NN) | Forschungscode, keine deklarative nutzerfreundliche Pipeline, Fokus Vision |
| Once-for-All (MIT Han Lab) | Supernetz → hardware-spezifische Subnetzze per Konfiguration | Forschungscode, kein Deployment-Tooling |
| Edge Impulse | Visuelle AutoML-Pipeline inkl. Board-Exporte | Kommerziell, closed, Vendor-Lock-in; Trainingspipeline liegt nicht im eigenen Repo |
| Ludwig (Uber/LF AI) | Deklaratives YAML-ML-Framework | PyTorch-basiert, kein Hardware-Budget-Bewusstsein, kein int8-TFLite-MCU-Export-Pfad; auf LLM-/Cloud-Modelle fokussiert, nicht auf MCU |
| TFLM + CMSIS-NN | Inference-Runtime auf MCU (C++), ARM-optimierte Kernel | Nur Runtime – kein Training/Export/Tracking/Model-Card-Standard |
| AutoFlow (kommerziell) | TinyML-Tool | Closed, Namenskonflikt |

**Lücke, die Caravan füllt:** deklarativ **und** hardware-constraint-aware **und** multi-board **und** open source – diese Kombination existiert Stand Oktober 2026 nicht. Caravan versucht explizit **nicht**, bessere NAS als MIT zu sein; der USP ist die benutzbare, reproduzierbare Pipeline.

Technische Basis-Entscheidungen: TFLM + CMSIS-NN als Inference-Standard (portierbar auf alle Zielboards), Keras/TF-Trainingsseite mit int8-Quantisierung, Python-CLI, keine Notebooks im Workflow, Pydantic für Manifest-Validierung, Optuna für spätere Hyperparameter-Suche.

---

## 3. Entscheidungen (Stand Oktober 2026)

| Entscheidung | Wert | Begründung |
|---|---|---|
| Name | **Caravan** | Mobility-Bezug; Modelle „ziehen" von Plattform zu Plattform (PC → Emulator → ESP32 → Automotive-MCU) |
| Lizenz | **Apache-2.0** | Framework + Modelle kommerziell nutzbar (Zoo-Ziel), OSS-Standard, Patent-Klausel |
| Framework vs. Zoo | getrennte Repos; Zoo referenziert Caravan | Zwei Communities statt einer; Modelle bleiben portierbar |
| Pilotmodell | **picket-mlp** | Klein, klar, ohnehin als nächste Version fällig; Framework wächst an echtem Bedarf |
| Distributionsname | offen: `caravan-ml` vs `caravan-tinyml` | `caravan` auf PyPI vermutlich vergeben; CLI bleibt `caravan` |
| Templates v0.1 | mlp, conv1d | Decken picket-mlp + mode-cnn/pace-artige Zeitserien ab |
| Emulation | Renode (ab v0.3), kein eigenes SoC-DSL | .repl/.resc sind bereits deklarativ; QEMU unzureichend für MCU-Peripherie |

Verworfene Namen (Kollisionen): Drivetrain („DrivetrainAI"-Org auf GitHub), Gait (stark durch Gait-Recognition-Forschung belegt, z. B. OpenGait – fachlich irreführend), Embark (Embark Trucks), Zookeeper (Apache ZooKeeper), AutoFlow (bestehendes TinyML-Tool).

---

## 4. Repo-Layout

```text
caravan/                         # eigenständiges Repo, Apache-2.0
├── pyproject.toml               # distribution: caravan-ml (t.b.d.), CLI: caravan
├── README.md
├── LICENSE                      # Apache-2.0
├── src/caravan/
│   ├── cli.py                   # caravan train / build / verify / bench / publish
│   ├── manifest.py              # YAML-Schema-Validierung (pydantic)
│   ├── templates/               # Architektur-Templates (Keras)
│   │   ├── conv1d.py            #   Zeitserien: IMU, CAN, Vibration
│   │   ├── smallcnn.py          #   2D-Inputs: Spektrogramme, kleine Bilder (ab v0.2)
│   │   ├── mlp.py               #   Feature-basierte Entscheider
│   │   └── forest.py            #   Baummodelle über ONNX (ab v0.2, für picket-forest)
│   ├── quantize.py              # int8-TFLite-Konvertierung + Accuracy-Gate
│   ├── analyze.py               # RAM/Flash/Latenz-Schätzung aus dem Flatbuffer
│   ├── targets/                 # Board-Datenbank (YAML)
│   │   ├── boards/
│   │   │   ├── s32k144.yaml
│   │   │   ├── stm32h743.yaml
│   │   │   ├── esp32.yaml
│   │   │   ├── d1mini.yaml
│   │   │   └── nano33ble.yaml
│   │   └── renode.py            # virtuelle Verifikation (Renode-Aufruf, ab v0.3)
│   ├── export/                  # model.cc-Generierung (xxd-Stil), TFLM-Stubs
│   ├── card.py                  # Model-Card-Renderer (aus echten Messwerten)
│   └── publish.py               # Hugging-Face-Upload
├── templates-c/                 # TFLM-Runner-Skeleton pro Board (CMake + CMSIS-NN)
└── tests/
```

---

## 5. Manifest-Schema

### 5.1 Beispiel (picket-mlp)

```yaml
apiVersion: caravan/v0
model:
  name: picket-mlp
  version: 0.1.0
  topic: automotive-security
  task: can-ids
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1
dataset:
  source: datasets/car-hacking/        # oder HF-Dataset-Referenz
  split: [0.7, 0.15, 0.15]
  window: 64
  labels: [normal, dos, fuzzy, replay]
train:
  epochs: 50
  batch: 256
  optimizer: adam
  early_stopping: true
export:
  quantization: int8
  formats: [tflite, model_cc]
  targets: [s32k144, stm32h743, esp32]   # refs auf targets/boards/*.yaml
  accuracy_drop_max: 0.02
verify:
  emulator: renode                      # ab v0.3
bench:
  metrics: [latency_p50, ram_peak, flash]
publish:
  hf_repo: mhabedank/picket-mlp
  license: apache-2.0
compliance:                             # Pflichtfeld; fließt in die Model Card
  eu_ai_act_class: limited-risk
  privacy: no-personal-data
  intended_use: "CAN-Bus-Intrusion Detection auf Gateway/Zonal-ECUs"
  known_limits:
    - "Trainiert auf HCRL-Car-Hacking-Datensatz; Verhalten bei Zero-Day-Angriffen ungetestet"
```

Schema-Regeln:
- Das Manifest beschreibt **Was**, nie **Wie im Code** – Architektur kommt aus dem Template.
- Fehlende Felder haben dokumentierte Defaults; ein minimales Manifest = model + dataset + export + compliance.
- **`compliance` ist Pflicht; `publish` ohne Compliance wird vom Schema abgelehnt.** So ist „Compliance comes first" des Zoos mechanisch durchgesetzt.
- Jede Stage ist cachebar (Hash aus Manifest + Dataset-Version) – Card-Änderungen triggern kein Retraining.

### 5.2 Pydantic-Schema (Code-Entwurf v0.1)

```python
"""caravan.manifest – Manifest-Schema v0.1 (apiVersion: caravan/v0)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class Template(str, Enum):
    """Verfügbare Architektur-Templates. v0.1: mlp + conv1d."""
    MLP = "mlp"
    CONV1D = "conv1d"
    # geplant, nicht in v0.1: smallcnn, forest


class Quantization(str, Enum):
    INT8 = "int8"
    FLOAT16 = "float16"      # nur für Boards ohne int8-Nutzen sinnvoll
    NONE = "none"


class EuAiActClass(str, Enum):
    """Vereinfachte EU-AI-Act-Risikoklassen für die Model Card."""
    MINIMAL = "minimal-risk"
    LIMITED = "limited-risk"
    HIGH = "high-risk"


class Split(BaseModel):
    train: float = 0.7
    val: float = 0.15
    test: float = 0.15
    stratified: bool = True

    @model_validator(mode="after")
    def sums_to_one(self) -> "Split":
        if abs(self.train + self.val + self.test - 1.0) > 1e-6:
            raise ValueError("Split-Verhältnisse müssen 1.0 ergeben")
        return self


class ModelSpec(BaseModel):
    name: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    topic: str
    task: str
    template: Template
    params: dict = Field(default_factory=dict)  # template-spezifisch, validiert im Template


class DatasetSpec(BaseModel):
    source: str                              # Pfad oder HF-Dataset-ID
    split: Split = Field(default_factory=Split)
    window: int | None = None                # Zeitserien; None für flache Features
    labels: list[str] = Field(min_length=2)
    representative_samples: int | None = None  # nötig für int8-Quantisierung


class TrainSpec(BaseModel):
    epochs: int = Field(default=50, gt=0)
    batch: int = Field(default=256, gt=0)
    optimizer: Literal["adam", "sgd", "adamw"] = "adam"
    learning_rate: float = 1e-3
    early_stopping: bool = True
    patience: int = 5
    seed: int = 42


class ExportSpec(BaseModel):
    quantization: Quantization = Quantization.INT8
    formats: list[Literal["tflite", "model_cc", "onnx"]] = ["tflite", "model_cc"]
    targets: list[str] = Field(min_length=1)
    accuracy_drop_max: float = Field(
        default=0.02,
        description="Max. erlaubter Accuracy-Verlust durch Quantisierung (Gate in Stage 3).",
    )

    @field_validator("targets")
    @classmethod
    def unique_targets(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("Doppelte Zielboards")
        return v


class VerifySpec(BaseModel):
    emulator: Literal["renode", "none"] = "renode"   # ab v0.3 aktiv


class BenchSpec(BaseModel):
    metrics: list[Literal["latency_p50", "latency_p99", "ram_peak", "flash"]] = [
        "latency_p50", "ram_peak", "flash",
    ]


class ComplianceSpec(BaseModel):
    eu_ai_act_class: EuAiActClass
    privacy: Literal["no-personal-data", "anonymized", "personal-data"]
    intended_use: str = Field(min_length=20)
    known_limits: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def personal_data_needs_review(self) -> "ComplianceSpec":
        if self.privacy == "personal-data" and self.eu_ai_act_class == EuAiActClass.MINIMAL:
            raise ValueError("Modelle mit personenbezogenen Daten sind nicht minimal-risk")
        return self


class PublishSpec(BaseModel):
    hf_repo: str
    license: Literal["apache-2.0", "mit", "cc-by-4.0"] = "apache-2.0"


class Manifest(BaseModel):
    """Wurzelobjekt: eine YAML-Datei, ein Modell."""
    apiVersion: Literal["caravan/v0"]
    model: ModelSpec
    dataset: DatasetSpec
    train: TrainSpec = Field(default_factory=TrainSpec)
    export: ExportSpec
    verify: VerifySpec = Field(default_factory=VerifySpec)
    bench: BenchSpec = Field(default_factory=BenchSpec)
    publish: PublishSpec | None = None
    compliance: ComplianceSpec

    @model_validator(mode="after")
    def publish_requires_compliance(self) -> "Manifest":
        if self.publish is not None and self.compliance is None:
            raise ValueError("Publish ohne Compliance-Angabe nicht erlaubt")
        return self


def load_manifest(path: Path) -> Manifest:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Manifest.model_validate(raw)
```

---

## 6. Pipeline-Stages

```text
manifest.yaml
   │ validate (pydantic)
   ▼
[1] build      → Keras/ONNX-Modell aus Template + Params
   ▼
[2] train      → Training, Checkpoints, Metriken (lokales Tracking)
   ▼
[3] quantize   → int8-TFLite (+ Accuracy-Delta-Gate: Abbruch wenn Drop > accuracy_drop_max)
   ▼
[4] analyze    → RAM/Flash-Schätzung, Latenz-Heuristik pro Zielboard
   │             → FAIL, wenn Board-Budget überschritten (Auto-Skalierung ab v0.2)
   ▼
[5] verify     → Renode: lädt model.cc, Inferenz-Tests gegen Testdaten (ab v0.3)
   ▼
[6] bench      → echte Hardware (Board-Matrix), optional/manuell; Results → report.json
   ▼
[7] card       → Model Card aus Manifest + echten Messwerten gerendert
   ▼
[8] publish    → Hugging-Face-Upload (tflite, model.cc, card, report.json)
```

CLI: `caravan run manifest.yaml --stages build,train,quantize,analyze`.

### Board-Datenbank (Beispiel `targets/boards/s32k144.yaml`)

```yaml
board: s32k144
family: nxp-s32k
core: cortex-m4f
clock_mhz: 80
ram_kb: 64            # + 4 KB FlexRAM
flash_kb: 512
accel: cmsis-nn
interfaces: [can-fd, i2c, spi, uart]
tflm: {kernel: cmsis_nn, opt: -O3}
renode: {platform: s32k144, status: experimental}
notes: "ASIL-B, Automotive-MCU; Eval-Board ~60–80 EUR"
```

Regel: Neue Boards = neue YAML-Datei, kein Framework-Code. Die Matrix wächst deklarativ. Geplant ist ein Requirement-Mapping: Modell-Analyse (Stage 4) erzeugt einen Hardware-Requirement-Spec („≥ 80 KB RAM, ≥ 300 KB Flash, FPU, int8"), der automatisch gegen die Board-Datenbank aufgelöst wird; Emulation (Renode) verifiziert vor Verfügbarkeit echter Hardware.

---

## 7. Roadmap

| Version | Inhalt | Nutzen für den Zoo |
|---|---|---|
| **v0.1** | Manifest-Schema, Templates (mlp, conv1d), Stages 1–3, model.cc-Export | picket-mlp & mode-cnn über die Pipeline statt Handbau |
| **v0.2** | Stage 4 (analyze), Board-Datenbank, Auto-Skalierung der Templates bei Budget-Überschreitung; Templates smallcnn/forest | RAM/Flash-Zahlen in jeder Model Card, aus Messung statt Handschätzung |
| **v0.3** | Stage 5 (Renode-Verifikation), Requirement-Mapping Modell→Board | Modelle ohne echte Hardware testbar – wichtig für Contributor ohne Board-Matrix |
| **v0.4** | Optuna-Suche über Template-Params mit Board-Budget als Nebenbedingung („NAS-light"; bewusst kein volles TinyNAS) | Automatisch bessere Architekturen pro Board |
| **v1.0** | Stages 6–8: Board-Benchmark-Runner + automatischer HF-Publish | Zoo-Ausstoß skaliert: neues Modell = ein Manifest + ein `caravan run` |

Bewusste Nicht-Ziele: kein eigener SoC-/QEMU-DSL-Designer, kein cycle-accurate Timing in der Emulation, kein Forschungs-NAS, kein Ersatz für TFLM, **kein Support für Cloud-/LLM-/Produktentwicklungsmodelle** (diese verlassen den Zoo über eine eigene Pipeline).

---

## 8. Erste Schritte

1. Framework-Repo anlegen, Apache-2.0, `pyproject.toml`, pydantic-Schema implementieren
2. **picket-mlp als Pilotmodell** – Framework an echtem Bedarf entwickeln
3. Templates nur so weit ausbauen, wie die ersten zwei Modelle sie brauchen (mlp + conv1d)
4. Renode und Benchmarks bewusst auf v0.2/v0.3 verschieben
5. Zoo-README: „Built with Caravan"-Abschnitt mit Versionspin
6. PyPI-Namen klären (`caravan-ml` vs `caravan-tinyml`), GitHub-Repo/Org sichern, grobe Marken-Recherche (DE/EU, da kommerzielle Nutzung erlaubt)

---

## 9. Offene Fragen (an die Validierung)

1. **PyPI-Distributionsname**: `caravan-ml` vs `caravan-tinyml` – Konventionen/Kollisionen?
2. **HF-Publish in CI**: Token-Handling ohne Leak, Release-Flow?
3. **Latenz-Heuristik in Stage 4**: Starten mit groben Cortex-M4-FLOPS-Schätzungen akzeptabel, solange echte Benchmarks (Stage 6) folgen? Wie kennzeichnen („estimated" vs. „measured") in der Model Card?
4. **Schema-Stabilität**: Ist `apiVersion: caravan/v0` + die Enum-/Literal-lastige Validierung zu rigid für v0.1, oder richtig?
5. **Compliance-Feld**: Ist die vereinfachte EU-AI-Act-Klassifizierung (minimal/limited/high) als Pflichtfeld praxistauglich, oder braucht es Freitext + Review-Flag?
6. **Templates als Enum vs. Plugin-System**: Ab wann wäre ein Registry-/Plugin-Ansatz für Community-Templates besser als das Enum?
7. **forest-Template** (picket-forest ist bereits ohne Caravan veröffentlicht): ONNX-basierter Baum-Export auf MCU – sinnvoller Weg oder separates Format?
8. **Renode-Verfügbarkeit**: Für wie viele der Zielboards (v. a. S32K144) existieren tatsächlich nutzbare Plattform-Beschreibungen? Fallback-Strategie, falls experimental?

*Stand: 22.10.2026*
