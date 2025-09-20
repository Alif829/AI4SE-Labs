# Java Method Miner (Tree-Sitter + Lizard)

This workspace contains a script to mine Java methods from GitHub repositories, compute AST metrics with Tree-Sitter, and compute cyclomatic complexity with Lizard. It emits newline-delimited JSON (NDJSON) chunk files suitable for downstream processing.

Files added:
- `requirements.txt` - Python dependencies.
- `mine_java_methods_lizard.py` - The main mining script.

## 1) Install dependencies

Save `requirements.txt` and run:

```bash
python -m pip install -r requirements.txt
```

## 2) Build Tree-Sitter Java (one-time)

You must compile the Tree-Sitter Java grammar into a shared library the Python binding can load.

Clone the grammar repo (pick a path you control):

```bash
git clone https://github.com/tree-sitter/tree-sitter-java /path/to/tree-sitter-java
```

Run this small Python snippet (it builds `build/my-languages.so`):

```bash
python - <<'PY'
from tree_sitter import Language
Language.build_library(
  'build/my-languages.so',
  ['/path/to/tree-sitter-java']
)
print("Built build/my-languages.so")
PY
```

Note the path to `build/my-languages.so` — pass that path to the script (arg `--tree_sitter_lib`) or place it at the default `build/my-languages.so`.

## 3) Quick test run

Export your GitHub token (or pass via `--github_token`):

```bash
export GITHUB_TOKEN="ghp_..."
python git_miner.py --out_dir ./out_test --clone_dir ./repos_test --test --cleanup
```

Alternatively you can put your token in a `.env` file in the project root with content:

```ini
# .env
GITHUB_TOKEN=ghp_...
```

Then run (the script auto-loads `.env` by default):

```bash
python git_miner.py --out_dir ./out_test --clone_dir ./repos_test --test --cleanup
```

You can also specify a custom env file with `--env_file /path/to/.env`.

## 4) Full run (example)

```bash
python java_miner.py --out_dir ./out_full --clone_dir ./repos_full --target_methods 25000 --cleanup
```

## Notes
- The script prefers Lizard for cyclomatic complexity; it falls back to an AST-based heuristic if needed.
- Output files are `methods_chunk_1.ndjson`, `methods_chunk_2.ndjson`, ... in the `--out_dir` directory.
- Respect repository licenses when using mined code.

