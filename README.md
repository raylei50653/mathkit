# mathkit

為數學研究專案提供**計算引擎**與**視覺化**的外掛式工具包。
以「導入」方式使用：研究 repo 不需改結構、不需把程式碼複製進來，
只在需要時 `uv run --with` 或 `import mathkit`。

第一個使用方是同層的 [`../math`](../math)（C5 boundary-coloring／Lean 4 形式化），
但核心不含任何 C5 專屬語義；C5 相關知識放在可拔除的 domain pack。

```
adapter → Math IR（數學意義）→ Visual Compiler → Scene（純視覺）→ layout → SVG／TikZ／Viewer
```

> 狀態：**M1a 完成**。`mathkit render` 可把 Math IR／Scene 轉成決定性 SVG 或 Scene JSON；下一步 M1b 平面引擎。

## 文件

| 文件 | 內容 |
| --- | --- |
| [專案規劃](docs/PLAN.md) | 目標、非目標、使用情境、里程碑、成功指標、風險 |
| [架構](docs/ARCHITECTURE.md) | 雙引擎、分層、Math IR → Visual Compiler → Scene、插件機制、決定性契約 |
| [技術棧](docs/TECH_STACK.md) | 選型、理由與被否決的替代方案 |
| [整合契約](docs/INTEGRATION.md) | 與 `math` repo 的邊界：讀什麼、不碰什麼、如何導入 |
| [架構決策紀錄](docs/adr/) | ADR，每個不可輕易反悔的決定一份 |

## 用法

```bash
# 在 math repo 內，不安裝、不改 pyproject
uv run --with ../mathkit mathkit render artifacts/c5_k4_blocks/observations.json -o /tmp/k4.svg
uv run --with ../mathkit mathkit render ../mathkit/examples/c5.ir.json -o /tmp/c5.svg   # 可用（M1a）
uv run --with ../mathkit mathkit render ../mathkit/examples/c5.ir.json -o /tmp/c5.scene.json  # Scene JSON
uv run --with ../mathkit mathkit serve artifacts/          # 本機瀏覽器檢視（M4）
```

```python
# 在 math 的腳本中選擇性使用；沒裝 mathkit 時腳本照常運作
try:
    from mathkit.core import coloring
except ImportError:
    coloring = None
```

## 開發

```bash
uv sync
uv run pytest
uv run ruff check . && uv run pyright && uv run lint-imports
uv run mathkit schema --out-dir schemas               # 模型改動後重生 schema
MATHKIT_UPDATE_GOLDEN=1 uv run pytest tests/test_cli.py  # 刻意改變輸出後重生 golden
```

授權：Apache-2.0（與 `math` 一致）。
