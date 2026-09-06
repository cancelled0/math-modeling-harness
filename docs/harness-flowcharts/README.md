# 数学建模 Harness 流程图

本目录保存当前 Harness 的可编辑 Mermaid 源文件和渲染结果。

- `harness-main-flow.mmd`：完整建模状态机、人工判断、Git 实验和论文交付流程。
- `method-routing-flow.mmd`：方法族到专业 Skills 的路由图。
- `harness-main-flow.svg` / `.png`：完整流程图渲染结果。
- `method-routing-flow.svg` / `.png`：方法路由图渲染结果。
- `mermaid-config.json`：渲染配置。
- `puppeteer-config.json`：使用本机 Microsoft Edge 的无头渲染配置。

图中红色节点是四类必须由用户确认的判断点，蓝色节点是阶段门，绿色节点是 Git 操作。修改 `.mmd` 后应重新生成 SVG 和 PNG，确保图片与源文件同步。

## 预览

![完整 Harness 流程图](harness-main-flow.png)

![方法路由流程图](method-routing-flow.png)
