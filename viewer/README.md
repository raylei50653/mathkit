# viewer

TypeScript 靜態檢視器（M4）。只讀 `mathkit.scene/1` JSON，不含數學邏輯。

預定技術：Vite + TypeScript + Cytoscape.js + KaTeX；型別由 `../schemas/scene.schema.json` 生成。
build 產物輸出到 `../src/mathkit/_viewer/`，隨 Python wheel 發佈，使用者不需要 Node。
