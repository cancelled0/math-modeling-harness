---
name: matlab-model-code-generator
description: 按已批准的方法契约生成并运行 MATLAB/北太天元实现，保存可追溯的结果摘要和执行收据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

从问题契约、方法契约、foundations、数据概况和 Git 实验上下文读取输入；复杂任务可读取可选 `implementation_spec.json`。不在此阶段选方法或创建额外人工检查点。

结果摘要必须符合 `workflow-orchestrator/assets/artifact-contracts.json`，包含 primary result、main/reference 角色（若适用）、必要科学检查、环境、种子和 receipt。运行后交 `matlab-code-reviewer`；实现、参数或数据变更使用新 run ID。
