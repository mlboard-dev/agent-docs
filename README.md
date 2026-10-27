# MLBoard Agent Docs

供 AI Agent 使用 MLBoard 的集中参考：接入训练、读取实验、编辑分析方案、制作 HTML 面板，以及部署、权限和客户端开发。无需先读整份源码。

## 从任务开始

| 任务 | 先读 |
|---|---|
| 第一次接入，准备实例地址/项目/key | [快速开始](guides/quickstart.md) |
| 修改训练代码、记录指标、离线补传 | [训练接入](guides/training.md) |
| 选择实验、查询曲线和结构化数据 | [数据查询](guides/querying.md) |
| 修改图表、布局、选集、个人/共享方案 | [分析方案](guides/dashboards.md) |
| 编写自定义 HTML 展示 | [HTML 面板](guides/html-panels.md) |
| 通过 MCP 操作 | [MCP 接入](guides/mcp.md) |
| 组织、项目、key 权限不足 | [权限模型](guides/permissions.md) |
| 超时、超预算、版本冲突、采样含义 | [排障与边界](guides/troubleshooting.md) |
| 部署到 LAN、反代、数据库与 Valkey | [部署与运维](guides/deployment.md) |
| 修改服务端、SDK、Web 或 iOS | [开发参考](guides/development.md) |

Agent 首先阅读 [AGENTS.md](AGENTS.md)。给它目标描述、实例地址、项目 ID，以及任务需要时的 Run / Dashboard ID。凭据由环境或客户端凭据配置注入，不写入任务文档。

## 完整参考

- [服务端文档目录](reference/server/README.md)：API、图表、权限、部署、查询、Web、移动 API 与运维。
- [Python SDK 文档目录](reference/py-client/README.md)：记录、同步、存储、本地查看器、TensorBoard 导入与测试。
- [iOS 文档目录](reference/ios/README.md)：原生开发、Following、动线与验证。
- [生产 JSON Schema](schemas/)：7份与锁定服务端逐字节一致的文件。
- [协议及代码示例](examples/README.md)：使用占位 ID，须按实际实例替换。
- [当前已知问题](KNOWN_ISSUES.md)：包含实测发现的Step降采样Relative缺失边界。
- [来源、版本及勘误](SOURCES.md)：41份模块文档/入口，固定三个源码提交和SHA-256，可重复同步。

这是文档仓库，不包含服务端、训练数据、凭据或运行环境，也不自动给 Agent 配置 MCP。当前没有需要安装的专用 Skill；直接提供本 README / AGENTS 及相关指南即可。

## 使用版本

文档基线见 [source-lock.json](source-lock.json)。目标实例的 `/api/v1/capabilities`、`/registry`、`/schemas` 是实际能力依据；版本不同时不能硬套快照上限。历史性能报告保留各自的测试条件，不代表当前容量保证。

## 维护

同步与校验命令见 [来源说明](SOURCES.md)。常规检查使用Python 3和已安装的Node（仅检查HTML示例的JavaScript语法），无需安装额外库：

```sh
python3 -B scripts/check_docs.py
```

文档示例的实际 HTTP 验证边界记录于 [VALIDATION.md](VALIDATION.md)。
