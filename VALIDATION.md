# 文档验证

2026-10-27，当前文档基线见[source-lock.json](source-lock.json)。下述28项HTTP示例验收对应`4caeb73`；Host模式文档更新至`73643d8`，产品Host/CLI/权限回归由服务端发布验证覆盖，本文不把旧HTTP示例记录当作新版本重跑结果。这是文档和示例验收，不是产品压测。

- 41份正式模块文档/入口按三个固定Git提交同步，保留原文与整理后SHA；7份生产schema逐字节同步。
- 离线检查相对链接、JSON语法、schema内部引用、Python AST与HTML内联JavaScript语法，结果见[离线记录](validation/docs-check.json)。
- 用锁定源码构建的服务端，在独立回环端口、新建临时SQLite实例执行28项HTTP检查：运行时7份schema一致、查询模板、个人方案创建/validate、布局preview/apply/读回、HTML新增/渲染/CSP、MCP初始化/10工具目录/capabilities/query均完成。
- 实测发现Step降采样可能缺失已记录的elapsed_seconds；raw查询保留。该项明确列为[已知问题](KNOWN_ISSUES.md)，运行报告状态为passed_with_known_limitations，未把它记作全通过。
- HTML示例仅使用实际允许的绑定字段；已验证源代码语法与受限渲染响应，未自动执行浏览器MessageChannel交互。SDK训练示例只做语法及接口对应检查，本轮没有启动训练进程。
- 临时实例凭据只在验证进程内存中使用，数据库与服务均已清理。报告无真实账号、key或业务数据。

[HTTP验证记录](validation/example-http.json)

复验：

```sh
python3 -B scripts/check_docs.py
python3 -B scripts/verify_examples.py --server-binary /path/to/mlboard
```

第二条命令会启动一个新的本地测试实例并写入合成fixture，使用本仓库outputs目录，退出后清理；不会连接或修改已有实例。需要已编译的MLBoard二进制，不自动构建/下载产品。
