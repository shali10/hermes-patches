# 🛠️ Hermes Patches

> **Non-intrusive Production Enhancement Patches for Hermes Agent**  
> 给 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插上全功能之翼 —— **Token 消耗精准计量、Telegram 原生富文本表格放行、中文菜单汉化、生产级 SQLite 锁死与外键自愈、低风险审批免打扰**。

<p align="center">
  <a href="README_EN.md"><b>English</b></a> | <b>简体中文</b>
</p>

<p align="center">
  <a href="https://github.com/shali10/hermes-patches/actions/workflows/test.yml"><img src="https://github.com/shali10/hermes-patches/actions/workflows/test.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg" alt="Python 3.10+" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes_Agent-v0.20%2B-orange.svg" alt="Hermes Agent" /></a>
  <a href="https://github.com/shali10/hermes-patches/pulls"><img src="https://img.shields.io/badge/PRs-welcome-green.svg" alt="PRs Welcome" /></a>
</p>

---

## ✨ 核心特性与生产痛点对照

| 模块 | 官方原生状态 | 安装 hermes-patches 后 ✨ |
|---|---|---|
| **📊 Token 消耗全透视** | 仅显示精简模型与百分比（`gpt-4o · 7%`） | **全指标精准展示**：Prompt 总量、缓存命中数及百分比、输出 Token、执行耗时、上下文占用（千分位格式化） |
| **📑 Telegram 原生表格** | CJK 中文字符下 Markdown 表格易被拦截退化为无序列表 | **100% 放行原生 Pipe Table**，享受现代 Telegram 原生高保真表格渲染 |
| **🇨🇳 Telegram 快捷菜单** | 官方全英文菜单（`/start`, `/new`, `/status`...） | **原生中文本地化**，命令功能与操作一目了然 |
| **🛡️ 生产数据库自愈** | 高并发写入时易报 `FOREIGN KEY` 缺失或 `database is locked` 崩溃 | **自动外键补齐自愈 + 连接级 `busy_timeout=5000` 争用保护**，彻底杜绝会话中断 |
| **⚡ 自动化审批免打扰** | 自动化任务易被 LOW/INFO 级静态扫描警告中断弹窗 | **自动放行低风险提示**，高危风险正常拦截，大幅提升自动化流畅度 |
| **🚀 升级自愈守护** | 升级 Hermes 源码或 `hermes update` 会丢失补丁 | **systemd `ExecStartPre` 自动守护**，版本更新后自动重应用，**升级永不失效** |

---

## 🔍 功能实测与展示 (Showcase)

### 1. 📊 Token 消耗与缓存命中全透视 (Runtime Footer)

* **官方默认精简页脚**：
  ```text
  LongCat-2.0 · 7%
  ```

* **安装补丁后全量页脚**：
  ```text
  🤖 gemini-3.7-flash-high | 🧠 Prompt总量: 45,210 | 💾 缓存命中: 40,000 (88%) | 📤 输出: 280 | 🎯 上下文: 4% | ⏱️ 耗时: 3.2s
  ```

---

### 2. 📑 Telegram 原生 Markdown Pipe Table 渲染效果

安装补丁后，在 Telegram 客户端中输出 Markdown Pipe 表格将**原生高保真呈现**：

<p align="center">
  <img src="docs/images/telegram_pipe_table_demo.png" alt="Telegram Markdown Pipe Table 原生富文本表格与页脚实测演示" width="760" />
</p>

```markdown
| 模型名称 | 上下文窗口 | 推理能力 | 特性标签 | 首字延迟 |
|:---|:---|:---:|:---:|---:|
| **Gemini 2.5 Flash** | `1,000,000` | 极高 | ⚡ ULTRA-FAST | 0.32s |
| **Claude 3.7 Sonnet** | `200,000` | 卓越 | 🧠 REASONING | 0.58s |
| **DeepSeek-V3** | `64,000` | 优秀 | 💰 COST-EFFICIENT | 0.75s |
| **GPT-4o** | `128,000` | 卓越 | 🌐 MULTIMODAL | 0.45s |
```

---

### 3. 🇨🇳 Telegram 快捷命令中文菜单

客户端输入 `/` 时弹出的官方菜单已全量本地化：

```text
/start   - 响应 Telegram 的启动请求
/new     - 新建一个对话会话
/reset   - 重置当前会话（清理上下文）
/clear   - 清理上下文（保留设置）
/status  - 显示当前会话状态、活跃模型与 Token 统计
/model   - 查看或切换当前使用的模型
/memory  - 查看或搜索持久化记忆库
/skills  - 查看或管理当前可用技能
/help    - 显示可用命令与帮助信息
/restart - 安全重启 Hermes Gateway 实例
/footer  - 切换页脚统计信息显示 (on/off)
```

---

