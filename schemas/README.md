`ir.schema.json`、`scene.schema.json` 由 `uv run mathkit schema --out-dir schemas` 產生後提交；`tests/test_cli.py` 會檢查是否過期。TS 檢視器的型別由此生成。

`ir.schema.json` 只嚴格檢查核心 kinds；`c5.*` 等領域 kinds 由各 domain pack 在載入時驗證。
