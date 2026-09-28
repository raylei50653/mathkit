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

### M1 核心資料結構 + 靜態 SVG（最小可用）
- `core.graph`：不可變的小圖（整數頂點、bitmask 鄰接），可與 networkx 雙向轉換。
- `core.planar`：平面性檢查、組合嵌入（rotation system）。
- `layout.tutte`：固定外圈的 Tutte 嵌入，boundary cycle 擺在正多邊形上。
- `scene`：Scene 資料模型 + JSON Schema。
- `render.svg`：Scene → SVG，決定性輸出。
- CLI：`mathkit render`（先吃 Scene JSON 或 edge list）。
- 驗收：同輸入兩次輸出 sha256 相同；5 種以上圖類 golden test。

### M2 著色引擎
- `core.coloring`：proper coloring、list coloring、所有擴張列舉（bitmask 回溯）。
- `core.kempe`：Kempe chain 分量、swap、可達等價類。
- `core.minor`：K5／K3,3 minor 證書的**檢查器**（給分支集 → 驗證），搜尋器為次要。
- `core.certificate`：輸入指紋、決定性 JSON dump、replay 描述。
- 驗收：hypothesis 性質測試；與 networkx 在隨機小圖上交叉比對。

### M3 C5 domain pack + math artifacts 轉接
- `domains.c5`：boundary pattern、Σ 十位元識別、relation 正規化、染色色盤。
- `adapters.math_artifacts`：辨識 artifact 目錄 → 轉成 Scene。
- `mathkit check`：獨立重算至少 3 類既有 artifact 並比對。
- `render.tikz`。
- 驗收：對 `math` 至少 3 個 artifact 目錄的交叉驗證全部一致；`math` repo 無任何改動。

### M4 互動檢視器
- `viewer/`：Vite + TypeScript 靜態頁，讀 Scene JSON。
- `mathkit serve`：Python 標準庫起本機 HTTP，把 artifacts 經 adapter 轉 Scene 後送出。
- 功能：record 列表／篩選、著色切換、Kempe chain 高亮、minor 分支集著色、匯出 SVG。
- 驗收：559 MB artifacts 目錄可在 3 秒內列出（延遲載入、不整包讀）。

### M5 評估項（不承諾）
- Rust 加速核心（PyO3），只在 profiling 顯示 Python 核心為瓶頸時啟動（ADR-0003）。
- Lean ProofWidgets 橋接：infoview 內顯示 Scene。會讓 `math` 的 lakefile 多一個 require，違反「零必要改動」，因此只能做成獨立 Lean package 並選擇性引入。
- 其他 domain pack。

## 6. 成功指標

- `math` 新腳本中，import mathkit 原語、取代自寫版本的比例（M3 後統計）。
- `mathkit check` 覆蓋的 artifact 類別數。
- 所有 render 輸出決定性（CI 以 golden sha256 把關）。
- 核心零強制重依賴：`pip install mathkit` 只帶 numpy；networkx、pydantic 等為 extras。

## 7. 風險與對策

| 風險 | 影響 | 對策 |
| --- | --- | --- |
| artifact 格式不一致 | adapter 寫不完 | adapter 以目錄為單位、逐個註冊；未知格式退回「原始 JSON 樹檢視」 |
| mathkit 與舊腳本結果不一致 | 信任問題 | 不一致時兩邊都不預設為對；輸出最小差異 record，交由人判斷 |
| 引擎被誤當成形式證明 | 證據層級混淆 | 所有輸出標註 `evidence: "computation"`，文件明示 |
| 大 artifact 拖慢檢視器 | 不可用 | 串流／索引、分頁；伺服器端只回需要的 record |
| 範圍膨脹成通用數學平台 | 做不完 | 以 §3 非目標為界；新 domain 需有真實使用方才加 |
