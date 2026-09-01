---
name: latex-paper-zh
description: 组装、编译和交付检查中文数学建模 LaTeX 论文。用于冻结结果和论文分节完成后的 CUMCM 中文 TeX/PDF 路径；不负责重新选择模型或改写未获批准的数值声明。
---

# 中文数模 LaTeX 交付

从冻结写作包、`paper/sections/*.tex`、验证图表和可追溯参考文献组装中文论文。普通模板可从 `assets/cumcm-template/` 复制；比赛提供官方模板时以官方模板为准，不擅自改变版式要求。

## 前置条件

- G4 已通过，`frozen_numbers.json` 当前有效。
- 中文论文分节、图表和参考文献已准备。
- `reference-manager` 已核对引用。

## 工作流

1. 检查 `xelatex`、`latexmk` 或兼容引擎和所需字体；未在 PATH 中时可用 `MODELING_TEX_BIN` 指向二进制目录。可执行文件缺失或 MiKTeX 尚未初始化时输出 `unavailable`，不得声称编译成功。
2. 组装 `paper/main.tex`，保持数字、符号、图表路径和引用键不变。
3. 使用 `scripts/compile_latex.py` 编译，保存机器可读报告。
4. 使用 `scripts/check_latex_delivery.py` 检查 PDF、未定义引用、严重溢出和失败日志。
5. 对最终 PDF 执行页面渲染核对，再交给三层审计。

## 规则

- 中文优先 XeLaTeX；不使用英文 `latex-paper-en` 代替中文模板职责。
- 不从探索目录补写论文数字，不改变冻结声明。
- 编译器不可用时可保留完整 TeX 交付，并将 Word 标记为备选；切换交付格式由配置或用户决定。

## 输出

- `paper/main.tex`
- `paper/main.pdf`（编译成功时）
- `paper/latex_build_report.json`
- `paper/latex_delivery_check.json`

完成后交给 `consistency-auditor`。
