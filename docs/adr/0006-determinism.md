# ADR-0006：決定性分為語意與序列化兩層；小圖 layout 以有理數精確解

狀態：採用（2026-09-28）

## 背景
原契約是「相同輸入 → 位元組相同輸出」。但 Tutte layout 經浮點線性系統求解，跨 Python／NumPy／BLAS／CPU 時，恰好落在捨入邊界的值（如 `0.123454999…` 對 `0.123455000…`）可能得出不同的最後一位，使這個保證無法兌現。

## 決定
1. **語意決定性**（無條件）：同輸入 → 同 IR、同 Scene 拓撲、同 canonical 排序、同關係與 `origin`。
2. **序列化決定性**（有條件）：同 mathkit／schema／layout 版本下，位元組相同。
3. 座標採 canonical quantization：正規化至固定 bounding box 後以整數網格表示。
4. Tutte 對頂點數 ≤ 64 的圖以 `fractions.Fraction` 精確求解，再以 round-half-even 量化，因此跨平台位元組一致。研究中的圖幾乎都在此範圍內。
5. 超過門檻時用 numpy 浮點，只保證語意決定性，Scene 標註 `layout.exact: false`。

## 後果
- 位元組 golden 只驗 exact 路徑；語意 golden 全平台跑。
- 精確解為 O(n³) 有理數運算，n ≤ 64 時成本可接受；門檻可調。
- layout 演算法變更必須升 layout 版本號。
