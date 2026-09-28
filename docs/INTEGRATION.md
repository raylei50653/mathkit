# 與 `math` 的整合契約

目標：`math` 可以用 mathkit，但**不需要**它；拿掉 mathkit 時 `math` 的建置、重播與 Lean 驗證都不受影響。

## 1. 邊界

| mathkit 可以 | mathkit 不可以 |
| --- | --- |
| 唯讀 `math/artifacts/**/*.json`、`math/docs/**/*.md` | 寫入 `math` 任何檔案（輸出一律到使用者指定路徑或 mathkit 自己的快取） |
| 在 `domains/c5` 內獨立重新實作 C5 概念 | import `math/scripts/*.py` |
| 讀 artifact 的 `source_sha256` 並記入 provenance | 修改或重新產生 artifact |
| 輸出差異報告 | 判定 artifact「錯」並自動修正 |

## 2. 導入方式（由輕到重）

1. **一次性 CLI**（建議起點，`math` 零改動）
   ```bash
   cd ../math
   uv run --with ../mathkit mathkit render artifacts/c5_k4_blocks/observations.json -o /tmp/k4.svg
   ```
2. **腳本內選擇性 import**（`math` 改單一腳本）
   ```python
   try:
       from mathkit.core import kempe
   except ImportError:
       kempe = None  # 退回既有實作
   ```
   腳本 docstring 的重播指令改為 `uv run --with networkx==3.5 --with ../mathkit ...`。
3. **正式依賴**（`math` 決定後才做）
   在 `math` 加 `pyproject.toml` 的 optional-dependency group `viz = ["mathkit @ git+..."]`，並釘 commit。

`math` 目前沒有 `pyproject.toml`，因此 1、2 是主要路徑。

## 3. 證據層級對齊

`math/docs/STATUS.md` 區分紙面、Python 有限證書、Lean 等證據層級。mathkit 的所有輸出都帶：

```json
"evidence": "computation",
"provenance": {"source": "artifacts/...", "sha256": "...", "mathkit": "0.1.0"}
```

mathkit 產生的圖只是呈現或獨立重算，**不提升**任何結論的證據層級。`mathkit check` 一致只代表「兩個獨立實作結果相同」。

## 4. Artifact 辨識

artifact 沒有統一 schema，adapter 以「目錄名 + 檔頭欄位」辨識：

```python
# domains/c5/adapters.py（草案）
@register("c5.k4_blocks")
def matches(path, head):
    return path.parent.name == "c5_k4_blocks" and head.get("schema") == 1
```

未辨識的檔案退回 `generic_json`（樹狀檢視），不報錯。
M3 前先針對 3 個代表性目錄寫 adapter，再依使用頻率擴充。

## 5. 大檔案

`artifacts/` 總量約 559 MB。adapter 的 `records()` 必須延遲讀取：

- 先只讀檔頭（前 64 KB）判斷格式；
- 大陣列用串流解析（`ijson`，extra `[stream]`）或建立 byte-offset 索引快取於 `~/.cache/mathkit/`；
- 檢視器分頁請求 record，不整檔送到瀏覽器。

## 6. 論文

`render.tikz` 輸出放 `math/paper/figures/` 的動作由**使用者**執行（指定 `-o`），mathkit 不主動寫入。建議在 `math` 以 Makefile 規則記錄生成指令與輸入 sha256，讓圖可重播。
