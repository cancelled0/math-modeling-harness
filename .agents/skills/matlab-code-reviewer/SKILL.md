---
name: matlab-code-reviewer
description: 审查并验证已批准的 MATLAB/北太天元建模代码、兼容性、结果契约和可复现证据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

检查算法映射、输入输出、单位、约束、划分、预处理、随机性、MATLAB/北太天元兼容性和执行收据，按 `workflow-orchestrator/assets/artifact-contracts.json` 的 code-review 契约输出 `code/matlab/Qx/reviews/qx_matlab_review.json`。不重新选方法；完成求解请求可修复机械错误并用新 run 重跑，语义变化交回运行器。
