# viewer

TypeScript 靜態檢視器（M4）。以 `mathkit.scene/1` 顯示，點選元素時依 `origin` 查 `mathkit.ir/1` 顯示語義；不含數學計算。

預定技術：Vite + TypeScript + Cytoscape.js + KaTeX；型別由 `../schemas/scene.schema.json` 生成。
build 產物輸出到 `../src/mathkit/_viewer/`，隨 Python wheel 發佈，使用者不需要 Node。
