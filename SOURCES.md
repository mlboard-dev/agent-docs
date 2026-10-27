# 来源与更新

快照日期：2026-10-27。来源均为已发布的私有模块仓库。

| 模块 | 固定提交 |
|---|---|
| server | [`73643d8`](https://github.com/mlboard-dev/server/tree/73643d862b4d6d930e6cfd41bb68acd949ed22df) |
| py-client | [`9f27e9d`](https://github.com/mlboard-dev/py-client/tree/9f27e9de3d37b61a0276c71aec0e514d88759761) |
| ios | [`d42eab1`](https://github.com/mlboard-dev/ios/tree/d42eab1f37a90c5d171611f57556877f62e39fda) |

`sources.json` 记录每份上游原文SHA-256、整理后的SHA-256和修改原因；`schemas/` 与生产嵌入文件逐字节一致。引用代码和部署模板的链接固定到上游提交，不依赖本地工作区。

## 已核对的文档勘误

- `server/docs/api-contract.md`：上游这一句仍是旧上限；按同提交 capabilities.go、query.schema.json 和 docs/query-performance.md 校正。
- `server/docs/api-contract.md`：生产 query schema 的 transform.kind 为 raw 或 downsample；none 不是当前 wire 值。
- `server/docs/agent-dashboards.md`：与上游本文末尾的个人方案权限及当前后端实现保持一致。

上游文档中的本机绝对路径和开发机地址改成通用示例；相对源码链接改为固定提交链接。其余正文保留原样，包含适用版本和验证边界。历史性能数字属于对应基线的测量，不是当前部署容量保证。

## 同步

修改source-lock.json到已检查过的提交，再执行：

```sh
python3 -B scripts/sync_references.py --repositories /path/to/checkouts
python3 -B scripts/check_docs.py
```

checkouts中分别放server、py-client、ios三个仓库。脚本按Git对象读取，不采用未提交文件；不自动fetch、推送或更改源码仓库。更新后复核reference-overrides.json，无法精确匹配的旧勘误会报错。新指南由本仓库维护，其他镜像文档通过同步脚本更新。

设计草案、工作日志、测试数据库、账号配置和原始性能产物不属于默认操作手册，没有复制进本仓库。
