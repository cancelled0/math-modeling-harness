# 数学建模竞赛 Harness

这是一套面向数学建模竞赛的项目级 Codex Harness。它以文件型状态机组织题目理解、学术证据扫描、数据处理、方法讨论与确认、代码实验、结果评估、论文写作和交付审计，同时保留人在关键建模判断中的决定权。

## 使用范围

仓库只包含 Harness 本身：

- `AGENTS.md`：项目公共规则；
- `.agents/skills/`：总入口、状态机、专业 Skills、检查脚本、模板和路由测试；
- `docs/harness-flowcharts/`：主流程和方法路由图；
- `.gitignore`、`.gitattributes`：项目仓库配置。

仓库不包含往年论文、赛题归档、比赛数据、实际比赛工作区、模型结果、临时文件或本机凭据。

## 安装

将仓库克隆为一个新的数学建模项目根目录：

```powershell
git clone <repository-url> math-modeling
cd math-modeling
```

也可以只把 `AGENTS.md`、`.agents/` 和 `docs/` 复制到已有的数学建模项目根目录。项目级 Skills 只在该目录及其子目录中的任务里可见。

Windows 环境优先使用 PowerShell 7。完整功能建议准备 Python 与 Git；中文 LaTeX/PDF/DOCX 交付还需要 XeLaTeX/latexmk、Pandoc 和适用字体。MATLAB 路径仅在用户指定 MATLAB、北太天元或已有 `.m` 工程时使用。

## 主要入口

- `math-modeling-manager`：完整赛题、跨阶段任务和既有任务续作的统一入口；
- `modeling-thought-partner`：自由讨论、推导和评价建模思路，不推进阶段门；
- `workflow-orchestrator`：读取 manifest、检查阶段门并选择一个下一动作；
- `paper-section-writer` 与 `latex-paper-zh`：数学建模论文写作、中文 LaTeX、PDF 和 DOCX 镜像交付。

完整 submission 流程概括为：

```text
题目解析与分类
→ 有边界的论文/数据证据扫描
→ 数据审计与特征工程
→ 方法筛选、自由讨论与人工确认
→ Git 实验分支、代码实现与审查
→ 基线比较、鲁棒性与误差分析
→ 求解过程和结果展示
→ 人工结果判断、方法解释与数值冻结
→ 数模论文写作、引用核验和 LaTeX 交付
→ 完整性、一致性与提交质量审计
```

详细流程见 [Harness 流程图](docs/harness-flowcharts/README.md)。

## 自检

在仓库根目录运行统一路由审计：

```powershell
python .agents/skills/math-modeling-manager/scripts/audit_skill_routes.py
```

状态机测试位于 `.agents/skills/workflow-orchestrator/evals/`，各专业 Skill 的测试或评估样例位于其自身的 `evals/` 目录。

## 协作建议

建议通过分支和 Pull Request 修改 Harness。提交建议时请说明触发场景、变更的输入输出契约、对阶段门的影响以及已运行的测试。公共规则集中修改 `AGENTS.md`；专业知识、操作步骤和局部检查放在对应 Skill 中，避免维护相互冲突的规则副本。

部分 Skills 来源于或改编自外部项目。公开分发或再许可前，请逐项核对其原始许可证和署名要求。
