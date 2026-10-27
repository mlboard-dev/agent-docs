# 训练接入

典型顺序：已有项目与训练 key → 跑小规模验证 → 检查远端完成 → 接入训练循环。

[SDK 示例](../examples/train.py) 记录10个明确标记的合成点，默认使用独立 Run 路径。用户授权验证接入后才能运行；生产训练时换成真实 CPU 标量，不在日志热路径中隐式做 tensor.item()/cpu()/numpy()。

关键约定：

- `sync="background"` 开启持续上传；只给 server 仍然是本地记录。
- `run_path` 是分类路径，不是本地文件路径。project 优先稳定 ID；需要创建项目时显式 create_project=True，并使用有 projects:write 的 global key 与正确 organization。
- `log().accepted` 只表示进入有界内存队列。`finish(wait_for="local")` 确认本地落盘，`finish(wait_for="remote")` 还确认服务端 ACK 与终态。
- 检查 finish.complete、dropped 和 reason。超时不等于上传完成；保留本地 spool 以供恢复。
- 每次 log 可使用自己的 Step；epoch、wall_time、elapsed_seconds、session_elapsed_seconds、processed_samples 各有原始语义。
- 每条 series 由指标名称与完整 context 区分。无 Step 的合法文本/表格/媒体可按时间轴读取。
- 断网恢复、同Run多session、DDP多producer必须使用SDK的身份规则，不手工重用同一事件身份写不同内容。
- 模型 config 大整数与精确小数使用 SDK 的 config_json / Decimal 支持；普通 float 已丢失的精度无法恢复。

完整资料：[SDK](../reference/py-client/docs/sdk.md)、[同步与 key](../reference/py-client/docs/sync-and-keys.md)、[存储与恢复](../reference/py-client/docs/storage-and-recovery.md)、[本地查看器](../reference/py-client/docs/local-viewer.md)、[TensorBoard 导入](../reference/py-client/docs/tensorboard.md)。
