> 来源：[server/docs/demo-data.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/demo-data.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 大规模合成 demo 数据

`deploy/demo/seed_scale.py` 给已初始化的开发机 demo 增加两个独立项目，不修改原有项目、实验和用户数据。它只通过正常 REST 创建 Run/session/producer、提交事件及设置结束状态，不直接改数据库。

| 项目 | 实验 | 数据 |
| --- | ---: | --- |
| 大规模实验 · 1000 runs | 1000 | 1个100000步、5个50000步、2个10000步、其余992个各50步；每个2指标，共839200点 |
| 多指标分页 · 128 metrics | 4 | 每个128指标×120步，共61440点 |

合计1004个实验、900640个指标点。包含多种模型/学习率/batch size、文件夹及完成/失败/停止状态；全是静态合成记录，不冒充正在训练。长曲线包含变化趋势、局部峰值及细粒度波动，可体验缩放、比较和大历史读取。它不是性能基准，不能用导入过程或浏览体感替代正式测量。

使用开发机已有 Python，无需新依赖：

```sh
python3 -B /path/to/mlboard/demo-live/source/server/deploy/demo/seed_scale.py \
  --root /path/to/mlboard/demo-live
```

这是特定演示入口的辅助工具，校验已授权LAN origin，使用私有 `credentials.json` 登录，日志不输出凭据。与部署程序共享排他锁，避免在数据库复制/切换时写入。

进度写入 `state/scale-seed-v1.json`，每批仅在完整核对ACK的Run/session/producer/seq后推进。固定事件身份支持同内容重试，网络响应丢失不重复生成点；再次运行会继续未完成项，并跳过完成项的元信息修改。遇到项目/Run重建、项目名称冲突或无效ACK会停止，不猜测归属或覆盖用户编辑。完成后逐页复核实验ID与incarnation，并输出 `state/scale-seed-v1-report.json`。

采用单写入者和有界批次，空闲磁盘低于10GiB暂停，给常驻demo及后续版本的数据副本留余量。不会调整查询/内存/超时预算，不会删除旧数据腾空间。默认未选实验时需在页面选择目标实验；长曲线建议先选1–2个，是否可扩大范围由产品实际预算决定。
