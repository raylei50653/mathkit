# ADR-0003：Python 優先，Rust 僅在 profiling 證明必要後引入

狀態：採用（2026-09-28）

## 背景
窮舉型計算可能遇到效能瓶頸；Rust + PyO3 能大幅加速，但會增加建置複雜度（需 maturin、跨平台 wheel）。

## 決定
M1–M4 全部以 Python（bitmask + numpy）實作。引入 Rust 的條件：
1. 有真實使用情境的 profiling 顯示單一 core 函式佔 > 50% 時間；且
2. 演算法層面的改進已嘗試過。

引入時以 `mathkit._native` 提供同名函式，Python 版保留為參照實作與測試對照。

## 後果
- 初期建置簡單，純 Python wheel。
- core API 設計需避免 Python 專屬物件穿過熱點邊界（用 int bitmask、tuple），以便日後替換。
