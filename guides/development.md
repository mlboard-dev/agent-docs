# 开发参考

产品源码独立维护于 [server](https://github.com/mlboard-dev/server)、[py-client](https://github.com/mlboard-dev/py-client)、[ios](https://github.com/mlboard-dev/ios)。本仓库只保存使用指南、协议示例与文档快照，不替代源码仓库工作约定。

- 服务端/Web：先读 [API契约](../reference/server/docs/api-contract.md)、[Web说明](../reference/server/docs/web.md)、[图表类型](../reference/server/docs/charts.md)、[字段/选集连续性](../reference/server/docs/frontend-analysis-continuity.md)。修改协议须同时考虑生产schema、HTTP/MCP、Web和客户端。
- Python：参考 [开发与测试](../reference/py-client/docs/development-and-testing.md)、[持久化](../reference/py-client/docs/storage-and-recovery.md)；不要把本地history/outbox与中心数据库混用。
- iOS：参考 [原生开发](../reference/ios/docs/development.md)、[验证说明](../reference/ios/docs/verification.md)、[Following](../reference/ios/docs/following.md)、[移动API](../reference/server/docs/mobile-api.md)。真机APNs/签名与模拟测试必须区分。
- UI操作应保留选集、坐标、草稿版本及当前读取边界。已有视图持久化与浏览器临时偏好不是同一层。

修改产品代码时先读取相应仓库的AGENTS.md与已有计划，保留用户现有未提交工作。在约定目录放工具链、缓存和测试产物；与本仓库文档同步是独立步骤。协议变化后更新source-lock.json并执行 [来源说明](../SOURCES.md) 的同步/校验流程。
