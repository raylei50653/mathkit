# ADR-0002：對研究 repo 單向、唯讀、選擇性依賴

狀態：採用（2026-09-28）

## 背景
`math` 的可信度建立在決定性 artifacts、sha256 與可重播指令上。任何外部工具若修改這些檔案或成為建置必要條件，都會削弱重播鏈。

## 決定
- mathkit 不 import `math` 的程式碼，不寫入 `math` 的檔案。
- `math` 對 mathkit 的依賴一律選擇性（`uv run --with` 或 `try: import`）。
- C5 概念在 mathkit 內獨立重新實作，而非共用程式碼。

## 後果
- 獨立實作可作為交叉驗證（`mathkit check`），是額外收穫。
- 代價：概念重複實作；兩邊定義漂移時需以 `check` 偵測。
