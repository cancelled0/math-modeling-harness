---
name: model-code-analyzer
description: 将已批准的方法、数据和模型基础转成可执行的实现契约；只在复杂任务或配置要求时运行。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

简单任务直接使用 `method_contract.json` 和 foundations。复杂、多模块、多语言、强约束或高风险任务才生成 `code/Qx/qx_implementation_spec.json`（MATLAB 放在 `code/matlab/Qx/`），字段遵循统一 artifact contract，至少记录模块、输入、输出、算法步骤、参数、检查和复现命令。

不扩张候选方法、不引入未经批准的 reference、不生成第二套结果契约；实现后交对应语言 reviewer。
