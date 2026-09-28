# 架構

mathkit 由兩個引擎組成，共用同一套 domain pack：

```
                         mathkit
                            │
         ┌──────────────────┴──────────────────┐
  Computation Engine                    Visualization Engine
  core: graph · planar · coloring       Math IR（數學意義）
        kempe · minor · relation              │ Visual Compiler
        certificate                           ▼
                                        Scene IR（純視覺）
                                              │ Layout
                                     ┌────────┼────────┐
                                    SVG      TikZ    Viewer

  domains/c5 同時提供：計算原語 · artifact adapters · 視覺編譯規則
```

## 1. 設計原則

1. **依賴單向**：研究 repo →（可選）mathkit。mathkit 永不 import 研究 repo 的程式碼。
2. **核心無領域語義**：`core`、`ir` 的基本型別、`scene`、`layout`、`render` 不知道 C5 是什麼；C5 只存在於 `domains/c5`。
3. **意義與外觀分離**（ADR-0005）：數學意義存在 **Math IR**；外觀存在 **Scene IR**。兩者之間只有 Visual Compiler 一條路。Scene 元素以 `origin` 指回 IR 物件 id，所以檢視器能顯示「這條邊在數學上是什麼」，但 renderer 本身不解讀它。
4. **決定性**：分兩層（ADR-0006，見 §6）。
5. **小依賴面**：核心只依賴 Python 標準庫 + numpy；其他以 extras 提供。

## 2. 分層

```
cli
domains | adapters          ← 領域語義、外部檔案
compile                     ← Visual Compiler：Math IR → Scene
render                      ← Scene → SVG / TikZ / JSON
layout                      ← 補 Scene 座標
ir | scene                  ← 兩份 IR，彼此不依賴
core                        ← 計算原語
```

上層可依賴下層，下層不得 import 上層；同一行以 `|` 分隔者互不依賴。由 import-linter 在 CI 強制（見 `pyproject.toml`）。

- `scene` 不依賴 `ir`：Scene 只存 `origin` 字串，不 import IR 型別。
- `compile` 本身只含規則註冊表與通用規則；C5 規則由 domain pack 註冊進來。

## 3. 模組職責

### core（計算引擎）
| 模組 | 職責 | 關鍵介面（草案） |
| --- | --- | --- |
| `graph` | 不可變小圖；頂點 `0..n-1`，鄰接為 int bitmask | `Graph.from_edges`, `.to_networkx()`, `.induced(mask)` |
| `planar` | rotation system、面列舉、平面性、外圈 | `Embedding.from_rotation(...)`, `embed(g)` |
| `coloring` | proper／list coloring、擴張列舉、色置換正規化 | `extensions(g, lists, fixed)` |
| `kempe` | 兩色子圖分量、swap、Kempe 等價類 | `chains(g, col, a, b)`, `swap(col, chain)` |
| `minor` | K5／K3,3 minor 分支集**驗證**；搜尋為輔 | `check_minor(g, branch_sets, H)` |
| `relation` | 有限 port 上的 pattern relation：交、投影、條件化 | `Relation.condition(literals)` |
| `certificate` | 輸入 sha256、決定性 JSON、replay 描述 | `fingerprint(paths)`, `dump(obj, path)` |

純函式或只回傳新物件；不讀寫檔案（`certificate.dump` 除外）。

### ir（Math IR）
描述「這是什麼數學物件、彼此是什麼關係」，不含任何座標或樣式。

```jsonc
{
  "schema": "mathkit.ir/1",
  "evidence": "computation",                 // computation | paper | lean
  "provenance": {"source": "artifacts/...json", "sha256": "...", "mathkit": "0.1.0"},
  "objects": [
    {"id": "G",   "kind": "graph", "vertices": ["b0", "b1", "v"], "edges": [{"id": "e0", "u": "b0", "v": "b1"}]},
    {"id": "B",   "kind": "c5.boundary_cycle", "graph": "G", "cycle": ["b0", "b1", "b2", "b3", "b4"]},
    {"id": "col", "kind": "coloring", "graph": "G", "values": {"b0": 1, "b1": 2}},
    {"id": "W",   "kind": "witness", "claim": "minor:K5", "of": "G", "data": {"branch_sets": [["v1", "v4"], ["v2"]]}},
    {"id": "T",   "kind": "transformation", "op": "reduction", "from": "G", "to": "G2", "map": {"v": "v'"}}
  ]
}
```

