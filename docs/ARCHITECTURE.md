# 架構

## 1. 設計原則

1. **依賴單向**：研究 repo →（可選）mathkit。mathkit 永不 import 研究 repo 的程式碼。
2. **核心無領域語義**：`core`、`scene`、`layout`、`render` 不知道 C5 是什麼；C5 只存在於 `domains/c5`。
3. **計算與呈現以資料分隔**：引擎產出物件 → adapter 轉成 **Scene JSON** → renderer 只吃 Scene。Python 與 TypeScript 檢視器之間唯一的契約是 Scene 的 JSON Schema。
4. **決定性**：相同輸入 → 位元組相同的輸出（排序、浮點格式、無時間戳）。這與 `math` 的 artifact 慣例一致，讓輸出能被 sha256 釘住。
5. **小依賴面**：核心只依賴 Python 標準庫 + numpy；其他以 extras 提供。

## 2. 分層

```
┌──────────────────────────────────────────────────────────────┐
│  使用方：math/scripts、筆記、論文建置、瀏覽器                 │
└───────────────┬───────────────────────────────┬──────────────┘
                │ import / CLI                  │ HTTP (本機)
┌───────────────▼──────────────┐   ┌────────────▼──────────────┐
│ cli  (render/serve/check/     │   │ viewer/ (TS, 靜態頁)       │
│       validate)               │   │  只讀 Scene JSON           │
└───┬───────────┬──────────┬───┘   └────────────▲──────────────┘
    │           │          │                    │ Scene JSON
┌───▼────┐ ┌────▼─────┐ ┌──▼──────────────┐     │
│adapters│ │ domains/ │ │ render          │─────┘
│(讀外部 │ │  c5 ...  │ │ svg / tikz /json│
│ 檔案)  │ │ (插件)   │ └──▲──────────────┘
└───┬────┘ └────┬─────┘    │
    │           │     ┌────┴─────┐
    │           │     │ layout   │ tutte / circular / fixed
    │           │     └────▲─────┘
    │      ┌────▼──────────┴──┐
    └─────►│ scene (資料模型)  │
           └────▲─────────────┘
           ┌────┴─────────────────────────────────────────┐
           │ core: graph · planar · coloring · kempe ·     │
           │       minor · relation · certificate          │
           └───────────────────────────────────────────────┘
```

箭頭方向是「依賴」：上層可依賴下層，下層不得 import 上層。以 `import-linter` 在 CI 強制執行。

## 3. 模組職責

### core（引擎）
| 模組 | 職責 | 關鍵介面（草案） |
| --- | --- | --- |
| `graph` | 不可變小圖；頂點為 `0..n-1`，鄰接為 int bitmask；可附標籤 | `Graph.from_edges`, `.to_networkx()`, `.induced(mask)` |
| `planar` | 平面性、rotation system、面列舉、外圈 | `embed(g) -> Embedding \| KuratowskiWitness` |
| `coloring` | proper／list coloring、列舉所有擴張、色置換正規化 | `extensions(g, lists, fixed) -> Iterator[Coloring]` |
| `kempe` | 兩色子圖分量、swap、Kempe 等價類 | `chains(g, col, a, b)`, `swap(col, chain)` |
| `minor` | K5／K3,3 minor 的分支集**驗證**；搜尋為輔 | `check_minor(g, branch_sets, H) -> Verdict` |
| `relation` | 有限 port 上的 pattern relation：交、投影、條件化 | `Relation.condition(literals)`, `.project(ports)` |
| `certificate` | 輸入 sha256、決定性 JSON、replay 描述 | `fingerprint(paths)`, `dump(obj, path)` |

所有 core 函式是純函式或只回傳新物件；不讀寫檔案（`certificate.dump` 除外）。

### scene（視覺化協定）
與 renderer 無關的描述：「畫什麼」，不是「怎麼畫」。

```jsonc
{
  "schema": "mathkit.scene/1",
  "title": "record 87",
  "evidence": "computation",          // computation | paper | lean
  "provenance": {"source": "artifacts/...json", "sha256": "..."},
  "nodes":  [{"id": "b0", "role": "boundary", "label": "b_0", "pos": null}],
  "edges":  [{"id": "e0", "u": "b0", "v": "b1", "role": "frame"}],
  "layers": [                          // 可切換的疊加層
    {"id": "coloring", "kind": "vertex-color", "values": {"b0": 1, "b1": 2}},
    {"id": "kempe-13", "kind": "highlight", "edges": ["e3", "e7"]},
    {"id": "K5",       "kind": "partition", "groups": [["v1","v4"], ["v2"]]}
  ],
  "layout": {"engine": "tutte", "outer": ["b0","b1","b2","b3","b4"]},
  "meta": {}                           // domain pack 自由欄位，renderer 忽略
}
```

