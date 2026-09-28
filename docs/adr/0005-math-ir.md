# ADR-0005：在 Scene 之前加入 Math IR 與 Visual Compiler

狀態：採用（2026-09-28）；修訂 [ADR-0001](0001-scene-protocol.md)

## 背景
原設計由 adapter 直接產出 Scene。Scene 只知道「有一條邊」，不知道它在數學上是 spoke、某個 reduction 保留的邊，還是 minor witness 的分支關係。要表達 `configuration →(reduction) configuration →(extension) witness` 這類鏈時，領域語義只能塞進 Scene 的 `role`／`meta`，renderer 會逐漸被迫理解 C5。

## 決定
- 新增 **Math IR**（`mathkit.ir/1`）：數學物件與其關係（`graph`、`configuration`、`coloring`、`relation`、`witness`、`transformation`、`proof_step`、`certificate_ref`；領域 kinds 以 `c5.` 等前綴）。
- 新增 **Visual Compiler**：`compile_visual(doc, view) -> Scene`，以 `kind → rule` 註冊表運作；領域規則由 domain pack 註冊。
- **Scene** 改為純視覺：`role` 改名 `class`（封閉的視覺詞彙），移除 `meta`，新增 `origin` 指回 IR id。
- `evidence`、`provenance` 在 IR 決定，Scene 原樣轉帶。
- IR kinds 只在有真實使用方時新增；M1a 只實作 `graph`、`coloring`、`c5.boundary_cycle`。

## 後果
- renderer 與 layout 永遠不接觸領域語義；語義也不會在進入 viewer 時消失（經 `origin` 可查回）。
- 同一份 IR 可編譯成多個 view（default、Kempe、minor）。
- IR 本身可存檔，作為比 Scene 更穩定的交換格式；`mathkit check` 也以 IR 為輸入。
- 代價：多一層模型與 schema；以「只按需新增 kind」控制膨脹。
