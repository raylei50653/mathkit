# ADR-0006：決定性分為語意與序列化兩層；小圖 layout 以有理數精確解

狀態：採用（2026-09-28）

## 背景
原契約是「相同輸入 → 位元組相同輸出」。但 Tutte layout 經浮點線性系統求解，跨 Python／NumPy／BLAS／CPU 時，恰好落在捨入邊界的值（如 `0.123454999…` 對 `0.123455000…`）可能得出不同的最後一位，使這個保證無法兌現。

## 決定
1. **語意決定性**（無條件）：同輸入 → 同 IR、同 Scene 拓撲、同 canonical 排序、同關係與 `origin`。
2. **序列化決定性**（有條件）：同 mathkit／schema／layout 版本下，位元組相同。
3. 座標採 canonical quantization：正規化至固定 bounding box 後以整數網格表示。
4. Tutte 可行時以 `fractions.Fraction` 精確求解，再以 round-half-even 量化，因此跨平台位元組一致；否則用 numpy 浮點，只保證語意決定性。Scene 以 `layout.exact` 標明走哪一條。
5. **契約**只綁 `layout.exact` 旗標，不綁圖的大小。何時走 exact 是實作門檻：初始規劃值為內部未知數 ≤ 64，之後可改依係數／分母成長或計算預算判斷，也可改用 Bareiss 等 fraction-free elimination。門檻變更需升 layout 版本；選擇本身必須決定性。

## 後果
- 位元組 golden 只驗 exact 路徑；語意 golden 全平台跑。
- 精確解為 O(n³) 有理數運算，分母可能膨脹；以可調門檻與 fraction-free elimination 控制。研究中的圖幾乎都遠小於初始門檻。
- layout 演算法變更必須升 layout 版本號。