- **核心 kinds**（無前綴）：`graph`, `configuration`, `coloring`, `relation`, `witness`, `transformation`, `proof_step`, `certificate_ref`。
- **領域 kinds**（有前綴）：`c5.boundary_cycle`, `c5.spoke`, `c5.attachment`, `c5.palette`, `c5.relation`, `c5.extension_witness` …，由 domain pack 定義與驗證。
- 物件以 id 互相引用；子元素 id 以 `物件/元素` 表示（如 `G/e0`）。
- **只在有真實使用方時才新增 kind**。M1a 只實作 `graph`、`coloring` 與 `c5.boundary_cycle`，其餘列在此處作為方向，不預先實作。
- `evidence` 與 `provenance` 在這層決定，Scene 只原樣轉帶（見 INTEGRATION §3）。

### compile（Visual Compiler）
`compile_visual(doc: MathDocument, view: str = "default") -> Scene`

- 規則表：`kind → Rule`。Rule 把一個 IR 物件轉成 Scene 元素（nodes、edges、layers、layout 提示），並填 `origin`。
- 規則來源：通用規則（`graph`、`coloring`、`witness` 的 `branch_sets`）＋ domain pack 註冊的規則。
- 沒有規則的 kind：產生警告並略過，不失敗；`graph` 類物件至少以通用規則畫出。
- 同一份 IR 可有多個 view（例如 `default`、`kempe:1-3`、`minor`），由 CLI／檢視器選擇。

### scene（Scene IR）
只描述「畫什麼」；詞彙是視覺的，不是數學的。

```jsonc
{
  "schema": "mathkit.scene/1",
  "title": "record 87",
  "evidence": "computation",
  "provenance": {"source": "...", "sha256": "..."},
  "nodes":  [{"id": "n0", "label": "b_0", "class": "outer", "pos": null, "origin": ["G/b0", "B"]}],
  "edges":  [{"id": "s0", "u": "n0", "v": "n1", "class": "outer", "origin": ["G/e0"]}],
  "layers": [
    {"id": "coloring", "kind": "vertex-color", "values": {"n0": 1, "n1": 2}, "origin": ["col"]},
    {"id": "K5",       "kind": "partition",    "groups": [["n3", "n6"], ["n4"]], "origin": ["W"]}
  ],
  "layout": {"engine": "tutte", "outer": ["n0", "n1", "n2", "n3", "n4"]}
}
```

- `class` 是視覺類別（`outer`、`emphasis`、`muted`、`dashed`…），封閉列舉，由 renderer 對應樣式。
- `origin` 是 IR 物件／元素 id 的清單；renderer 忽略它，檢視器用它查 IR 顯示語義。
- `pos` 為 null 時由 `layout` 補上；有值時直接使用（手工擺位可重現）。
- `layers.kind` 是封閉列舉；新增需升 schema 小版本。
- 沒有 `meta` 自由欄位：領域資訊一律留在 IR，以 `origin` 連回。
- JSON Schema 由 Python 模型產生，放 `schemas/`（`ir.schema.json`、`scene.schema.json`），TS 型別由此生成。

### layout
| 引擎 | 用途 | 里程碑 |
| --- | --- | --- |
| `fixed` | 使用 Scene 自帶座標 | M1a |
| `circular` | 小圖、外圈正多邊形 | M1a |
| `tutte` | 平面圖、外圈固定，內點解線性系統；小圖用有理數精確解（§6） | M1b |
| `layered` | DAG（relation 蘊含、transformation 鏈、自動機） | M3 後 |

### render
- `svg`：手寫生成器（不依賴 matplotlib），CSS 變數控制色盤，支援深色模式。
- `tikz`：輸出 `tikzpicture` 片段，供 `math/paper/main.tex` `\input`。
- `json`：Scene 本身（給檢視器）。

### adapters
把「外部檔案」轉成 Math IR。

```python
class Adapter(Protocol):
    name: str
    def matches(self, path: Path, head: dict) -> bool: ...     # 只看檔頭
    def records(self, path: Path) -> Iterator[RecordRef]: ...  # 延遲、可分頁
    def document(self, ref: RecordRef) -> MathDocument: ...
```

內建 `generic_json`（未知格式 → 樹狀檢視）與 `edge_list`；研究專屬的放在 domain pack。

