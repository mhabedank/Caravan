"""Probe: what does the TFLite converter do with preprocessing layers inside a Keras model?

Throwaway conversion probes only: every model is untrained / randomly initialised, every input is
synthetic random data. Nothing here is trained or meant for use.

Rerun:
    /home/user/Caravan/.venv/bin/python probe_preprocessing_conversion.py [experiment-substring ...]

Writes <name>__<mode>.tflite and results.json next to this script, and prints a summary.

Modes per model:
  a  = like Caravan: Optimize.DEFAULT + representative + TFLITE_BUILTINS_INT8, in/out type int8
  b  = same, but inference_input_type left unset (float32 / int32 input kept), output int8
  c  = only if a and b both failed: plain float conversion (no quantization) with
       supported_ops [TFLITE_BUILTINS] -- does a non-int8 builtin exist for the op?
  cf = only if a and b both failed: float conversion with [TFLITE_BUILTINS, SELECT_TF_OPS]
       (shows the TF op that is missing; quantized calibration cannot run Flex ops at all)

Each experiment runs in its own subprocess (one of them segfaults the converter).
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import keras  # noqa: E402
import numpy as np  # noqa: E402
import tensorflow as tf  # noqa: E402
from ai_edge_litert.interpreter import Interpreter  # noqa: E402

sys.path.insert(0, "/home/user/Caravan/src")
from caravan.convert.batch import fix_batch  # noqa: E402  (read-only use of Caravan)

HERE = Path(__file__).resolve().parent
RNG = np.random.default_rng(0)
keras.utils.set_random_seed(0)

TFLM_OPS = {  # from tflite-micro main micro_mutable_op_resolver.h (Add<Op> methods), upper-snake
    "ABS", "ADD", "ADD_N", "ARG_MAX", "ARG_MIN", "ASSIGN_VARIABLE", "AVERAGE_POOL_2D",
    "BATCH_MATMUL", "BATCH_TO_SPACE_ND", "BROADCAST_ARGS", "BROADCAST_TO", "CALL_ONCE", "CAST",
    "CEIL", "CONCATENATION", "CONV_2D", "COS", "CUMSUM", "DEPTH_TO_SPACE", "DEPTHWISE_CONV_2D",
    "DEQUANTIZE", "DIV", "DYNAMIC_UPDATE_SLICE", "EMBEDDING_LOOKUP", "ELU", "EQUAL", "EXP",
    "EXPAND_DIMS", "FILL", "FLOOR", "FLOOR_DIV", "FLOOR_MOD", "FULLY_CONNECTED", "GATHER",
    "GATHER_ND", "GREATER", "GREATER_EQUAL", "HARD_SWISH", "IF", "L2_NORMALIZATION", "L2_POOL_2D",
    "LEAKY_RELU", "LESS", "LESS_EQUAL", "LOG", "LOGICAL_AND", "LOGICAL_NOT", "LOGICAL_OR",
    "LOGISTIC", "LOG_SOFTMAX", "MAXIMUM", "MAX_POOL_2D", "MIRROR_PAD", "MEAN", "MINIMUM", "MUL",
    "NEG", "NOT_EQUAL", "PACK", "PAD", "PADV2", "PRELU", "QUANTIZE", "READ_VARIABLE",
    "REDUCE_ALL", "REDUCE_MAX", "REDUCE_MIN", "RELU", "RELU6", "RESHAPE", "RESIZE_BILINEAR",
    "RESIZE_NEAREST_NEIGHBOR", "REVERSE_V2", "RFFT", "ROUND", "RSQRT", "SELECT_V2", "SHAPE",
    "SIN", "SLICE", "SOFTMAX", "SPACE_TO_BATCH_ND", "SPACE_TO_DEPTH", "SPLIT", "SPLIT_V",
    "SQUEEZE", "SQRT", "SQUARE", "SQUARED_DIFFERENCE", "STRIDED_SLICE", "SUB", "SUM", "SVDF",
    "TANH", "TRANSPOSE_CONV", "TRANSPOSE", "UNPACK", "UNIDIRECTIONAL_SEQUENCE_LSTM", "VAR_HANDLE",
    "WHILE", "ZEROS_LIKE",
}

# ---------------------------------------------------------------- synthetic data helpers
CAN_VOCAB = [0x260, 0x316, 0x43F, 0x4B1, 0x18F]
NUM_MEAN = np.array([1000.0, 5.0, 0.1, 300.0, 50.0], np.float32)  # deliberately mixed scales
NUM_STD = np.array([400.0, 2.0, 0.05, 100.0, 20.0], np.float32)


SAME_MEAN = np.full(5, 50.0, np.float32)   # control: every feature on the same scale
SAME_STD = np.full(5, 20.0, np.float32)


def raw_numeric(n, shape, same=False):
    """Raw float features; by default with very different scales per column (last axis)."""
    k = shape[-1]
    mean, std = (SAME_MEAN, SAME_STD) if same else (NUM_MEAN, NUM_STD)
    return (RNG.normal(size=(n, *shape)) * std[:k] + mean[:k]).astype(np.float32)


def raw_can_ids(n, shape, oov_rate=0.15, dtype=np.int32):
    ids = RNG.choice(CAN_VOCAB, size=(n, *shape))
    oov = RNG.random(size=(n, *shape)) < oov_rate
    ids = np.where(oov, RNG.integers(0, 0x7FF, size=(n, *shape)), ids)
    return ids.astype(dtype)


class CompareOneHot(keras.layers.Layer):
    """Hash-table-free lookup: one-hot by comparison against a constant vocabulary, + OOV slot."""

    def __init__(self, vocab, cast_input_to=None, **kw):
        super().__init__(**kw)
        self.vocab = list(vocab)
        self.cast_input_to = cast_input_to

    def call(self, x):
        if self.cast_input_to:
            x = keras.ops.cast(x, self.cast_input_to)
        v = keras.ops.convert_to_tensor(np.array(self.vocab), dtype=x.dtype)
        hit = keras.ops.cast(keras.ops.equal(keras.ops.expand_dims(x, -1), v), "float32")
        oov = 1.0 - keras.ops.sum(hit, axis=-1, keepdims=True)
        return keras.ops.concatenate([oov, hit], axis=-1)

    def get_config(self):
        return {**super().get_config(), "vocab": self.vocab, "cast_input_to": self.cast_input_to}


class Standardize(keras.layers.Layer):
    """Hand-written (x - mean) / std with constants (no adapt state)."""

    def __init__(self, mean, std, **kw):
        super().__init__(**kw)
        self.mean, self.std = list(map(float, mean)), list(map(float, std))

    def call(self, x):
        return (x - np.array(self.mean, np.float32)) / np.array(self.std, np.float32)

    def get_config(self):
        return {**super().get_config(), "mean": self.mean, "std": self.std}


# ---------------------------------------------------------------- experiment builders
BATCH = [1]  # probes are built with batch fixed to 1 directly; fix_batch is checked separately


def Inp(shape, **kw):
    return keras.Input(batch_shape=(BATCH[0], *shape), **kw)


# Each returns (model, [sample_fn per input]) ; sample_fn(n) -> np array batch.
# single-input models are built with batch None and go through Caravan's fix_batch.

def e1_normalization_layer():
    inp = Inp((5,), name="x")
    norm = keras.layers.Normalization(axis=-1)
    norm.adapt(raw_numeric(512, (5,)))
    h = keras.layers.Dense(8, activation="relu")(norm(inp))
    return keras.Model(inp, keras.layers.Dense(3)(h)), [lambda n: raw_numeric(n, (5,))]


def e1_lambda_standardize():
    inp = Inp((5,), name="x")
    z = keras.layers.Lambda(lambda x: (x - NUM_MEAN) / NUM_STD)(inp)
    h = keras.layers.Dense(8, activation="relu")(z)
    return keras.Model(inp, keras.layers.Dense(3)(h)), [lambda n: raw_numeric(n, (5,))]


def e1_custom_standardize():
    inp = Inp((5,), name="x")
    z = Standardize(NUM_MEAN, NUM_STD)(inp)
    h = keras.layers.Dense(8, activation="relu")(z)
    return keras.Model(inp, keras.layers.Dense(3)(h)), [lambda n: raw_numeric(n, (5,))]


def e1_rescaling():
    inp = Inp((5,), name="x")
    z = keras.layers.Rescaling(scale=1.0 / NUM_STD, offset=-NUM_MEAN / NUM_STD)(inp)
    h = keras.layers.Dense(8, activation="relu")(z)
    return keras.Model(inp, keras.layers.Dense(3)(h)), [lambda n: raw_numeric(n, (5,))]


def e1_normalization_only():
    """Output IS the normalised vector: measures per-feature precision of in-model normalisation."""
    inp = Inp((5,), name="x")
    norm = keras.layers.Normalization(axis=-1)
    norm.adapt(raw_numeric(512, (5,)))
    return keras.Model(inp, norm(inp)), [lambda n: raw_numeric(n, (5,))]


def e1_normalization_only_same_scale():
    """Control for e1_normalization_only: all five raw features share one scale."""
    inp = Inp((5,), name="x")
    norm = keras.layers.Normalization(axis=-1)
    norm.adapt(raw_numeric(512, (5,), same=True))
    return keras.Model(inp, norm(inp)), [lambda n: raw_numeric(n, (5,), same=True)]


def e1_split_inputs_normalization_only():
    """Mixed scales, but one input tensor per feature -> one quantization scale per feature."""
    ins = [keras.Input(batch_shape=(1, 1), name=f"f{i}") for i in range(5)]
    outs = []
    for i, x in enumerate(ins):
        norm = keras.layers.Normalization(mean=float(NUM_MEAN[i]), variance=float(NUM_STD[i]) ** 2)
        outs.append(norm(x))
    samplers = [(lambda i: (lambda n: raw_numeric(n, (5,))[:, i:i + 1]))(i) for i in range(5)]
    return keras.Model(ins, keras.layers.Concatenate()(outs)), samplers


def e2_integer_lookup():
    inp = Inp((8,), dtype="int32", name="ids")
    idx = keras.layers.IntegerLookup(vocabulary=CAN_VOCAB, num_oov_indices=1)(inp)
    e = keras.layers.Embedding(len(CAN_VOCAB) + 1, 4)(idx)
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [lambda n: raw_can_ids(n, (8,))]


def e2_string_lookup():
    inp = Inp((8,), dtype="string", name="ids")
    vocab = [hex(v) for v in CAN_VOCAB]
    idx = keras.layers.StringLookup(vocabulary=vocab, num_oov_indices=1)(inp)
    e = keras.layers.Embedding(len(vocab) + 1, 4)(idx)
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [
        lambda n: np.vectorize(hex)(raw_can_ids(n, (8,))).astype(object)]


def e2_compare_onehot_int32():
    inp = Inp((8,), dtype="int32", name="ids")
    oh = CompareOneHot(CAN_VOCAB)(inp)                       # (8, 6)
    e = keras.layers.Dense(4, use_bias=False)(oh)            # embedding via matmul
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [lambda n: raw_can_ids(n, (8,))]


def e2_compare_onehot_float():
    inp = Inp((8,), dtype="float32", name="ids")
    oh = CompareOneHot(CAN_VOCAB)(inp)
    e = keras.layers.Dense(4, use_bias=False)(oh)
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [lambda n: raw_can_ids(n, (8,), dtype=np.float32)]


def e2_compare_onehot_only_int32():
    """Output IS the one-hot: checks exactness of the comparison after conversion."""
    inp = Inp((8,), dtype="int32", name="ids")
    return keras.Model(inp, CompareOneHot(CAN_VOCAB)(inp)), [lambda n: raw_can_ids(n, (8,))]


def e2_compare_onehot_only_float():
    inp = Inp((8,), dtype="float32", name="ids")
    return keras.Model(inp, CompareOneHot(CAN_VOCAB)(inp)), [
        lambda n: raw_can_ids(n, (8,), dtype=np.float32)]


def e2_compare_onehot_noOOV_only_int32():
    """Comparison one-hot without the OOV slot (OOV -> all zeros): is the graph simpler?"""
    class Hit(keras.layers.Layer):
        def call(self, x):
            v = keras.ops.convert_to_tensor(np.array(CAN_VOCAB), dtype="int32")
            return keras.ops.cast(keras.ops.equal(keras.ops.expand_dims(x, -1), v), "float32")
    inp = Inp((8,), dtype="int32", name="ids")
    return keras.Model(inp, Hit()(inp)), [lambda n: raw_can_ids(n, (8,))]


def e3_category_encoding_only():
    """Output IS the CategoryEncoding one-hot: exactness check."""
    inp = Inp((1,), dtype="int32", name="idx")
    oh = keras.layers.CategoryEncoding(num_tokens=6, output_mode="one_hot")(inp)
    return keras.Model(inp, oh), [lambda n: RNG.integers(0, 6, size=(n, 1)).astype(np.int32)]


class TfGatherEmbedding(keras.layers.Layer):
    """Embedding via tf.gather directly (no negative-index handling of keras.ops.take)."""

    def __init__(self, n, d, **kw):
        super().__init__(**kw)
        self.n, self.d = n, d

    def build(self, _):
        self.table = self.add_weight(shape=(self.n, self.d), initializer="uniform")

    def call(self, x):
        return tf.gather(self.table, x)

    def get_config(self):
        return {**super().get_config(), "n": self.n, "d": self.d}


def e3_embedding_tf_gather():
    inp = Inp((8,), dtype="int32", name="idx")
    e = TfGatherEmbedding(6, 4)(inp)
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [lambda n: RNG.integers(0, 6, size=(n, 8)).astype(np.int32)]


def e3_category_encoding():
    inp = Inp((1,), dtype="int32", name="idx")
    oh = keras.layers.CategoryEncoding(num_tokens=6, output_mode="one_hot")(inp)
    out = keras.layers.Dense(3)(oh)
    return keras.Model(inp, out), [lambda n: RNG.integers(0, 6, size=(n, 1)).astype(np.int32)]


def e3_embedding():
    inp = Inp((8,), dtype="int32", name="idx")
    e = keras.layers.Embedding(6, 4)(inp)
    out = keras.layers.Dense(3)(keras.layers.Flatten()(e))
    return keras.Model(inp, out), [lambda n: RNG.integers(0, 6, size=(n, 8)).astype(np.int32)]


def _window_head(x):
    h = keras.layers.Conv1D(8, 3, activation="relu")(x)
    h = keras.layers.GlobalAveragePooling1D()(h)
    return keras.layers.Dense(3)(h)


def _window_sample(dtype, same=False):
    def f(n):
        w = np.empty((n, 64, 5), np.float32)
        w[..., 0] = raw_can_ids(n, (64,))
        w[..., 1:] = raw_numeric(n, (64, 4), same=same)
        if dtype == np.int32:
            w = np.round(w)
        return w.astype(dtype)
    return f


def _e4(dtype, same=False):
    inp = Inp((64, 5), dtype=dtype, name="window")
    cat = keras.layers.Lambda(lambda x: x[:, :, 0])(inp)                    # (64,)
    num = keras.layers.Lambda(lambda x: keras.ops.cast(x[:, :, 1:5], "float32"))(inp)
    norm = keras.layers.Normalization(axis=-1)
    norm.adapt(raw_numeric(256, (64, 4), same=same).reshape(-1, 4))
    feats = keras.layers.Concatenate()([CompareOneHot(CAN_VOCAB)(cat), norm(num)])  # (64, 10)
    return keras.Model(inp, _window_head(feats)), [_window_sample(np.dtype(dtype).type, same)]


def e4_window_float32():
    return _e4("float32")


def e4_window_int32():
    return _e4("int32")


def e4_window_int32_same_scale():
    return _e4("int32", same=True)


def e5_two_inputs():
    num_in = keras.Input(batch_shape=(1, 64, 4), dtype="float32", name="a_numeric")
    cat_in = keras.Input(batch_shape=(1, 64), dtype="int32", name="b_can_id")
    norm = keras.layers.Normalization(axis=-1)
    norm.adapt(raw_numeric(256, (64, 4)).reshape(-1, 4))
    feats = keras.layers.Concatenate()([CompareOneHot(CAN_VOCAB)(cat_in), norm(num_in)])
    return keras.Model([num_in, cat_in], _window_head(feats)), [
        lambda n: raw_numeric(n, (64, 4)), lambda n: raw_can_ids(n, (64,))]


EXPERIMENTS = [
    e1_normalization_layer, e1_lambda_standardize, e1_custom_standardize, e1_rescaling,
    e1_normalization_only, e1_normalization_only_same_scale, e1_split_inputs_normalization_only,
    e2_integer_lookup, e2_string_lookup, e2_compare_onehot_int32, e2_compare_onehot_float,
    e2_compare_onehot_only_int32, e2_compare_onehot_only_float, e2_compare_onehot_noOOV_only_int32,
    e3_category_encoding, e3_category_encoding_only, e3_embedding, e3_embedding_tf_gather,
    e4_window_float32, e4_window_int32, e4_window_int32_same_scale,
    e5_two_inputs,
]


# ---------------------------------------------------------------- conversion + analysis
def convert(model, samplers, mode):
    # Multi-input models: a positional list is matched against the converter's own input order,
    # which is NOT the Keras order (measured: f0..f4 became f2,f0,f4,f3,f1). Yield a dict keyed by
    # signature input name unless PROBE_REP=list (to reproduce the mismatch).
    as_dict = len(model.inputs) > 1 and os.environ.get("PROBE_REP", "dict") == "dict"
    names = [t.name for t in model.inputs]

    def rep():
        for _ in range(100):
            xs = [s(1) for s in samplers]
            yield dict(zip(names, xs)) if as_dict else xs

    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = rep
    if mode in ("c", "cf"):
        conv = tf.lite.TFLiteConverter.from_keras_model(model)
        conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS] + (
            [tf.lite.OpsSet.SELECT_TF_OPS] if mode == "cf" else [])
        return conv.convert()
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    if mode == "a":
        conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    return conv.convert()


def _q(x, d):
    s, z = d["quantization"]
    if d["dtype"] in (np.int8, np.uint8, np.int16) and s:
        return np.clip(np.round(x / s + z), np.iinfo(d["dtype"]).min,
                       np.iinfo(d["dtype"]).max).astype(d["dtype"])
    return x.astype(d["dtype"])


def _dq(y, d):
    s, z = d["quantization"]
    return (y.astype(np.float32) - z) * s if s else y.astype(np.float32)


def analyse(blob, model, samplers):
    info = {"size_bytes": len(blob)}
    interp = Interpreter(model_content=blob)
    ops = [o["op_name"] for o in interp._get_ops_details()]
    info["ops"] = ops
    info["distinct_ops"] = sorted(set(ops))
    info["not_in_tflm"] = sorted(set(ops) - TFLM_OPS)
    ins, outs = interp.get_input_details(), interp.get_output_details()
    info["inputs"] = [f"{d['name']}:{np.dtype(d['dtype']).name}{list(d['shape'])}"
                      f" q={tuple(round(float(v), 6) for v in d['quantization'])}" for d in ins]
    info["outputs"] = [f"{d['name']}:{np.dtype(d['dtype']).name}{list(d['shape'])}"
                       f" q={tuple(round(float(v), 6) for v in d['quantization'])}" for d in outs]
    # tensor dtypes inside the graph (to see e.g. GATHER params int8, EQUAL operands)
    tdet = {t["index"]: t for t in interp.get_tensor_details()}
    info["op_io_dtypes"] = sorted({
        f"{o['op_name']}("
        + ",".join(np.dtype(tdet[i]['dtype']).name for i in o["inputs"] if i >= 0)
        + ")->" + ",".join(np.dtype(tdet[i]['dtype']).name for i in o["outputs"])
        for o in interp._get_ops_details()})
    try:
        interp.allocate_tensors()
        # match converted inputs to keras inputs by order of name
        n = 32
        raw = [s(n) for s in samplers]
        ref = np.asarray(model.predict([r for r in raw] if len(raw) > 1 else raw[0], verbose=0))
        got = []
        order = _input_order(ins, model)
        for k in range(n):
            for d, j in zip(ins, order):
                interp.set_tensor(d["index"], _q(raw[j][k:k + 1], d))
            interp.invoke()
            got.append(_dq(interp.get_tensor(outs[0]["index"]), outs[0])[0])
        got = np.stack(got)
        err = np.abs(got - ref.reshape(got.shape))
        span = float(np.ptp(ref)) or 1.0
        info["inference"] = "ok"
        info["max_abs_err"] = round(float(err.max()), 5)
        info["max_err_over_output_range"] = round(float(err.max()) / span, 4)
        if got.ndim >= 2 and model.name.startswith("probe_onlyout"):
            pass
        info["per_last_axis_max_err"] = [round(float(v), 4) for v in
                                         err.reshape(-1, err.shape[-1]).max(0)]
    except Exception as e:  # noqa: BLE001
        info["inference"] = f"FAILED: {type(e).__name__}: {str(e).strip()[:400]}"
    return info


def _input_order(ins, model):
    names = [t.name for t in model.inputs]
    order = []
    for d in ins:
        hits = [j for j, nm in enumerate(names) if nm in d["name"]]
        order.append(hits[0] if hits else len(order))
    return order


def check_fix_batch(build):
    """Build with batch None, run Caravan's fix_batch, compare predictions with the original."""
    try:
        BATCH[0] = None
        model, samplers = build()
        if len(model.inputs) != 1:
            return "n/a (fix_batch handles only model.inputs[0])"
        fixed = fix_batch(model)
        x = samplers[0](8)
        ref = np.asarray(model.predict(x, verbose=0))
        got = np.concatenate([np.asarray(fixed.predict(x[i:i + 1], verbose=0)) for i in range(8)])
        d = float(np.abs(ref - got).max())
        return "ok (same outputs)" if d < 1e-4 else f"CHANGES OUTPUT (max abs diff {d:.4g})"
    except Exception as e:  # noqa: BLE001
        return "FAILED: " + short_err(e)[:300]
    finally:
        BATCH[0] = 1


