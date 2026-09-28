# 技術棧

## 總表

| 範圍 | 選擇 | 必要／選用 |
| --- | --- | --- |
| 語言（引擎、CLI） | Python ≥ 3.12 | 必要 |
| 套件與環境 | uv + hatchling（`src/` layout） | 必要 |
| 數值 | numpy（Tutte 線性系統） | 必要，唯一的必要第三方依賴 |
| 圖論參照 | networkx 3.5 | extra `[nx]`；只用於轉換與測試對照 |
| 資料模型 | 標準庫 `dataclasses` + 手寫 JSON Schema 產生 | 必要（無依賴） |
| Schema 驗證 | `jsonschema` | extra `[validate]` |
| CLI | 標準庫 `argparse` | 必要 |
| 本機伺服器 | 標準庫 `http.server` | 必要 |
| 測試 | pytest、hypothesis | dev |
| 靜態檢查 | ruff（lint + format）、pyright（strict） | dev |
| 層級守衛 | import-linter | dev |
| 檢視器 | TypeScript + Vite + Cytoscape.js + KaTeX | 只在開發檢視器時需要（pnpm） |
| TS 型別 | `json-schema-to-typescript` 從 `schemas/scene.schema.json` 生成 | dev |
| 論文輸出 | TikZ 文字輸出（無執行期依賴） | 必要 |
| 加速（評估） | Rust + PyO3 + maturin | M5，不承諾 |
| CI | GitHub Actions：ruff、pyright、pytest、golden、viewer build | — |

本機已有：Python 3.14、uv、Node 24、pnpm。

## 選型理由

### Python 為引擎主語言
- `math` 的 196 支腳本全是 Python，使用方直接 import，零轉換成本。
- 問題規模是「很多小圖 × 窮舉」，瓶頸多在演算法而非語言；bitmask + 良好剪枝在 Python 已足夠（`math` 現況已證明）。
- 若日後真有熱點，以 Rust 擴充**同名函式**，Python 介面不變（ADR-0003）。

### 自有小圖結構，而非直接用 networkx
- networkx 物件大、慢、不可雜湊，不適合做「數百萬個小圖」的窮舉鍵。
- `math` 腳本本來就大量用 bitmask；把這個慣例正式化。
- 仍提供 `to_networkx()`／`from_networkx()`，networkx 當參照實作與測試對照組。

### dataclasses 而非 pydantic
- 核心不想帶重依賴；Scene 模型簡單，手寫 `to_json`／schema 產生器即可。
- 若 Scene 驗證需求變複雜，再以 extra 形式引入 pydantic，不動核心。

### SVG／TikZ 手寫輸出，而非 matplotlib
- 需要決定性位元組輸出（golden 測試、sha256 釘住）；matplotlib 輸出含版本、ID 等不穩定內容。
- TikZ 讓論文圖與正文字型、色彩一致。
- 圖元只有點、線、多邊形、文字、標籤，手寫生成器約數百行。

### 檢視器：Vite + TS + Cytoscape.js
- Cytoscape.js：圖檢視成熟、支援 preset 座標（直接用 Python 算好的 Tutte 座標）、選取／高亮 API 完整。
- 不選 D3：自由度高但圖互動要自己寫大量程式碼。
- 不選 React／Svelte 等框架（初期）：頁面只有「列表 + 畫布 + 側欄」，原生 TS 足夠；複雜度上升再評估。
- KaTeX：節點／標題的數學標籤。
- 產物打包進 wheel，使用者不需要 Node。

### 不選的方案
| 方案 | 否決理由 |
| --- | --- |
| SageMath | 安裝重、與 uv 生態整合差；可作為使用者端選用對照，不作依賴 |
| Manim | 動畫導向，不適合大量 record 的檢視與決定性靜態圖 |
| Jupyter 為主要介面 | 會把邏輯留在 notebook；可提供 `_repr_svg_` 讓 Scene 在 notebook 中顯示，但不作核心 |
| Graphviz 為唯一 layout | 無法固定外圈做平面嵌入；保留為 `layered` 的可選後端 |
| 直接寫成 Lean ProofWidgets | 會嵌入 `math` 的 Lean 建置；列為 M5 評估 |

## 版本策略

- Python 支援範圍：3.12–3.14；CI 矩陣三版。
- Scene schema 以 `mathkit.scene/<major>` 版本化；major 變動需提供轉換器。
- 語意化版本；0.x 期間 core API 可破壞性變更，但需在 CHANGELOG 註明。
