# PythonScheduler 1.2.3

面向 iOS 17+ rootless / RootHide 越狱环境的 Python 脚本管理器源码。目标设备信息由用户提供：iOS 17.3.1、Relaxin、Sileo。

## 本版完成

- 本地 HTTP API，仅监听 `127.0.0.1:18765`。
- SwiftUI 管理端源码：导入/删除/立即运行脚本、定时任务、任务启停、日志、pip 安装单个依赖。
- 后台服务：每日、间隔、每周、单次调度；错过当天设定时间时，服务恢复后会补执行一次；脚本独立 venv；运行超时；日志；删除脚本时清理其任务和 venv。
- DEB rootless 目录布局：`/var/jb/usr/libexec` 与 `/var/jb/Library/LaunchDaemons`。
- LaunchDaemon 以 `mobile` 用户运行，避免以 root 身份执行用户脚本。
- API 对脚本 ID、请求体大小、时间和包名进行基本校验。

## 重要限制 / 安装前检查

1. **没有生成 IPA**：本构建环境不是 macOS，不能运行 Xcode/iOS SDK，也不能替用户签名。`ios/` 是 Xcode 项目源码。需在 macOS Xcode 15+ 打开 `ios/PythonScheduler.xcodeproj`，选择签名团队并构建 Archive，再导出 IPA。
2. DEB 目标架构为 `iphoneos-arm64`（rootless arm64）。尚未在真实 Relaxin 设备上验证。安装前请确认该 bootstrap 的 Python 解释器确实位于 `/var/jb/usr/bin/python3`，并且 `venv`、`ensurepip`、`ssl` 可用。
3. Relaxin/RootHide 不同 bootstrap 版本的 jbroot、launchd 域和启动方式可能不同。DEB 的 postinst 使用 `/var/jb/Library/LaunchDaemons` 与 `launchctl bootstrap system`；如设备实际路径不同，需要按设备环境调整，不能保证通用。
4. 越狱未激活期间，任何越狱 launch daemon 都不能运行。重新激活越狱后才可恢复服务。
5. Python 脚本是用户提供的任意代码，运行时拥有 `mobile` 用户权限；只导入可信脚本。pip 安装需要网络和可用的 Python wheel/编译依赖。
6. 独立 venv 依赖 Python 的 `venv/ensurepip`。有些 iOS bootstrap 的 Python 构建可能不带完整模块；安装脚本会在缺失时中止并提示，不会伪装成已成功。
7. 调度服务每 15 秒检查一次任务；每日/每周任务采用“到点后当天补执行一次”的策略。iOS 本地时间/时区变化可能影响日历任务；间隔任务以 epoch 计算。

## 构建 DEB

在 Debian/Linux 上执行：

```sh
dpkg-deb --build --root-owner-group deb PythonScheduler.deb
```

安装前先检查：

```sh
dpkg-deb --info PythonScheduler.deb
dpkg-deb --contents PythonScheduler.deb
```

卸载：

```sh
apt remove com.python.scheduler
```

用户脚本和日志位于 `/var/mobile/Library/PythonScheduler`，卸载包不会主动删除这些用户数据。

## API

- `GET /health`, `/scripts`, `/tasks`, `/logs`
- `POST /scripts`：`{"name":"a.py","content":"<base64>"}`
- `POST /tasks`：脚本 ID、mode (`daily|interval|weekly|once`)、time、minutes、days、date
- `PATCH /tasks/<id>`：`{"enabled":false}`
- `DELETE /tasks/<id>`、`DELETE /scripts/<id>`
- `POST /run`：`{"script_id":"..."}`
- `POST /pip`：`{"script_id":"...","package":"requests"}`
- `POST /requirements`：`{"script_id":"...","requirements":"requests\nhttpx"}`

服务仅绑定 loopback，不应改为 `0.0.0.0`。

## 1.2.3 修订

- iOS 客户端 pip 安装请求超时提升到 15 分钟，requirements 安装提升到 30 分钟，避免客户端先于后台 pip 进程超时。
- 客户端现在会检查 HTTP 状态码，并把后台 API 错误返回给界面，而不是将 HTTP 4xx/5xx 当作成功响应。
- 增加调度器单元测试，覆盖每日补执行、同日防重复、每周日期、间隔任务、单次任务和禁用任务。
- 清理打包目录中的 Python `__pycache__`，避免把本机字节码放入 iOS DEB。

运行测试：

```sh
python3 -m py_compile deb/var/jb/usr/libexec/python-scheduler.py
python3 -m unittest discover -s tests -v
```

## GitHub 手机端构建

把 `PythonScheduler-1.2.3-source.zip` 上传到仓库根目录，并把独立工作流文件内容保存为 `.github/workflows/build.yml`。该工作流会在 GitHub macOS runner 解压源码、运行 Python 测试并尝试构建未签名 IPA。未签名 IPA 仍需自行签名后才能安装。


## 1.2.3 修订

- 新增本地 HTTP API 集成测试，覆盖健康检查、脚本/任务创建删除、任务启停。
- 每周任务严格校验星期代码，单次任务严格校验日期格式，避免无效任务写入数据库。
- pip 单包安装参数增加包名/版本格式白名单，拒绝以 `-` 开头的 pip 选项，降低参数注入风险。
- GitHub Actions 改为同时执行单元测试与 API 集成测试，再构建未签名 IPA。

注意：requirements.txt 是用户主动导入的 pip requirements 文件，仍应只导入可信来源。
