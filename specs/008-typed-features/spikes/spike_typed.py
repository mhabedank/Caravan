"""Spike for feature 008: per-column inputs, in-graph preprocessing, full int8 — on the synthetic
fixture with DERIVED (sorted) labels, the case that fails today (feature 006, R11)."""
import sys, json, collections
import numpy as np
sys.path.insert(0, "src")  # run from the repository root
import tensorflow as tf, keras
from caravan.data.windows import plan_windows, plan_split

SEED = 42
rows = [l.split(",") for l in open("tests/fixtures/datasets/synthetic/records.csv").read().splitlines()[1:]]
labels_raw = [r[0] for r in rows]
cols = {"can_id": np.array([int(r[1]) for r in rows], np.int32)}
for i, name in enumerate(["dlc", "b0", "b1", "b2"], start=2):
    cols[name] = np.array([float(r[i]) for r in rows], np.float32)
LABELS = sorted(set(labels_raw))          # derived: dos, fuzzy, normal, replay
W = 64
plan = plan_windows(labels_raw, W)
split = plan_split(plan, {"train": .7, "val": .15, "test": .15}, stratified=True, seed=SEED, labels=LABELS)
def windows(idx, name): return np.stack([cols[name][plan.kept[i]:plan.kept[i]+W] for i in idx])
y_all = np.array([LABELS.index(l) for l in plan.labels])
tr, va, te = list(split.train), list(split.val), list(split.test)

# fit preprocessing on the TRAIN part only
train_rows = np.concatenate([np.arange(plan.kept[i], plan.kept[i]+W) for i in tr])
stats = {n: (float(cols[n][train_rows].mean()), float(cols[n][train_rows].std() or 1.0)) for n in ["dlc","b0","b1","b2"]}
freq = collections.Counter(cols["can_id"][train_rows].tolist())
vocab = [v for v, _ in freq.most_common(32)]
print("vocab size", len(vocab), "stats", {k: (round(m,2), round(s,2)) for k,(m,s) in stats.items()})

@keras.saving.register_keras_serializable("spike")
class Standardize(keras.layers.Layer):
    def __init__(self, mean, std, **kw): super().__init__(**kw); self.mean, self.std = mean, std
    def call(self, x): return keras.ops.expand_dims((x - self.mean) / self.std, -1)
    def get_config(self): return {**super().get_config(), "mean": self.mean, "std": self.std}

@keras.saving.register_keras_serializable("spike")
class VocabOneHot(keras.layers.Layer):
    """index 0 = unknown; 1..V = vocabulary, by comparison (no hash table, no ONE_HOT)."""
    def __init__(self, vocab, **kw): super().__init__(**kw); self.vocab = list(vocab)
    def call(self, x):
        hits = keras.ops.cast(keras.ops.equal(keras.ops.expand_dims(x, -1), keras.ops.convert_to_tensor(np.array(self.vocab, np.int32))), "float32")
        unknown = 1.0 - keras.ops.sum(hits, axis=-1, keepdims=True)
        return keras.ops.concatenate([unknown, hits], axis=-1)
    def get_config(self): return {**super().get_config(), "vocab": self.vocab}

def build(batch=None):
    ins, parts = [], []
    i = keras.Input(batch_shape=(batch, W), dtype="int32", name="can_id"); ins.append(i); parts.append(VocabOneHot(vocab, name="can_id_onehot")(i))
    for n in ["dlc","b0","b1","b2"]:
        i = keras.Input(batch_shape=(batch, W), dtype="float32", name=n); ins.append(i); parts.append(Standardize(*stats[n], name=f"{n}_norm")(i))
    x = keras.layers.Concatenate(name="features")(parts)
    x = keras.layers.Flatten()(x)
    x = keras.layers.Dense(32, activation="relu")(x); x = keras.layers.Dropout(0.1)(x)
    x = keras.layers.Dense(16, activation="relu")(x); x = keras.layers.Dropout(0.1)(x)
    out = keras.layers.Dense(len(LABELS), activation="softmax", name="label")(x)
    return keras.Model(ins, {"label": out})

def feed(idx): return {n: windows(idx, n) for n in ["can_id","dlc","b0","b1","b2"]}
keras.utils.set_random_seed(SEED)
m = build()
m.compile(optimizer=keras.optimizers.Adam(1e-3), loss={"label": "sparse_categorical_crossentropy"}, metrics={"label": ["accuracy"]})
m.fit(feed(tr), {"label": y_all[tr]}, validation_data=(feed(va), {"label": y_all[va]}), epochs=50, batch_size=256, verbose=0,
      callbacks=[keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True, monitor="val_loss")])
trained = (np.argmax(m.predict(feed(te), verbose=0)["label"], -1) == y_all[te]).mean()

fixed = build(batch=1); fixed.set_weights(m.get_weights())
def rep():
    for i in tr: yield {n: windows([i], n) for n in ["can_id","dlc","b0","b1","b2"]}
conv = tf.lite.TFLiteConverter.from_keras_model(fixed)
conv.optimizations = [tf.lite.Optimize.DEFAULT]; conv.representative_dataset = rep
conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
conv.inference_output_type = tf.int8
blob = conv.convert()
open("typed.tflite","wb").write(blob)
from ai_edge_litert.interpreter import Interpreter
it = Interpreter(model_content=blob); it.allocate_tensors()
ops = sorted({d["op_name"] for d in it._get_ops_details()})
ins = {d["name"]: d for d in it.get_input_details()}
print("inputs:", [(d["name"], d["dtype"].__name__, d["quantization"]) for d in it.get_input_details()])
out = it.get_output_details()[0]
correct = 0
for i in te:
    for d in it.get_input_details():
        key = d["name"].split("serving_default_")[-1].split(":")[0]
        it.set_tensor(d["index"], windows([i], key).astype(d["dtype"]))
    it.invoke(); correct += int(np.argmax(it.get_tensor(out["index"])) == y_all[i])
quant = correct / len(te)
print(json.dumps({"labels": LABELS, "trained": round(float(trained),4), "quantized": round(quant,4), "test_windows": len(te), "bytes": len(blob), "ops": ops}))
