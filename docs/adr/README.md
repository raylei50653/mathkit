# 架構決策紀錄（ADR）

一個決定一份；狀態為 提議／採用／取代／否決。取代時不刪舊檔，改狀態並連到新檔。

| # | 決定 | 狀態 |
| --- | --- | --- |
| [0001](0001-scene-protocol.md) | 計算與呈現以 Scene JSON 分隔 | 採用 |
| [0002](0002-non-invasive-integration.md) | 對研究 repo 單向、唯讀、選擇性依賴 | 採用 |
| [0003](0003-python-first.md) | Python 優先，Rust 僅在 profiling 證明必要後引入 | 採用 |
| [0004](0004-domain-plugins.md) | 領域語義以 entry-point 插件提供 | 採用 |
