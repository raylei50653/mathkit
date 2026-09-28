# 專案規劃

## 1. 背景

`math` repo 目前的計算與呈現方式：

- 196 支獨立 Python 腳本（`scripts/`），各自重寫相近的原語：
  - 圖著色與 list-coloring 窮舉
  - Kempe swap／Kempe chain 連通性
  - 平面性與 K5／K3,3 minor 證書（115 支腳本用到 planar／minor）
  - C5 boundary pattern 正規化與 relation 運算
  - sha256 輸入指紋與決定性 JSON 輸出
- 約 559 MB 的決定性 JSON artifacts（`artifacts/`），格式鬆散一致（`schema`、`scope`、`source_sha256`），但沒有正式 schema，也沒有檢視工具。
- 圖形幾乎只存在於紙面證明與 Markdown 表格；`tools/docgraph` 只處理文件關係，不處理數學物件。

痛點：同一原語重寫多次，正確性靠各自重播；幾十筆 record 的結構只能讀 JSON，很難看出來；論文要的圖得手畫 TikZ。

## 2. 目標

1. **引擎**：一組經過測試、決定性、可重用的組合數學原語，讓新腳本能直接 import，不用再自己寫一套。
2. **視覺化**：把 artifacts 與引擎物件轉成
   - 靜態圖：SVG（文件）、TikZ（論文），輸出逐位元組決定性；
   - 互動檢視：本機瀏覽器翻 records、看染色／Kempe chain／minor 分支集。
3. **非侵入**：研究 repo 零必要改動。mathkit 讀 artifacts 時只讀、不寫；研究 repo 對 mathkit 的依賴一律是選擇性的。
4. **可攜**：核心不含 C5 語義，換一個研究題目（例如別的著色問題、別的圖類）也能用。

## 3. 非目標

- 不取代 Lean。引擎結果屬「計算證據」層級，不是形式證明；需要進 Lean 的東西仍在 `math` 內處理。
- 不重寫或搬遷 `math/scripts/` 既有腳本。遷移由 `math` 自行決定，逐支、可選。
- 不做通用 CAS（符號代數）或通用繪圖庫。
- 不做雲端服務；檢視器是本機靜態頁。
- 初期不做 Lean infoview widget（見 M5，評估後再決定）。

## 4. 使用情境

| # | 情境 | 使用者動作 | 需要的模組 |
| --- | --- | --- | --- |
| U1 | 寫新的窮舉腳本 | `from mathkit.core import coloring, kempe` | core |
| U2 | 看某筆 record 長什麼樣 | `mathkit render <artifact> --record 87` | adapters + layout + render |
| U3 | 翻整個 artifact 目錄 | `mathkit serve artifacts/` | viewer |
| U4 | 論文插圖 | `mathkit render ... --format tikz` | render.tikz |
| U5 | 交叉驗證舊腳本 | `mathkit check <artifact>` 用獨立實作重算並比對 | core + domains.c5 |
| U6 | artifact 格式健檢 | `mathkit validate <artifact>` | adapters + schemas |

U5 很重要：mathkit 的獨立實作可以當舊腳本的 second opinion，提高計算證據的可信度。

## 5. 里程碑

每個里程碑都要可交付、可單獨使用。

### M0 規劃與骨架（本次）
- 目錄、pyproject、文件、ADR。
- 驗收：`uv run pytest` 通過 smoke test。

### M1a 垂直切片：能真的畫出東西
- `core.graph`：不可變小圖（整數頂點、bitmask 鄰接），可與 networkx 雙向轉換。
- `ir`：`MathDocument`＋ `graph`、`coloring` 兩個核心 kinds。
- `domains.c5`：只加 `c5.boundary_cycle` kind 與其 compile rule（外圈、boundary 標籤）。
- `compile`：規則註冊表＋通用 `graph`／`coloring` 規則。
- `scene`：Scene 模型、`origin`、JSON Schema 產生（`mathkit schema`）。
- `layout.fixed`、`layout.circular`。
- `render.svg`：決定性輸出、深色模式。
- CLI：`mathkit render <ir-or-scene.json> -o out.svg`。
- 驗收：
  - `mathkit render examples/c5.ir.json` 產出 C5（外圈五點＋一個中心點）的 SVG；
  - 同輸入兩次 sha256 相同；
  - `validate_origins` 對 M1a 所有輸出成立；
  - 同一 `(kind, view)` 重複註冊會拋 `RuleConflictError`；
  - import-linter 分層與禁止依賴 contracts 全數通過。