- `pos` 為 null 時由 `layout` 補上；有值時 renderer 直接用（讓手工擺位可重現）。
- `layers` 的 `kind` 是封閉列舉；新增 kind 需升 schema 小版本。
- JSON Schema 由 Python 模型產生，放 `schemas/scene.schema.json`，TS 型別再由它生成。

### layout
| 引擎 | 用途 |
| --- | --- |
| `tutte` | 平面圖、固定外圈（boundary cycle 放正 k 邊形），解線性系統；結果決定性 |
| `circular` | 小圖、關係圖 |
| `layered` | DAG（relation 蘊含、自動機），可交給 `dot` 或自實作 Sugiyama |
| `fixed` | 使用 Scene 自帶座標 |

座標四捨五入到固定小數位再輸出，避免跨平台浮點差異破壞決定性。

### render
- `svg`：手寫生成器（不依賴 matplotlib），CSS 變數控制色盤，支援深色模式。
- `tikz`：輸出 `tikzpicture` 片段，色盤對應 `\definecolor`，供 `math/paper/main.tex` `\input`。
- `json`：Scene 本身（給檢視器）。

### adapters
把「外部檔案」轉成 core 物件或 Scene。每個 adapter 宣告：
```python
class Adapter(Protocol):
    name: str
    def matches(self, path: Path, head: dict) -> bool: ...   # 只看檔頭，便宜
    def records(self, path: Path) -> Iterator[RecordRef]: ...  # 延遲、可分頁
    def scene(self, ref: RecordRef) -> Scene: ...
```
內建 `generic_json`（任何 JSON 的樹檢視）與 `edge_list`；研究專屬的放在 domain pack。

### domains（插件）
- 透過 Python entry points 註冊：`[project.entry-points."mathkit.domains"] c5 = "mathkit.domains.c5:plugin"`。
- 插件可提供：adapters、額外 core 原語（例如 C5 boundary pattern、Σ 十位元編碼）、色盤、`check` 重算器。
- core 不 import 任何 domain；CLI 啟動時由 entry points 發現。
- 日後若 domain pack 變大，可獨立成 `mathkit-c5` 發佈，介面不變。

### cli
`mathkit render | serve | check | validate | schema`。`serve` 用標準庫 `http.server` + 預先 build 好的 viewer 靜態檔，不需要 Node 執行期。

### viewer（TypeScript）
- 只讀 Scene JSON；不含任何數學邏輯（計算都在 Python）。
- build 產物打包進 Python wheel（`mathkit/_viewer/`），使用者不需要裝 Node。

## 4. 資料流範例

`mathkit render math/artifacts/c5_k4_blocks/observations.json --record 3`

1. cli 讀檔頭 → 各 adapter `matches()` → 選中 `c5.k4_blocks`
2. adapter 取第 3 筆 → 用 `core.graph` 建圖、`domains.c5` 解讀 lists
3. 組 Scene（nodes/edges/layers，`pos=null`）
4. `layout.tutte` 以 boundary 為外圈補座標
5. `render.svg` 輸出；provenance 記錄來源 sha256

`mathkit check <artifact>`：adapter 取出輸入 → 用 mathkit 獨立重算 → 與 artifact 記錄值比對 → 輸出差異報告（不改 artifact）。

## 5. 目錄

```
mathkit/
├── pyproject.toml
├── src/mathkit/
│   ├── core/        graph planar coloring kempe minor relation certificate
│   ├── scene/       model.py（Scene 資料類別）· schema 產生
│   ├── layout/      tutte circular layered fixed
│   ├── render/      svg tikz
│   ├── adapters/    base generic_json edge_list
│   ├── domains/c5/  pattern relation adapters check
│   ├── cli.py
│   └── _viewer/     （build 產物，git 忽略）
├── viewer/          TypeScript 原始碼
├── schemas/         scene.schema.json（產生後提交）
├── tests/           unit · property · golden
├── examples/
└── docs/            PLAN ARCHITECTURE TECH_STACK INTEGRATION adr/
```

## 6. 測試策略

| 層級 | 工具 | 內容 |
| --- | --- | --- |
| 單元 | pytest | 每個 core 函式的小例子 |
| 性質 | hypothesis | 隨機小圖：著色合法、Kempe swap 後仍合法、Tutte 嵌入無交叉 |
| 交叉 | pytest + networkx | 平面性、連通分量與 networkx 對照 |
| Golden | pytest | render 輸出 sha256 固定 |
| 相容 | `mathkit check` | 對 `math` artifacts 重算（M3 起，本機執行，不進 CI 以免依賴外部 repo） |
| 架構 | import-linter | 層級依賴方向 |
