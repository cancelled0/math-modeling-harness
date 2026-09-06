---
name: latex-paper-zh
description: 组装、编译和交付检查中文数学建模 LaTeX 论文，并可从权威 TeX 派生可追溯 DOCX 镜像。用于冻结结果和论文分节完成后的 CUMCM 中文 TeX/PDF/Word 双交付路径；不负责重新选择模型或改写未获批准的数值声明。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# 中文数模 LaTeX 交付

从冻结写作包、`paper/sections/*.tex`、验证图表和可追溯参考文献组装中文论文。普通模板可从 `assets/cumcm-template/` 复制；比赛提供官方模板时以官方模板为准，不擅自改变版式要求。默认以 `paper/main.tex` 为唯一权威源，DOCX 是从该版本生成的派生镜像。

## 前置条件

- G4 已通过，`frozen_numbers.json` 当前有效。
- 中文论文分节、图表和参考文献已准备。
- `reference-manager` 已核对引用。

## 工作流

1. 检查 `xelatex`、`latexmk` 或兼容引擎和所需字体；双交付时同时检查 Pandoc。未在 PATH 中时可用 `MODELING_TEX_BIN` 指向 TeX 二进制目录，用 `MODELING_PANDOC` 指向 Pandoc 可执行文件或目录。能力缺失或 MiKTeX 尚未初始化时输出 `unavailable`，不得声称成功。
2. 组装 `paper/main.tex`，保持数字、符号、图表路径和引用键不变。
3. 使用 `scripts/compile_latex.py` 编译，保存机器可读报告。
4. 使用 `scripts/check_latex_delivery.py` 检查 PDF、未定义引用、严重溢出和失败日志。
5. 对最终 PDF 执行页面渲染核对。
6. 若配置为 `latex_primary_docx_mirror`，只有 LaTeX 构建和冻结状态当前有效时，才运行 `scripts/export_docx.py paper/main.tex --output paper/exports/main.docx --report paper/docx_export_report.json`。需要统一 Word 样式时传入受版本控制的 `--reference-doc`。
7. 运行 `scripts/check_docx_delivery.py paper/exports/main.docx --source-tex paper/main.tex --export-report paper/docx_export_report.json --report paper/docx_delivery_check.json`，校验 OOXML 结构、内容非空以及来源/输出哈希。
8. 使用文档渲染能力逐页检查 DOCX。若 LibreOffice 等渲染器不可用，只能记录 `passed_with_visual_check_pending`，不得称最终 Word 视觉检查通过。
9. PDF 和可选 DOCX 一起交给三层审计，核对正文、公式、图表、引用和冻结数字没有跨格式漂移。

## 双交付与 Overleaf 规则

- `paper/main.tex`、分节、BibTeX、图件、类文件和样式文件构成可上传 Overleaf 的权威源码包。
- Pandoc 不保证复刻复杂 LaTeX 宏、浮动体和版式；DOCX 的角色是审阅/提交镜像，不取代 PDF 排版判断。
- 不自动把 Word 修改反向合并到 TeX。人工在 Word 中提出的改动应形成差异清单，回写到 `.tex`，重新编译并重新导出。
- 人工在 Overleaf 修改后，先把相同源文件同步回本地仓库并提交 Git，再重新生成两种交付物。来源哈希不一致时将 DOCX 判为 stale。

## 规则

- 中文优先 XeLaTeX；不使用英文 `latex-paper-en` 代替中文模板职责。
- 不从探索目录补写论文数字，不改变冻结声明。
- 编译器或 Pandoc 不可用时保留完整 TeX 与真实失败报告；切换为 Word 主格式必须由配置或用户决定，不能用旧 DOCX 冒充当前镜像。

## 输出

- `paper/main.tex`
- `paper/main.pdf`（编译成功时）
- `paper/latex_build_report.json`
- `paper/latex_delivery_check.json`
- `paper/exports/main.docx`（双交付模式且导出成功时）
- `paper/docx_export_report.json`（含 TeX/DOCX 哈希和工具版本）
- `paper/docx_delivery_check.json`

完成后交给 `consistency-auditor`。
