# 部署与运维参考

使用 [部署手册](../reference/server/docs/deployment.md) 中的独立二进制或Compose模板，源码链接固定到文档基线。Docker Hub目前的beta标签为 `syx0310/mlboard:beta`；标签可变，部署时记录实际digest和平台。

- 服务端支持SQLite或PostgreSQL，附件支持local/S3。Valkey是可选共享缓存，不是权限或持久摄取的替代品。
- 设置公开访问地址MLBOARD_PUBLIC_URL；LAN IP与反代场景参考 [LAN/反代](../reference/server/docs/lan-and-proxy.md)。示例地址和路径已泛化，不对应可直接访问的实例。
- HTTPS、代理源地址、SSE/WebSocket转发和读取期限需要与实际入口匹配。只信任配置的代理CIDR，不盲目信任客户端X-Forwarded-For。
- 用户修改实例设置后，持久设置优先于首次启动环境变量。读取期限、查询预算与上传/下载预算分别处理。
- 备份必须覆盖SQL、附件及settings.key等必要私密配置；恢复先在隔离环境验证。具体流程参考部署与存储手册，不能只复制活跃SQLite主文件。
- 跨平台构建保持CGO_ENABLED=0，说明所交付架构；见 [跨平台编译](../reference/server/docs/cross-compilation.md)。

[配置项](../reference/server/docs/configuration.md) · [存储/附件](../reference/server/docs/storage.md) · [Valkey与实时多实例](../reference/server/docs/realtime-cluster.md) · [实例管理](../reference/server/docs/admin.md)
