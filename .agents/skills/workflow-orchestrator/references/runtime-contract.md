# Runtime revision 2 执行契约

manifest 的 schema_version 保持 1；runtime_revision 为 2。旧会话用 `workflow.py migrate` 保存历史快照并重新验证。现有产物不会仅因文件存在被自动接受。

本文件描述可执行字段和操作；公共政策统一见 [项目 AGENTS.md](../../../../AGENTS.md)。

## 调用和依赖

`start --question Qx --step ...` → 专业 Skill 生成真实产物 → `finish`。全局步骤用 GLOBAL；next 返回正确的负责人。所有声明的检查器必须执行，错误或未知检查阻止完成。

scope=global 的解析、分类、数据只做一次；全局引用、编译和审计等待全部问题的分节完成。depends_on 可引用 Q1:result-verdict；配置 question_dependencies={"Q2":["Q1"]} 表示 Q2 的方法筛选依赖 Q1 被接受的结果。循环依赖在初始化时拒绝。另一问等待人工判断时，可推进独立机械动作。

配置优先级：显式初始化参数 > session_config > profile 模板。运行记录固定解析配置和模板快照。配置改变后运行 reconfigure；只改论文格式保留模型，改变模型配置重验证上游。lean 可以升级为 submission。

deadline_at 是带时区 ISO 时间。research_budget_minutes 默认 30，paper_reserve_minutes 默认 180。检索到预算即记录缺口并交接；后续针对具体疑问补查。临近截止优先完成最低可用答案并保护写作时间，不能自动批准决定。

## 最小机器证据

| 产物 | 必需内容 |
|---|---|
| problem_parse.json | subquestions、material_ambiguities（无歧义为空列表）、题目引用放 input_files |
| problem_classification.json | subquestions |
| data_profile.json | data_mode、input_files、quality_findings；无数据时 no_data_reason |
| source_registry.json | sources；无外部来源时空列表及 reason |
| method_contract.json | main、usable_baseline、rationale、task_type、required_checks |
| qx_foundations.json | assumptions、symbols、preparation、derivations |
| run_summary.json | status、question_id、experiment_id、methods、comparison_contract、primary_metric、task_type、scientific_checks、random_seed、environment、execution |
| 代码审查 JSON | status、evidence_files、checks |
| 鲁棒性 JSON | status、evidence_files、findings、limitations |
| figure_manifest.json | status、figures、evidence_files；无图时 omission_reason |
| 审计 JSON | status=passed、evidence_files、unresolved=[]，与同名 Markdown 一致 |

预测检查 temporal_split、availability_time；优化检查 feasibility、constraint_residuals、solver_status；机理检查 units、identifiability；评价检查 weight_sensitivity；分类/回归检查 heldout_evaluation；仿真检查 replication_stability。每项 scientific_checks 为 `{status:"passed", evidence_files:[...]}`；其他题型由方法契约明确 required_checks。机器检查不能证明数学推导正确，代理仍需专业核对。

input_files、output_files、evidence_files、source_file、local_path 等显式路径递归登记内容哈希。输出、输入或依赖变化撤销下游允许动作，修改时间不能绕过。

## 决定和迭代

当前证据准备好后用 `decision-context --question Qx --step ...` 获取 evidence_hashes。用户实际答复的 JSONL 包含 decision_id、decision_type、decided_by=human、status=DECIDED、user_message（真实答复或会话消息引用）、decided_at、choice、evidence_hashes；结果决定另含 experiment_id。

- framing_choice、method_choice、package_signoff 使用 choice=accept；selected_method 记录具体方法并与契约一致。
- result_verdict 使用 accept/adjust/reject/fallback；调整记录 diagnosis（data/feature/method/parameter/implementation/metric）和 rerun_from，用户未说明理由时 rationale 为 null。更换方法回到方法筛选和确认。

人工决定与 AI 分析的区分遵循项目 AGENTS.md「自动推进与人工判断」。

`rerun --from-step ... --new-experiment` 新建运行目录并保留旧实验。Git 的接受/拒绝必须验证实际账本和实验绑定。冻结证据改变需记录解冻并重新冻结；纯排版不重跑模型。

## 展示和交付

运行 → 审查 → 结果分析 → 鲁棒性 → [求解过程展示](../../modeling-results-presenter/SKILL.md) → 用户结果判断 → 方法解释 → 冻结 → 图表 → 分节初稿 → 润色 → 全局引用 → 编译/导出 → 视觉检查 → 三层审计。

展示稿 presentation.json/MD 中的数字绑定真实文件和 JSON 定位；先展示内容，后请用户判断。初稿写 paper/drafts，润色写 paper/sections，避免修改上游已验证文件。Word/Overleaf 改动回到本地权威源后重跑受影响写作与编译；数值声明改变另行解冻。

paper/visual_review.json 的 files 映射覆盖 main.pdf 及需要的 DOCX。每项包括 sha256、status=passed、reviewer、reviewed_at、page_count、pages_reviewed（全部页面）、checks（equations/figures/citations/pagination/contest_format 均 true）。实际逐页核对后才可写 passed。结构检查 visual_check_pending 允许进入视觉核验，但不能通过 G6。

export 只接受当前完整通过的会话，包含来源注册表、清洗/特征和论文，排除原始数据与缓存。--overleaf 只打包 TeX、引用和资源，main.tex 位于包根。交付前在干净临时目录编译该包。
