# The `defaults` section

Preprocessing and encoder settings applied to **every input feature of one type**, so that a
manifest with twenty numeric columns does not repeat itself twenty times. `<type>` is `number`, `category`,
`binary` or `image`.

Precedence, highest first: a feature's own value, then the type's entry here, then the type's
built-in default.

Each field mirrors the per-feature setting of the same name exactly, and that setting's entry
says what it does and what its values mean.

| Field | Mirrors |
|---|---|
| {mf}`defaults.<type>.preprocessing.normalization` | {mf}`input_features[].preprocessing.normalization` |
| {mf}`defaults.<type>.preprocessing.missing_value_strategy` | {mf}`input_features[].preprocessing.missing_value_strategy` |
| {mf}`defaults.<type>.preprocessing.fill_value` | {mf}`input_features[].preprocessing.fill_value` |
| {mf}`defaults.<type>.preprocessing.most_common` | {mf}`input_features[].preprocessing.most_common` |
| {mf}`defaults.<type>.preprocessing.vocab` | {mf}`input_features[].preprocessing.vocab` |
| {mf}`defaults.<type>.preprocessing.fallback_true_label` | {mf}`input_features[].preprocessing.fallback_true_label` |
| {mf}`defaults.<type>.preprocessing.height` | {mf}`input_features[].preprocessing.height` |
| {mf}`defaults.<type>.preprocessing.width` | {mf}`input_features[].preprocessing.width` |
| {mf}`defaults.<type>.preprocessing.num_channels` | {mf}`input_features[].preprocessing.num_channels` |
| {mf}`defaults.<type>.preprocessing.resize_method` | {mf}`input_features[].preprocessing.resize_method` |
| {mf}`defaults.<type>.encoder.type` | {mf}`input_features[].encoder.type` |
| {mf}`defaults.<type>.encoder.embedding_size` | {mf}`input_features[].encoder.embedding_size` |

:::{manifest-field} defaults.<type>.preprocessing.normalization
**Type** and **Default** as {mf}`input_features[].preprocessing.normalization`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.normalization` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.missing_value_strategy
**Type** and **Default** as {mf}`input_features[].preprocessing.missing_value_strategy`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.missing_value_strategy` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.fill_value
**Type** and **Default** as {mf}`input_features[].preprocessing.fill_value`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.fill_value` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.most_common
**Type** and **Default** as {mf}`input_features[].preprocessing.most_common`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.most_common` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.vocab
**Type** and **Default** as {mf}`input_features[].preprocessing.vocab`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.vocab` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.fallback_true_label
**Type** and **Default** as {mf}`input_features[].preprocessing.fallback_true_label`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.fallback_true_label` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.height
**Type** and **Default** as {mf}`input_features[].preprocessing.height`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.height` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.width
**Type** and **Default** as {mf}`input_features[].preprocessing.width`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.width` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.num_channels
**Type** and **Default** as {mf}`input_features[].preprocessing.num_channels`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.num_channels` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.preprocessing.resize_method
**Type** and **Default** as {mf}`input_features[].preprocessing.resize_method`, for the type `<type>`

**Does** — sets {mf}`input_features[].preprocessing.resize_method` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.encoder.type
**Type** and **Default** as {mf}`input_features[].encoder.type`, for the type `<type>`

**Does** — sets {mf}`input_features[].encoder.type` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{manifest-field} defaults.<type>.encoder.embedding_size
**Type** and **Default** as {mf}`input_features[].encoder.embedding_size`, for the type `<type>`

**Does** — sets {mf}`input_features[].encoder.embedding_size` for every input feature of type `<type>` that does not set it
itself.

**Change it** — when most columns of one type need the same value and you would otherwise write it
on each of them.
:::

:::{note}
{mf}`defaults.<type>.preprocessing.vocab` and
{mf}`defaults.<type>.preprocessing.fallback_true_label` pin one value for *every* column of that
type, and two columns rarely share a vocabulary. Set these two on the feature itself.
:::
