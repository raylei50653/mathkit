# ADR-0001：計算與呈現以 Scene JSON 分隔

狀態：採用（2026-09-28），由 [ADR-0005](0005-math-ir.md) 修訂：Scene 的輸入改為 Math IR 經 Visual Compiler 產生

## 背景
需要同時支援 SVG、TikZ、瀏覽器互動三種輸出，且引擎為 Python、檢視器為 TypeScript。

## 決定
引擎與 adapter 產出 `mathkit.scene/1` JSON；所有 renderer（含 TS 檢視器）只消費 Scene。Scene 描述「畫什麼」（節點、邊、角色、疊加層、provenance），不描述樣式細節。JSON Schema 為唯一跨語言契約。

## 後果
- 新增輸出格式只需新 renderer，不動引擎。
- Scene 可存檔、比對、放進 artifact，成為可重播的呈現。
- 代價：Scene 表達力受限於封閉的 layer kinds，新視覺概念需升 schema 小版本。
