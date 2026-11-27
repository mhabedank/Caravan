# Edge cases for the profiler of `caravan init` (feature 013, T002)

Small hand-written tables, each for one rule of research R4 or one refusal:

| File | What it checks |
|---|---|
| `empty-column.csv` | rule 1: a column with every cell empty is left out |
| `constant.csv` | rule 2: one value in every row carries no information |
| `ids.csv` | rule 5: integers in a column named like an identifier (`sensor_id`, `code`) are a category |
| `small-codes.csv` | rule 7: an integer column with 5 distinct values is a category |
| `missing.csv` | empty cells are counted; the type comes from the values present |
| `bad-name.csv` | a name that cannot name a feature is proposed as left out |
| `headers-differ/` | two files whose headers differ stop profiling, naming both |
| `no-header/` | a file whose first row is numbers has no header |
| `numeric-output.csv` | a numeric `target` is proposed as the output, of type `number` |

Added by feature 015 (T002), for the certainty of each rule (research R1) and the examples a missing
answer names (research R5):

| File | What it checks |
|---|---|
| `time-column.csv` | a numeric `t` that never decreases, 40 distinct values: proposed left out, uncertain (a time or a counter) |
| `many-text.csv` | a text `station` with 300 distinct values: a category, but uncertain (an identifier or a time stamp?) |
| `no-output.csv` | three float columns, none named like an answer and none with few values: the output is open |
| `ok-fault.csv` | a `state` of `ok` and `fault`: as an anomaly output, the value that means normal is open |
