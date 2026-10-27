> 来源：[server/docs/charts.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/charts.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 图表与示例

在项目的“分析视图”中添加面板，可选择 17 种类型。面板按可见区域加载，离开视口或收起分区后释放图表；分区分页和查询预算继续生效。

| 面板 | 数据来源与配置 |
| --- | --- |
| 标量曲线 `timeseries` | Scalar；独立 X 轴、平滑、框选缩放、图例、精确悬浮 |
| 柱状图 `bar` | Run 配置/汇总或 Table；X/Y、分组、平均/求和/数量/最后值、横向/纵向；数值轴包含零 |
| 散点图 `scatter` | Run 配置/汇总或 Table；X/Y、分组、悬浮标签、线性/对数轴、框选缩放 |
| 箱线图 `boxplot` | Run 配置/汇总或 Table；分组字段和数值字段，线性插值四分位数、Tukey 1.5 IQR 须及离群点 |
| 平行坐标 `parallel_coordinates` | Run 配置/汇总或 Table；2–12 个数值/分类字段，分组、轴选择刷选，可在 JSON 中设置 `axis_scales` 和 `inverse_axes` |
| 二维嵌入 `embedding` | Table 的预先计算好的 X/Y 坐标、类别和样本标签；不在浏览器重新运行降维算法 |
| 分布演变 `distribution` | 单个 Run 的 Histogram 随 Step 的热力图，可切换 Run；区间必须一致，默认显示每步概率质量，可设 `normalize: false` 显示计数 |
| 直方图 `histogram` | Histogram；按 Run、Step 选择快照 |
| 混淆矩阵 `confusion_matrix` | Confusion matrix；原始计数、行/列归一化和类别过滤 |
| ROC / PR `roc` / `precision_recall` | 带阈值及 TP/FP/FN/TN 的 Curve；坐标与阈值悬浮 |
| 表格 / 文本 `table` / `text` | 对应结构化记录；分页、原始数据与导出 |
| 图像 / 音频 / 视频 `image` / `audio` / `video` | Media 引用真实产物；可见面板内 ≤2 MiB 的支持格式自动读取，较大文件按需读取；播放器不会自动播放 |
| 自定义 `html` | 沙箱文档，通过声明的查询/字段授权读取数据；禁止网络访问，保留发布/绑定权限检查 |

图表操作、页内放大和全屏见 [web.md](web.md#图表)。Agent 通过 HTTP/MCP 读取数据、修改布局与图表配置的完整流程见 [agent-dashboards.md](agent-dashboards.md)。

## 字段与资源限制

在添加/编辑面板中选择数据来源与字段。Run 来源提供 `run`、`state`、`config.<字段>`、`summary.<指标名称>`；带上下文的指标附加排序后的 `[key=value]`。这些数据仍受项目/Run 访问权限控制。

标量曲线和原生结构化面板先读取 Run 元信息、指标目录与查询数据。Run 来源的柱状图、散点图、箱线图、平行坐标和二维嵌入在面板可见时独立读取精确汇总；面板编辑器在打开时读取汇总以提供指标和字段选择，Run 页的“原始指标汇总”在展开时读取。加载失败会显示错误并提供重试，不把元信息响应中的空汇总当成指标结果。

实验列表的汇总列、比较表与新建视图的指标选择继续读取精确汇总，公共分享继续使用分享接口按权限过滤后的汇总。分析视图中独立的汇总加载不阻塞同页仅依赖查询数据的图表。

Table 来源使用每个 Run/指标/上下文的最新快照，精确比较 int64 Step，不混入历史快照。附加 `$run`、`$run_id`、`$step` 字段。缺失/非数值坐标不转成零；字段错误会提示修正。表格处理上限 100000 行；柱状/箱线图保留全部有效数据统计，分类上限 200、分组上限 50。

散点/嵌入默认最多 5000 个显示点、平行坐标默认 2000；`max_points` 可设 100–20000。分布图最多 128 个采样时刻和 128 个相邻合并区间。发生采样时显示提示，数据检查器/JSON 导出保留查询结果。箱线图仅在离群点超过 1000 时采样离群点，四分位数不采样。

通过 REST、MCP 或 XML 保存面板使用相同 DashboardSpec。`GET /api/v1/registry` 返回实际支持的面板及 `options_schema`，`GET /api/v1/schemas` 包含 `chart-options.schema.json`。Run 来源面板设置 `options.data_source: "runs"` 且 `query_refs: []`；Table 来源须声明 `source.kind: "table"` 查询，分布图使用 Histogram 查询。

## 生成完整 Demo

从根目录运行，使用仓库内的 Python SDK；需要已安装的 ffmpeg 生成两秒视频。全部内容为确定性合成数据，实际写入服务端。

```sh
export PYTHONPATH="$PWD/src/py-client"
# 通过环境变量提供 MLBOARD_API_KEY，勿把它写入源码或命令历史。
python3 src/server/examples/chart_gallery.py \
  --server http://127.0.0.1:8766 \
  --organization org_default \
  --logdir outputs/chart-gallery
```

密钥需要 `projects:write`、Runs/Data 读写、Dashboards 读写、`html:publish`、`html:bind_data`。脚本创建 Chart gallery 项目、6 个超参数实验和包含 17 类面板的“图表示例”分析视图，输出可直接打开的地址。重复运行复用已完成示例实验并更新该视图；不会覆盖其他项目。`gallery.json` 仅记录公共标识和页面地址，不保存密钥。

当前覆盖常用实验图表、二维嵌入和媒体；尚未实现 W&B 的参数重要性计算、三维点云和交互式分割掩码叠加。