### domains（插件）
- 以 entry point `mathkit.domains` 註冊（ADR-0004）。一個 domain pack 可提供：
  - **計算原語**：例如 C5 boundary pattern、Σ 十位元編碼；
  - **IR kinds**：`c5.*` 的結構與驗證；
  - **adapters**：`math` artifacts → Math IR；
  - **視覺規則**：`c5.*` kinds 的 compile rules 與 views；
  - **checkers**：`mathkit check` 的獨立重算器。
- core、ir 基本型別、scene、layout、render 不 import 任何 domain。

### cli
`mathkit render | serve | check | validate | schema`。
`render` 接受 Math IR（走 compile）或 Scene JSON（直接 layout + render）。
`serve` 用標準庫 `http.server` + wheel 內的 viewer 靜態檔。

### viewer（TypeScript）
只讀 Scene（顯示）與 Math IR（點選元素時依 `origin` 顯示語義）；不含數學計算。build 產物打包進 wheel。

## 4. 資料流範例

`mathkit render math/artifacts/c5_k4_blocks/observations.json --record 3 --view default`

1. cli 讀檔頭 → adapter `matches()` → 選中 `c5.k4_blocks`
2. adapter 取第 3 筆 → Math IR（`graph`、`c5.boundary_cycle`、`coloring`…，含 provenance）
3. compile 依 kind 套規則 → Scene（`pos=null`、`origin` 已填）
4. layout 補座標 → render 輸出 SVG

`mathkit check <artifact>`：adapter → Math IR → domain checker 以 core 獨立重算 → 與 artifact 記錄值比對 → 差異報告（不改 artifact）。

## 5. 目錄

```
mathkit/
├── pyproject.toml
├── src/mathkit/
│   ├── core/        graph planar coloring kempe minor relation certificate
│   ├── ir/          Math IR：MathDocument、核心 kinds
│   ├── scene/       Scene IR
│   ├── compile/     Visual Compiler：規則註冊、通用規則
│   ├── layout/      fixed circular tutte layered
│   ├── render/      svg tikz
│   ├── adapters/    base generic_json edge_list
│   ├── domains/c5/  primitives ir_kinds adapters rules checkers
│   ├── cli.py
│   └── _viewer/     （build 產物，git 忽略）
├── viewer/          TypeScript 原始碼
├── schemas/         ir.schema.json · scene.schema.json（產生後提交）
├── tests/           unit · property · golden
├── examples/
└── docs/
```

## 6. 決定性契約（ADR-0006）

| 層級 | 保證 | 範圍 |
| --- | --- | --- |
| **語意決定性** | 同輸入 → 同 IR、同 Scene 拓撲、同 canonical 排序、同關係與 `origin` | 無條件；所有平台 |
| **序列化決定性** | 同輸入 → 位元組相同的 JSON／SVG／TikZ | 同 mathkit 版本、同 schema 版本、同 layout 版本 |

達成方式：

- 所有集合與 dict 輸出前排序；JSON 固定 `sort_keys`、縮排與換行。
- 座標經 **canonical quantization**：先正規化到固定 bounding box，再以整數網格（預設 1/10⁴）表示，輸出為整數或固定小數。
- Tutte：頂點數 ≤ 門檻（預設 64）時以 `fractions.Fraction` 精確解，量化時用 round-half-even，因此跨平台位元組一致；超過門檻才用 numpy 浮點，此時只保證語意決定性，輸出標註 `layout.exact: false`。
- 不寫入時間戳、主機名、絕對路徑。
- Golden 測試分兩類：語意 golden（比對正規化結構，全平台跑）與位元組 golden（比對 sha256，只驗 exact 路徑）。

## 7. 測試策略

| 層級 | 工具 | 內容 |
| --- | --- | --- |
| 單元 | pytest | core、compile rules、render 小例子 |
| 性質 | hypothesis | 著色合法、Kempe swap 保持合法、Tutte 嵌入無交叉、compile 的每個 Scene 元素都有有效 `origin` |
| 交叉 | pytest + networkx | 平面性、連通分量與 networkx 對照 |
| Golden | pytest | §6 兩類 golden |
| 相容 | `mathkit check` | 對 `math` artifacts 重算（本機執行，不進 CI） |
| 架構 | import-linter | §2 分層 |