### M1b 平面引擎
- `core.planar`：
  1. 由給定 rotation system 建嵌入、列舉面、以 Euler 公式驗證（`math` 的部分 artifacts 已記錄 planar rotation，可直接吃）；
  2. 平面性測試與嵌入搜尋：先以 networkx `check_planarity` 作為選用後端（extra `[nx]`），再以自有 LR 演算法取代；自有版與 networkx 交叉比對通過後才成為預設。
- `layout.tutte`：外圈固定、小圖有理數精確解（ADR-0006）。
- 驗收：5 種以上平面圖類的語意 golden 與位元組 golden；隨機平面圖 Tutte 無邊交叉。

### M2 著色引擎
- `core.coloring`：proper coloring、list coloring、所有擴張列舉（bitmask 回溯）。
- `core.kempe`：Kempe chain 分量、swap、可達等價類。
- `core.minor`：K5／K3,3 minor 證書的**檢查器**（給分支集 → 驗證），搜尋器為次要。
- `core.certificate`：輸入指紋、決定性 JSON dump、replay 描述。
- 驗收：hypothesis 性質測試；與 networkx 在隨機小圖上交叉比對。

### M3 C5 domain pack + math artifacts 轉接
- `domains.c5`：boundary pattern、Σ 十位元識別、relation 正規化、染色色盤。
- `domains.c5` adapters：辨識 artifact 目錄 → 轉成 Math IR；補上所需的 `c5.*` kinds 與 compile rules（spoke、attachment、palette、extension witness 等，按 adapter 實際需要）。
- `mathkit check`：獨立重算至少 3 類既有 artifact 並比對。
- `render.tikz`。
- 驗收：對 `math` 至少 3 個 artifact 目錄的交叉驗證全部一致；`math` repo 無任何改動。

### M4 互動檢視器
- `viewer/`：Vite + TypeScript 靜態頁，以 Scene 顯示，點選元素依 `origin` 顯示 IR 語義。
- `mathkit serve`：Python 標準庫起本機 HTTP，把 artifacts 經 adapter → Math IR → compile 轉成 Scene 後送出（IR 一併提供）。
- 功能：record 列表／篩選、著色切換、Kempe chain 高亮、minor 分支集著色、匯出 SVG。
- 驗收：559 MB artifacts 目錄可在 3 秒內列出（延遲載入、不整包讀）。

### M5 評估項（不承諾）
- Rust 加速核心（PyO3），只在 profiling 顯示 Python 核心為瓶頸時啟動（ADR-0003）。
- Lean ProofWidgets 橋接：infoview 內顯示 Scene。會讓 `math` 的 lakefile 多一個 require，違反「零必要改動」，因此只能做成獨立 Lean package 並選擇性引入。
- 其他 domain pack。

## 6. 成功指標

- `math` 新腳本中，import mathkit 原語、取代自寫版本的比例（M3 後統計）。
- `mathkit check` 覆蓋的 artifact 類別數。
- 決定性契約（ARCHITECTURE §6）：語意 golden 全平台通過；exact 路徑位元組 golden 全平台通過。
- 核心零強制重依賴：`pip install mathkit` 只帶 numpy；networkx、pydantic 等為 extras。

## 7. 風險與對策

| 風險 | 影響 | 對策 |
| --- | --- | --- |
| artifact 格式不一致 | adapter 寫不完 | adapter 以目錄為單位、逐個註冊；未知格式退回「原始 JSON 樹檢視」 |
| mathkit 與舊腳本結果不一致 | 信任問題 | 不一致時兩邊都不預設為對；輸出最小差異 record，交由人判斷 |
| 引擎被誤當成形式證明 | 證據層級混淆 | 所有輸出標註 `evidence: "computation"`，文件明示 |
| 大 artifact 拖慢檢視器 | 不可用 | 串流／索引、分頁；伺服器端只回需要的 record |
| 範圍膨脹成通用數學平台 | 做不完 | 以 §3 非目標為界；新 domain 需有真實使用方才加 |
