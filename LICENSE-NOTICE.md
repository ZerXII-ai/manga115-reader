# 许可证与上游

本项目的部署脚本与 Suwayomi 补丁按 [MPL-2.0](LICENSE) 提供。构建时须从官方发行版下载 Suwayomi Server v2.4.2366，并验证 SHA-256；仓库不分发其 JAR。Suwayomi Server 及其各依赖的许可由上游规定，详见 [Suwayomi Server](https://github.com/Suwayomi/Suwayomi-Server) 和发行包中的许可信息。

`build/openlist/openlist-v4.2.9.patch` 包含从 OpenList 上游 [PR #3342](https://github.com/OpenListTeam/OpenList/pull/3342) 与 [PR #3344](https://github.com/OpenListTeam/OpenList/pull/3344) 选取、适配到 v4.2.9 的代码及测试，按 [AGPL-3.0](build/openlist/LICENSE-AGPL-3.0) 分发；OpenList 上游源码及许可见 [OpenList](https://github.com/OpenListTeam/OpenList/tree/v4.2.9)。

容器还使用 [OpenList](https://github.com/OpenListTeam/OpenList)、[Rclone](https://github.com/rclone/rclone)、Alpine Linux 及其 OpenJDK 软件包；其镜像、商标和许可分别归对应项目所有。
