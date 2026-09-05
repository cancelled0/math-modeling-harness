# 可执行科学证据

预测、回归、分类的 run_summary 保存 split.strategy、preprocessing.fit_scope 和 evaluation_audit_file。审计文件由实际划分与拟合过程导出：

```json
{"folds":[{"train_ids":[0,1],"evaluation_ids":[2],"preprocessing_fit_ids":[0,1]}]}
```

没有学习型预处理时改用 `preprocessing: "none"` 与具体 no_preprocessing_reason。程序检查非空、ID 唯一、训练与评估无交集、拟合范围包含于训练集。ID 标识原始样本，不得各划分重新编号。

时间序列每折另保存 target_times（训练与评估行）、prediction_origins、feature_available_at（评估行），键为行 ID 字符串，值为统一时间标准的 ISO 时间。feature_available_at 是实际使用输入中最晚可用时间。程序检查训练目标早于评估目标，特征在预测起点可用且起点早于目标。滚动预测逐折保存。

优化任务保存 constraint_audit_file，含 constraint_labels、violations（逐条非负违反量）、tolerance。违反量由最终解代回原约束计算。程序检查数量、有限性、非负性及容差。

其余 scientific_checks 标明 verification_mode 为 computed、model_review 或 human_review。审查型附 reviewer、rationale；computed 的 evidence_files 保存实际计算依据。结构核验不代表程序证明了单位、可辨识性或自然语言论证，报告应如实注明验证方式。