def short_err(e):
    lines = [ln for ln in str(e).splitlines() if ln.strip()]
    keep = [ln for ln in lines if "error" in ln.lower() or "op" in ln.lower()
            or "not supported" in ln.lower() or "failed" in ln.lower()]
    return f"{type(e).__name__}: " + " | ".join((keep or lines)[:6])[:900]


def run_all():
    import subprocess
    merged = {"tf": tf.__version__, "keras": keras.__version__}
    for build in EXPERIMENTS:
        name = build.__name__
        with open(HERE / f"log_{name}.txt", "w") as log:
            rc = subprocess.run([sys.executable, __file__, "--only", name], stdout=log,
                                stderr=subprocess.STDOUT).returncode
        f = HERE / f"results_{name}.json"
        if rc == 0 and f.exists():
            merged[name] = json.loads(f.read_text())[name]
        else:
            last = [ln for ln in (HERE / f"log_{name}.txt").read_text().splitlines()
                    if ln.startswith("MODE ")]
            merged[name] = {"crashed": f"process exit code {rc}", "last_step": last[-1:]}
        print(name, "->", "ok" if rc == 0 else f"exit {rc}", flush=True)
    (HERE / "results.json").write_text(json.dumps(merged, indent=1))
    print(f"wrote {HERE / 'results.json'}")


