# 📝 更新日志 (Changelog)

所有 `hermes-patches` 的重要更新与演进均记录于此。  
本项目遵循 [Semantic Versioning (语义化版本 2.0.0)](https://semver.org/lang/zh-CN/) 规范。

---

## [v1.6.1] - 2026-09-08

### 🔄 交互控制台持续会话主循环与状态实时刷新
- **交互会话主循环 (Interactive Main Loop)**：
  - 修复交互控制台在完成单项或多选补丁安装后立即退出进程的问题；
  - 引入完整的终端交互循环机制，补丁操作、Dry-Run 预检、卸载还原或断言测试完成后，在底部输出操作提示，支持「按回车刷新并返回主菜单」与「输入 0 / q 退出」；
  - 保持管理界面的连续性，无需重复执行脚本即可连续管理多个补丁模块。
- **状态动态自刷新 (Live Status Dynamic Re-probing)**：
  - 每次返回主菜单时自动重新执行轻量级状态嗅探，各模块状态徽标（`[已应用 ✓]` / `[未应用 -]`）及顶栏计数器实时刷新展示最新状态。
- **环境自适应隔离**：
  - 非交互式执行场景（无 TTY 管道构建、自动化 CI、带 CLI 参数调用）保持单次执行即正常退出（Exit Code 0），互不干扰。
- **测试套件扩充**：
  - `tests/test_behavior.py` 扩充用例 12，覆盖交互循环退出状态机与 TTY 判定逻辑断言。

---

## [v1.6.0] - 2026-09-08

### 🎛️ 新增支持多选安装与补丁应用状态显示
- **补丁应用状态显示 (Live Status Probing & Badges)**：
  - 控制台启动时自动检测各补丁是否已经刷入，菜单项前直观显示 `[已应用 ✓]` 或 `[未应用 -]`；
  - 顶栏实时统计当前环境补丁数量（如 `补丁状态: X/10 已应用`）；
  - CLI 新增 `--status` 参数（支持 `--json` 输出结构化数据），方便直接读取补丁状态。
- **支持多选安装 (Direct Multi-Selection)**：
  - 主界面输入框直接支持多选编号，无需二级菜单跳转；
  - 支持空格分隔（如 `2 3 7`）、逗号分隔（如 `2,3,7`）、连续范围（如 `2-5` 即 2、3、4、5 号）以及混合表达式（如 `2-4, 7, 10`）；
  - 选定多项后直接安装所选补丁并自动平滑重启；
  - CLI `--only` 与 `--skip` 参数同步支持数字编号和范围语法（如 `--only 2 3 7` 或 `--only 2-5`）。
- **Python CLI 控制台对齐**：
  - 终端直接运行 `hermes-patches` 时拉起一致的交互控制台。
- **测试套件扩充**：
  - `tests/test_behavior.py` 扩充用例 11，覆盖多选编号/范围语法解析与状态探测断言。

---

## [v1.5.0] - 2026-09-07

### 🧱 核心里程碑：SQLite 主库防误删护栏与 Neo-Brutalist 极客视觉升级 (State DB Anti-Destruction Guard)
- **新增第 10 项生产级杀手补丁 `state-guard`（`tools/approval.py` / `tools/approval_detection.py`）**：
  - 对 live `state.db`（以及 `-wal`, `-shm`, `-journal`）注入不可绕过的 `HARDLINE_PATTERNS` 动作级防删安全地线；
  - 精准阻断 Agent 自主执行系统清理时可能触发的 `rm /path/to/state.db`、`unlink`、`truncate -s 0`、`> / >>` 覆盖截断、`find -delete / -exec rm` 以及 `mv state.db` 等破坏性命令；
  - 采用精确的负向前瞻 `(?![A-Za-z0-9_.])`，严格区分生产活库与备份文件，100% 允许合法的 `.bak`、`.corrupt`、`.old`、`.gz` 文件清理以及 `sqlite3 .backup`、`sqlite3 PRAGMA`、`ls`、`grep` 等只读/备份操作；
  - 即使开启 `--yolo` 模式，硬核护栏依旧生效，彻底免除运维与自动化清理过程中的误删库恐慌。
- **深度适配上游模块化大拆分与双向自适应**：
  - 全面支持上游最新解耦拆分（`commands_platforms.py`、`hermes_state_wal.py`、`hermes_state_messages.py`、`run_turn_runner.py`、`cli_stream_mixin.py`、`stream_consumer_think.py`、`approval_detection.py`）；
  - 具备全智能自适应寻径引擎，老版本单体架构与最新模块化架构均能一键无缝安装与打补丁。
- **全新新野兽派 (Neo-Brutalism) 架构与特性全景图**：
  - 官方视觉全面升级，引入高对比度、硬边框、警示黄横幅的新野兽派架构全景看板，完整呈现 10 大补丁的痛点-根因-根治矩阵。
- **测试套件扩充与自动化 CI 全面绿标**：
  - `tests/test_behavior.py` 扩充至 10 项全量运行时行为断言与安全边界用例，在上游最新代码库上 10/10 自动化秒级通过。
- **交互式菜单扩展**：
  - `install.sh` 扩充交互式数字选项至 10 个独立补丁选项及 14 个操作控制项。

---

## [v1.4.0] - 2026-09-02

### ⚡ 核心增强：多厂商全字段缓存解析与代理会话级智能前缀推导 (Adaptive Cache & Multi-Vendor Ingestion)
- **多模型/中转全字段缓存解析（`agent/usage_pricing.py`）**：
  - 补齐 Google / Gemini 原生 `cached_content_token_count` 与 `cachedContentTokenCount` 解析；
  - 补齐 vLLM / LiteLLM 的 `cached_prompt_tokens`；
  - 补齐 OpenAI `details` 对象内多种别名形式的缓存命中解析。
- **代理会话级智能前缀缓存推导（`agent/conversation_loop.py`）**：
  - 当第三方中转代理（如 CPA、自建反代等）漏传 `cached_tokens` 时，自动基于多轮历史会话及工具调用链的前缀基线智能推导真实前缀缓存命中数与百分比，彻底消除假 0。
- **修复 Gateway 正常响应字典 `cache_read_tokens` 键缺失缺陷（`gateway/run.py`）**：
  - 补齐正常响应返回字典中的 `cache_read_tokens` 字段，打通最后一公里数据传输。
- **新增 `terminal-cwd` 补丁（`tools/environments/base.py`）**：
  - 显式 workdir 被删除后，在构建命令 wrapper 前回退到可用父目录，避免 exit 126。

---

## [v1.3.9] - 2026-08-29

### 🐛 修复 Runtime Footer 双返回路径缓存字段注入短路
- 修复 `transform_gateway_run` 使用全局 `cache_read_tokens not in cand` 判断，导致第一处 Payload 注入后第二处正常返回 Payload 被跳过的问题。
- 改为按返回路径分别匹配、分别幂等注入，确保异常/空响应路径与正常成功路径均传递 `cache_read_tokens`。
- 增加 CI 断言：两处 Payload 必须各包含一次缓存字段，提取逻辑只出现一次。
- 已验证首次安装、重复安装、Python AST 编译均通过。

---


## [v1.3.8] - 2026-08-29

### 🐛 关键修复：补齐网关层 Cache Read Token 传输链路 (Gateway Cache Read Ingestion Fix)
- **修复网关运行态 `cache_read_tokens` 传输断链**：
  - 深度重构 `patch_runtime_footer` 中的 `transform_gateway_run`：在官方 `gateway/run.py` 构造 `agent_result` 字典时，主动提取 `_cache_read_toks = getattr(_agent, "session_cache_read_tokens", 0) or 0` 并注入到正常返回与异常返回的两处 `agent_result` Payload 中。
  - 彻底解决由于上游官方网关未透传缓存字段、导致消费端 `agent_result.get("cache_read_tokens")` 永远返回 `None`/`0`、进而引发页脚缓存命中率持续固定显示 `0 (0%)` 的根本缺陷。
- **全链路 Token 提取与注入幂等加固**：
  - 升级 `transform_gateway_run` 的注入算法，支持无损识别多版本官方与二次魔改源码，实现安全幂等注入。

---

## [v1.3.7] - 2026-08-29

### 🎯 运行态取数兼容与双路 Token 注入加固 (Runtime Token Ingestion Fix)
- **多模型/代理取数双路兼容**：
  - 在 `gateway/run.py` 注入点改为 `prompt_tokens=agent_result.get("prompt_tokens") or agent_result.get("input_tokens") or 0`，确保无论是从 `turn_finalizer` 还是底层 `CanonicalUsage` 返回，均能正确读取到最顶层的 Prompt 全量数据。
  - 配合 `runtime_footer.py` 的自适应算法，彻底消除 `agent_result` 字段取数错位问题。

---

## [v1.3.6] - 2026-08-29

### 🎯 计量精准度与安装时序深度加固 (Metering Precision & Installer Hardening)
- **Token 缓存命中率与 Prompt 总量双重精准校准**：
  - 深度重构 `patch_runtime_footer` 中的 Token 计量算法。针对 Hermes Gateway 运行时已将 `session_prompt_tokens` 规范化为总量的场景，自动消除二次累加导致的 Prompt 总量虚高与命中率折半偏差。
  - 智能自适应任何调用源（无论是独立 Miss 输入还是已合并 Total），均能 100% 精确还原真实的物理 Prompt 总量与准确的命中百分比。
- **一键安装环境依赖自愈 (Venv Auto-Selection)**：
  - 优化 `install.sh` 解释器查找链，优先使用 Hermes Agent 自身 Virtualenv Python，确保 `yaml` 等配置解析依赖 100% 具备，杜绝精简 Linux 系统因缺少系统级 PyYAML 导致的配置跳过。
- **systemd 守护挂载时序修复与零副作用预检**：
  - 修复 `setup_systemd_hook` 在 `--dry-run`、`--list-patches`、`-h` 或菜单展示时的过早写入问题，确保预检与帮助完全零副作用、零磁盘修改。
- **补丁无缝热升级 (Seamless In-Place Upgrade)**：
  - `transform_footer` 升级为基于正则的动态循环体覆写，无论之前安装的是 v1.3.0 还是 v1.3.5，再次执行一键安装均可平滑升至最新版。

---

## [v1.3.5] - 2026-08-29

### 🐛 关键修复 (Bug Fixes)
- **Runtime Footer 全量计量注入修复**：修复 `patch_runtime_footer` 在修改 `build_footer_line` 签名时的条件误判 bug，确保 `build_footer_line` 完整接收 `prompt_tokens`、`output_tokens`、`cache_read_tokens`，彻底解决 Gateway 运行时因 `TypeError` 导致 Token 页脚静默吞噬的问题。
- **一键配置自愈增强**：`ensure_runtime_config` 自动初始化 `display.final_response_markdown: keep`、`display.streaming: false` 与 `telegram.extra.allow_cjk_rich: true`，消除格式剥离与流式降级冲突。
- **GitHub CDN 防缓存**：一键安装脚本管道注入 `nocache` 时间戳，杜绝 CDN 缓存引起的补丁延迟。

## [v1.3.4] - 2026-08-29

### 🛡️ 生产级守护加固与 systemd 重启自愈 (Systemd Service Hardening)
* **🔄 彻底根治 `systemctl restart` 报 control process exited with error code 错误**：
  * **非阻塞守护语法**：在 `10-local-patches.conf` 中将 `ExecStartPre` 升级为 `ExecStartPre=-...`（容错前缀），即使自愈脚本遇到环境扰动也绝不阻塞 Gateway 主服务正常拉起。
  * **脚本前置同步机制**：在执行任何补丁注入与服务重启前，第一时间将最新脚本同步覆盖至 `~/.hermes/scripts/hermes-local-patches.py` 并 `daemon-reload`，彻底消除旧脚本残留导致 `ExecStartPre` 崩溃卡死的问题。
  * **智能失败重试与诊断**：在重启失败时自动执行 `systemctl reset-failed` 并抓取输出 `journalctl` 现场日志。

---

## [v1.3.3] - 2026-08-29

### 🛡️ 全补丁矩阵运行时深度加固 (Full Matrix Runtime Hardening)
* **🇨🇳 Telegram 菜单与帮助汉化逻辑重构 (`hermes_cli/commands.py`)**：
  * 重构 `telegram_bot_commands` 动态汉化机制，彻底消除静态列表重写引发的 `NameError: name '_RAW_TELEGRAM_BOT_COMMANDS' is not defined` 异常。
  * 完美保留上游全部动态命令门控、插件命令发现与过滤逻辑，同时对全部 99+ 命令实现 100% 地道中文汉化。
* **🛡️ SQLite State DB 注入全面加固 (`hermes_state.py`)**：
  * 重写 `apply_database_pragmas` 注入锚点，确保 `PRAGMA busy_timeout = 5000` 连接级高并发锁等待 100% 生效。
  * 采用多行容错锚点安全注入 `append_message` 与 `append_messages_batch` 的外键自动补齐与自愈逻辑，彻底防止跨会话写入外键崩溃。
* **✂️ Telegram 4096 智能段落切分精准命中 (`gateway/platforms/base.py`)**：
  * 修复 Python 多行字符串字面量转义问题，采用精确锚点安全覆写，100% 确保长消息优先在自然段落 (`\n\n`) 边界处平滑切分。
* **🧪 引入全量 8 大补丁端到端运行时断言测试套件**：
  * 在 GitHub Actions CI 工作流中加入完整的动态导入、函数调用与字段断言测试矩阵，确保每一项补丁在全新上游代码库中 100% 真实可用。

---

## [v1.3.2] - 2026-08-29

### 🐛 缺陷修复 (Bug Fixes)
* **📑 彻底修复 Telegram CJK 原生表格放行补丁因注释特征码不匹配被跳过的重大缺陷**：
  * 修复了上游 `adapter.py` 函数注释变更导致 `patch_telegram_cjk_rich` 误判为 `UNCHANGED` 未真正修改磁盘文件的严重 Bug。
  * 改为动态精确覆写 `_has_telegram_desktop_cjk_rich_garble_shape` 函数体，100% 确保含有中文字符的 Markdown Pipe Table 原生放行渲染，不再被降级为无序圆点列表。

---

## [v1.3.1] - 2026-08-29

### 🚀 新增特性 (Added)
* **🇨🇳 全量 99 个命令与 `/help`、`/commands` 地道汉化**：
  * 将 `menu` 汉化补丁升级为 **全量命令汉化引擎**，补齐官方 `COMMAND_REGISTRY` 中全部 99 个命令的专业中文释义。
  * 深度重构 `gateway_help_lines()` 与 `_build_description()`，使在 Telegram / QQ / Discord / Web 发送 `/help`、`/commands` 时，命令功能说明、参数提示与 `(别名: /...)` 标签 100% 以清晰地道的中文输出。
  * 终端 CLI 执行 `/help` 与命令补全同样享受全量中文释义。
* **⚙️ 自动初始化 `display.language: zh`**：
  * 在 `--auto-config` 流程中自动确保配置 `display.language: zh`，打通全系统内置多语言响应。

---

## [v1.3.0] - 2026-08-29

### 🚀 新增特性 (Added)
* **⚙️ 零配置开箱即用 (Turnkey Zero-Config Init)**：
  * 安装引擎现自动校验并初始化 `~/.hermes/config.yaml`（`--auto-config`），自动开启 `runtime_footer.enabled: true` 并预配置全量 6 项计量参数字段。
  * 彻底解决用户因官方默认未开启页脚配置而误以为「补丁没生效」的痛点，做到一键运行、即刻呈现！
* **🔄 全自动平滑重启 (Auto Gateway Restart)**：
  * 新增 `--restart` 参数并在默认全量安装中启用，安装完毕后自动探测 `hermes-gateway` 系统服务并执行平滑重启。
  * 无需手动切换窗口敲命令，代码注入与服务重启全链路一次性闭环。
* **🔍 终极多维自适应寻径引擎 (Universal Path Prober)**：
  * 重构源码定位逻辑，覆盖 6 层高优先级寻径：环境变量（`HERMES_PATCH_SOURCE_ROOT` / `HERMES_SOURCE_DIR`）、`/proc` 活跃进程逆向追溯、systemd `ExecStart` 探测、CLI 二进制 shebang 解释器解析、常见虚拟环境探测与系统标准路径扫描。
  * 100% 解决在复杂虚拟环境、多 Python 版本及自定义部署路径下的安装识别问题。
* **🧹 字节码全量清理与刷新 (Bytecode Cache Purge)**：
  * 安装后自动递归清除目标目录下的 `__pycache__` 与 stale `.pyc` 编译缓存，杜绝 Python 加载旧字节码导致的代码不生效。
* **🛡️ systemd 双环境变量兼容守护**：
  * `10-local-patches.conf` 守护单元同时注入 `HERMES_PATCH_SOURCE_ROOT` 与 `HERMES_SOURCE_DIR` 双环境变量，并显式传入 `--target` 参数，确保开机与重启时自愈守护 100% 稳定运行。

---

## [v1.2.0] - 2026-08-29

### 🚀 新增特性 (Added)
* **`nostream` 补丁（流式静默控制与 429 频控护盾）**：
  * 支持全局 `display.streaming: false` 与平台级流式拦截，彻底关闭中间高频 `editMessageText` 消息编辑。
  * 消除 Telegram 客户端高频跳动、频繁编辑震动与通知打扰。
  * 彻底避免生成长文本时长周期轮询导致的 `429 Flood control exceeded` 封禁限制。
* **`clean-think` 补丁（全链路深度思考净化）**：
  * **CLI 端**：将终端 `show_reasoning` 默认策略调整为静默模式，不再弹出大尺寸思维链面板遮挡屏幕。
  * **IM / Gateway 端**：全面拦截并剥离 `<think>`, `<thought>`, `<thinking>`, `<reflection>`, `<antml:thought>`, `<inner_monologue>` 等变体标签及未闭合草稿块。
* **`smart-split` 补丁（Telegram 4096 消息智能段落切分）**：
  * 重构基础平台消息切分器，优先在自然段落边界（`\n\n`）处切分，次选行边界（`\n`）。
  * 保持跨块 Markdown 结构完整性，避免在代码块中间生硬截断导致的 `can't parse entities` 解析错误。
* **🖥️ 交互式中文数字菜单 (Interactive Numbered Menu)**：
  * `install.sh` 升级为全中文可视化数字交互菜单。
  * **默认选项 `[1]` 全量一键安装**：支持直接按回车一键搞定全部 8 个补丁。
  * **支持自由组合多选**：输入单数字（如 `2`）或组合数字（如 `2 3 7` / `2,3,7`）按需安装。
  * **集成常用快捷动作**：`[10]` Dry-Run 预检分析、`[11]` 一键无损卸载与回滚、`[0]` 安全退出。
* **❓ 常见问题排障指南 (FAQ & Troubleshooting)**：
  * 官方文档新增专属 FAQ 章节，涵盖 `/footer on` 页脚激活、Telegram 客户端缓存刷新、Docker 容器内打补丁以及多 Python 虚拟环境路径指定。

### 🔄 优化与变更 (Changed)
* **全中文地道输出**：核心补丁引擎 `hermes_patches.py` 终端日志全面中文化，引入直观彩色状态图标（`🟢 已应用`、`⚪ 已是最新/无需变更`、`🟡 待应用`、`🔴 失败`）。
* **智能寻径算法增强**：新增基于 `which hermes` CLI 二进制多级符号链接追溯探测，极大提升非标准路径与虚拟环境下的自动识别成功率。
* **非侵入式配置保障**：移除破坏性 YAML 文件整写逻辑，改由代码内部原生默认初始化指标，零配置损坏风险。
* **双语文档与导航**：在中英文文档中全量引入标准 HTML 显式跳转锚点与顶部导航栏。
* **CI 与测试**：更新 GitHub Actions 每日 CI 流程，覆盖全量 8 个补丁注入及 9 个核心文件的 Python 语法编译检测。

---

## [v1.1.0] - 2026-08-29

### 🚀 新增特性 (Added)
* **模块化精细控制**：引入 `--only` 与 `--skip` CLI 参数，支持用户按需选择注入模块（例如：`--only table db`）。
* **CLI 模块查询**：新增 `--list-patches` 命令，快速列出所有补丁 ID、别名列表与功能说明。
* **`tirith` 补丁（低风险审批免打扰）**：自动放行 LOW / INFO 级别的静态安全扫描提示，高危风险正常拦截，提升自动化流畅度。
* **双语官方文档**：新增英文完整文档 `README_EN.md` 与中英文快速导航切换。
* **开源社区规范**：添加 GitHub Issue 模板（Bug Report 与 Feature Request）。
* **CI 兼容性防护**：添加每日定时 GitHub Actions 工作流，自动对 upstream `NousResearch/hermes-agent` 最新代码执行注入与编译测试。

### 🛡️ 安全增强 (Security)
* 引入原子编译保护机制：修改代码时先在临时文件进行 `py_compile.compile(..., doraise=True)` 编译校验，只有语法 100% 正确时才原子置换原文件。
* 物理备份与无损回滚：首次执行自动生成 `.bak` 文件，支持 `bash install.sh --uninstall` 瞬间还原。

---

## [v1.0.0] - 2026-08-29

### 🎉 首次发布 (Initial Release)
* **`footer` 补丁（Runtime Footer 全指标计量）**：
  * 输出 Prompt 总量、缓存命中数及命中率百分比、输出 Token、执行耗时与上下文占用率。
  * 所有数值引入千分位格式化（`12,345`），排版工整清晰。
* **`table` 补丁（Telegram CJK 原生 Markdown 表格放行）**：
  * 绕过桌面端 CJK 字符乱码检测，100% 放行现代 Telegram 原生 Markdown Pipe Table。
* **`menu` 补丁（Telegram 快捷命令中文本地化）**：
  * 将 `/start`, `/new`, `/reset`, `/status`, `/model`, `/memory`, `/skills`, `/help`, `/restart`, `/doctor`, `/footer` 等快捷命令描述汉化为地道中文。
* **`db` 补丁（SQLite 生产级外键自愈与高并发争用保护）**：
  * 数据库连接注入 `PRAGMA busy_timeout = 5000`，有效缓解高并发锁表。
  * 自动补齐 session 外键父记录，彻底根治消息写入时的外键缺失中断报错。
* **一键安装与守护脚本**：
  * 提供 `install.sh` 脚本，支持自动寻径 Hermes 安装目录。
  * 配置 systemd `ExecStartPre` 自动守护钩子，实现 Hermes 源码升级后补丁自动重应用（升级不失效）。