## 🏗️ 架构与工作原理 (How It Works)

`hermes-patches` 采用 **非侵入式 AST 级安全代码注入** 与 **服务级生命周期预检守护**：

```text
               ┌──────────────────────────────┐
               │    Hermes Gateway 启动服务   │
               └──────────────┬───────────────┘
                              │
                    (systemd ExecStartPre)
                              ▼
               ┌──────────────────────────────┐
               │   hermes-patches 预检引擎    │
               │   • 检查源码与补丁状态       │
               │   • py_compile 字节码校验    │
               │   • 幂等注入，失败绝不覆盖   │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │     Hermes Agent 核心就绪    │
               │  [Token全计量 | 原生表格    │
               │   DB锁自愈   | 汉化快捷菜单] │
               └──────────────────────────────┘
```

---

## 🛡️ 生产级安全防护机制 (Safety First)

为防止生产环境意外损坏，引擎内置三重安全防护：

1. **🔬 字节码编译预检 (Atomic Compile Check)**：所有代码修改先在隔离临时文件中执行，并强制通过 Python 原生 `py_compile.compile(..., doraise=True)` 编译。语法校验 100% 通过后方可原子置换（`os.replace`），绝不产生损坏或半成品文件。
2. **🔄 100% 幂等性设计 (Idempotent)**：引擎精准识别已打补丁的特征签名。重复运行无论多少次均能安全跳过，绝不产生重复插入。
3. **💾 自动备份与秒级无损回滚**：首次打补丁前自动将原文件备份为 `.bak` 镜像，提供一键卸载还原命令。

---

## 🚀 极速安装与使用 (Installation)

### 1. 标准一键安装（推荐）

在运行 Hermes Agent 的 Linux 服务器上执行以下命令：

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

### 2. 模块化按需打补丁（可选）

如果你只想安装部分补丁（例如：仅开启表格放行与数据库自愈，不汉化菜单）：

```bash
# 仅安装特定模块 (footer, table, menu, db, tirith)
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --only table db

# 排除特定模块 (例如跳过中文菜单)
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --skip menu
```

### 3. 查看补丁列表与预检 (Dry Run)

```bash
# 列出所有可用补丁
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --list-patches

# 仅预览改动，不实际写入磁盘 (Dry Run)
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --dry-run -v
```

### 4. Docker / 容器化环境集成

在自定义 `Dockerfile` 中加入以下构建指令即可：

```dockerfile
# Dockerfile
RUN curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

---

## ⚙️ 配置文件说明 (`~/.hermes/config.yaml`)

安装脚本会自动配置。如需自定义页脚显示项，可在 `~/.hermes/config.yaml` 中配置：

```yaml
display:
  runtime_footer:
    enabled: true
    fields:
      - model          # 🤖 模型名称
      - prompt_tokens  # 🧠 Prompt 总量
      - cache_read     # 💾 缓存命中数与命中率 (%)
      - output_tokens  # 📤 输出 Token
      - context_pct    # 🎯 上下文占用百分比
      - elapsed_time   # ⏱️ 执行耗时 (秒)
```

---

## ❓ 常见问题与排查 (FAQ & Troubleshooting)

<details>
<summary><b>Q: 安装后 Telegram 客户端没有看到新页脚或中文菜单？</b></summary>

> **解答**：修改在 Hermes Gateway 进程重启后生效。在 Telegram 机器人聊天框输入 `/restart`，或在终端执行 `systemctl restart hermes-gateway` 即可生效。
</details>

<details>
<summary><b>Q: 升级 Hermes Agent（如 <code>hermes update</code>）后需要重新安装吗？</b></summary>

> **解答**：**完全不需要**。安装脚本已自动向 `hermes-gateway.service` 注入 `ExecStartPre` 守护钩子。每次 Hermes 升级或重启服务时，均会自动重跑幂等补丁引擎，确保特性永不失效。
</details>

<details>
<summary><b>Q: 本项目解决了哪些 SQLite 生产报错？</b></summary>

> **解答**：
> 1. `sqlite3.OperationalError: database is locked`：高并发读写争用。补丁注入 `PRAGMA busy_timeout = 5000` 连接级排队机制。
> 2. `sqlite3.IntegrityError: FOREIGN KEY constraint failed`：会话父记录未就绪时的孤儿消息写入崩溃。补丁注入 `INSERT OR IGNORE INTO sessions` 自动自愈补齐。
</details>

---

## 🗑️ 一键卸载与恢复 (Uninstall)

如需彻底还原到官方原生代码状态：

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --uninstall
```

---

## 🤝 参与贡献与致谢

欢迎提交 Issue 和 Pull Request！如果你有更实用的 Hermes 生产补丁，欢迎分享与合并。

- **Upstream Project**: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **License**: [MIT](LICENSE)
