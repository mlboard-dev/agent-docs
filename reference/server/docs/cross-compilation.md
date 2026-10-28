> 来源：[server/docs/cross-compilation.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/cross-compilation.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# CGO 关闭的跨平台构建

从独立 server 仓库执行。已有工具要求：满足 `go.mod` 的 Go、Python 3.9+；需要更新内嵌 Web 时，再使用满足 `web/package.json` 的 Node。脚本不安装或升级工具链，不需要 C 交叉编译器。SQLite 使用现有纯 Go `modernc.org/sqlite`。

## 构建

先按 [部署说明](deployment.md#1-最简sqlite--本地文件) 构建 `web/dist`，再执行：

```sh
python3 -B scripts/cross-build.py
```

默认依次构建 `linux/amd64`、`linux/arm64`、`darwin/amd64`、`darwin/arm64`、`windows/amd64`、`windows/arm64`。Windows 产物使用 `.exe` 后缀。所有目标固定 `CGO_ENABLED=0`；使用 `-mod=readonly -trimpath -buildvcs=false -buildmode=exe`，每次最多两个包并行，六个目标不并发启动。继承的 `GOFLAGS`、Go workspace 和自动工具链下载关闭；不会更改 `HOME` 或用户 Go 配置。

可指定已有 Go、输出根目录、目标子集与包并行数：

```sh
python3 -B scripts/cross-build.py \
  --go /path/to/installed/go/bin/go \
  --output-root "$PWD/outputs/cross-build" \
  --parallel 2 \
  --target linux/amd64 --target windows/arm64
```

默认输出根目录为 `server/outputs/cross-build/`，含 `cache/`、`tmp/` 和每次唯一的 `artifacts/<run>/`。显式输出根目录同样包含全部缓存与临时文件；不能与 Go/Web 源码重叠。可复用该输出目录缓存，不向全局 Go 目录写入。生产发布应先固定源版本并完成 Web 构建；源码在构建过程中变化会阻止生成成功 manifest。失败时保留本次日志及已生成文件供排查，不将不完整矩阵标记为成功。

脚本在开始及各目标构建前后检查至少 8 GiB 可用磁盘。首次构建仍需为工具链、模块和跨平台缓存另留空间；资源紧张的构建主机应增加构建期间监测。Go 的内存软上限可在调用时设置，例如 `GOMEMLIMIT=2GiB python3 -B scripts/cross-build.py --parallel 2`，它不替代主机或容器的硬限制。

## 验证产物

每个目标构建后，脚本使用 `go version -m -json` 验证模块/入口、`CGO_ENABLED=0`、`GOOS`、`GOARCH` 和 `-trimpath=true`，随后计算 SHA-256。成功 manifest 包含二进制字节数、完整 Go 构建信息、工具链版本、Git 身份（若有）和保守的本仓构建输入哈希（`cmd/`、`internal/`、`web/`、`go.mod`、`go.sum`，排除缓存）。Go 依赖版本及校验值保留在各二进制的构建信息中；`-buildvcs=false` 不影响 manifest 单独记录源身份。

```sh
python3 -B scripts/cross-build.py \
  --verify outputs/cross-build/artifacts/<run>/manifest.json

# 也可独立查看单个产物，不执行它：
go version -m -json outputs/cross-build/artifacts/<run>/bin/mlboard-windows-arm64.exe
```

`--verify` 重新检查所有文件的 SHA、大小和实际内嵌构建信息，不信任 manifest 声明的平台。它不执行目标程序、不重新编译。编译和身份校验通过不等于目标系统运行验收；实际启动、SQLite/PG、路径权限与信号行为应在对应系统验证。Windows 的投影磁盘预算通过 `GetDiskFreeSpaceEx` 检查当前用户可用字节，与其他平台的 8 GiB 门槛相同；不会为编译成功而跳过检查。

## 开发检查

脚本编排测试只使用隔离假工具链，不编译应用：

```sh
python3 -B -m unittest discover -s scripts -p test_cross_build.py -v
```

真实六目标矩阵应在独占构建窗口运行，并保留 manifest、日志和二进制；不要把模拟测试报告成实际交叉编译或目标系统运行结果。当前工作区最终矩阵使用的锁定 Go 版本由该次报告记录。