def main(filters):
    results = {"tf": tf.__version__, "keras": keras.__version__}
    for build in EXPERIMENTS:
        name = build.__name__
        if filters and not any(f in name for f in filters):
            continue
        print(f"\n===== {name}", flush=True)
        res = {}
        res["fix_batch"] = check_fix_batch(build)
        try:
            BATCH[0] = 1
            model, samplers = build()
        except Exception as e:  # noqa: BLE001
            res["build"] = short_err(e)
            traceback.print_exc()
            results[name] = res
            print(json.dumps(res, indent=1))
            continue
        failed = 0
        modes = os.environ.get("PROBE_MODES", "a,b,c,cf").split(",")
        for mode in ("a", "b", "c", "cf"):
            if mode not in modes:
                failed += 1  # a skipped mode counts as failed so c/cf can be forced
                continue
            if mode in ("c", "cf") and failed < 2:
                continue
            print(f"MODE {mode} converting", flush=True)
            try:
                blob = convert(model, samplers, mode)
            except Exception as e:  # noqa: BLE001
                res[mode] = {"convert": "FAILED", "error": short_err(e)}
                failed += 1
                continue
            (HERE / f"{name}__{mode}{'_listrep' if os.environ.get('PROBE_REP') == 'list' else ''}.tflite").write_bytes(blob)
            res[mode] = {"convert": "ok", **analyse(blob, model, samplers)}
        results[name] = res
        print(json.dumps(res, indent=1), flush=True)
    tag = "_".join(filters) + ("_listrep" if os.environ.get("PROBE_REP") == "list" else "")
    out = HERE / ("results.json" if not filters else f"results_{tag}.json")
    out.write_text(json.dumps(results, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--only"]:
        EXPERIMENTS[:] = [b for b in EXPERIMENTS if b.__name__ == sys.argv[2]]
        main([sys.argv[2]])
    elif sys.argv[1:]:
        main(sys.argv[1:])
    else:
        run_all()
