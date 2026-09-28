# ADR-0004：領域語義以 entry-point 插件提供

狀態：採用（2026-09-28）

## 背景
第一個使用方是 C5 boundary-coloring 研究，但目標是可用於其他研究題目。

## 決定
`core`／`scene`／`layout`／`render` 不含領域語義。領域知識（C5 pattern、Σ 編碼、artifact adapter、`check` 重算器）以 `mathkit.domains` entry point 註冊。C5 pack 初期放在 `src/mathkit/domains/c5`，日後可拆為獨立套件而介面不變。

## 後果
- 以 import-linter 禁止 core 層 import `mathkit.domains`。
- 新研究題目只要寫一個插件。
