# 📝 更新日志 (Changelog)

所有 `hermes-patches` 的重要更新与演进均记录于此。  
本项目遵循 [Semantic Versioning (语义化版本 2.0.0)](https://semver.org/lang/zh-CN/) 规范。

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

### 🔄 优化与变更 (Changed)
* 补丁注册表 `PATCH_REGISTRY` 扩展为 8 个核心模块，全面支持 `--only` 与 `--skip` 参数精细化匹配。
* 更新 GitHub Actions 每日 CI 流程，覆盖全量 8 个补丁注入及 9 个核心文件的 Python 语法编译检测。
* 同步更新 `README.md` 与 `README_EN.md` 文档中的功能展示、痛点对照表与 CLI 示例。

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
