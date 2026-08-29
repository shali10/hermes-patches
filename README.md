# 🛠️ Hermes Patches

> **Non-intrusive Turnkey Production Enhancement Patches for Hermes Agent**  
> 给 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插上全功能之翼 —— **Token 消耗精准计量、Telegram 原生富文本表格放行、中文菜单汉化、生产级 SQLite 锁死与外键自愈、低风险审批免打扰、流式静默控制与 429 频控护盾、全链路深度思考净化、4096 超长消息智能排版切分、零配置自动初始化与一键平滑重启**。

<p align="center">
  <a href="README_EN.md"><b>English</b></a> | <b>简体中文</b> | <a href="CHANGELOG.md"><b>📝 更新日志 (Changelog)</b></a> | <a href="https://github.com/shali10/hermes-patches/releases"><b>🏷️ Releases</b></a>
</p>

<p align="center">
  <a href="https://github.com/shali10/hermes-patches/releases"><img src="https://img.shields.io/github/v/release/shali10/hermes-patches?color=blue&label=Release" alt="Latest Release" /></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/Changelog-v1.3.6-orange.svg" alt="Changelog" /></a>
  <a href="https://github.com/shali10/hermes-patches/actions/workflows/test.yml"><img src="https://github.com/shali10/hermes-patches/actions/workflows/test.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg" alt="Python 3.10+" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes_Agent-v0.20%2B-orange.svg" alt="Hermes Agent" /></a>
  <a href="https://github.com/shali10/hermes-patches/pulls"><img src="https://img.shields.io/badge/PRs-welcome-green.svg" alt="PRs Welcome" /></a>
</p>

> 🧭 **快速导航**：[✨ 痛点对照](#features) · [🔍 效果实测](#showcase) · [🚀 一键安装](#installation) · [📦 补丁清单](#patches) · [❓ 排障FAQ](#faq) · [📝 更新日志](#changelog) · [↩️ 一键卸载](#uninstall)

---

<a id="features"></a>
## ✨ 核心特性与生产痛点对照

| 模块 | 官方原生状态 | 安装 hermes-patches (v1.3.0) 后 ✨ |
|---|---|---|
| **📊 Token 消耗全透视** | 仅显示精简模型与百分比（`gpt-4o · 7%`） | **全指标精准展示**：Prompt 总量、缓存命中数及百分比、输出 Token、执行耗时、上下文占用（千分位格式化） |
| **📑 Telegram 原生表格** | CJK 中文字符下 Markdown 表格易被拦截退化为无序列表 | **100% 放行原生 Pipe Table**，享受现代 Telegram 原生高保真表格渲染 |
| **🇨🇳 Telegram 快捷菜单** | 官方全英文菜单（`/start`, `/new`, `/status`...） | **原生中文本地化**，命令功能与操作一目了然 |
| **🛡️ 生产数据库自愈** | 高并发写入时易报 `FOREIGN KEY` 缺失或 `database is locked` 崩溃 | **自动外键补齐自愈 + 连接级 `busy_timeout=5000` 争用保护**，彻底杜绝会话中断 |
| **⚡ 自动化审批免打扰** | 自动化任务易被 LOW/INFO 级静态扫描警告中断弹窗 | **自动放行低风险提示**，高危风险正常拦截，大幅提升自动化流畅度 |
| **🚫 流式静默与频控护盾** | 中间消息高频 `editMessageText` 导致界面狂闪、手机震动，易触发 Telegram 429 限流 | **支持全局 `display.streaming: false` 优雅静默**，转为一次性完整交付，零抖动、免限流 |
| **🧠 思考过程深度净化** | 推理模型输出冗长 `<think>` 刷屏，CLI 弹大窗，IM 偶发草稿泄露 | **全链路深度剥离所有思维链变体**（`<think>`, `<thought>`, `<antml:thought>` 及未闭合块），只留干净最终正文 |
| **✂️ 4096 消息智能切分** | 超过 4096 字符时生硬截断，导致代码块破坏或报 `can't parse entities` | **优先在自然段落（`\n\n`）边界优雅切分**，自动闭合并补齐代码围栏与表格结构 |
| **⚙️ 零配置开箱即用** | 安装后需手动敲多条命令开启配置 | **自动校验并初始化 `config.yaml`**，页脚、参数与优化开箱即用，无需多余设置 |
| **🔄 自动平滑重启生效** | 安装后需用户自行排查进程并手动重启 | **自动探测并平滑重启 `hermes-gateway` 服务**，一行命令瞬间全量生效 |
| **🚀 升级自愈守护** | 升级 Hermes 源码或 `hermes update` 会丢失补丁 | **systemd `ExecStartPre` 自动守护**，版本更新后自动重应用，**升级永不失效** |

---

<a id="showcase"></a>
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

### 4. 🚫 流式输出静默与 429 频控防护 (Quiet Streaming)

在 `~/.hermes/config.yaml` 中配置 `display.streaming: false` 后，Gateway 将彻底关闭中间草稿编辑：
* **零消息跳动**：等待大模型推理完毕后，一次性投递高保真排版消息；
* **免除 429 限流**：彻底避免长文本生成时高频调用 Telegram `editMessageText` 导致的 Flood Control 封禁。

---

### 5. 🧠 思考过程深度净化 (Deep Thinking Cleaner)

无论是 DeepSeek-R1、QwQ、Claude 3.7 Thinking 还是 Gemini 思考模式：
* **CLI 端**：默认静音冗长的思维链弹窗，不再占用几十上百行终端；
* **IM 端**：自动拦截 `<think>`, `<thought>`, `<thinking>`, `<reflection>`, `<antml:thought>` 以及流式中断导致的未闭合残缺标签，保证消息框永远只有整洁干练的最终答复。

---

<a id="architecture"></a>
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
               │   • 自动更新 config.yaml     │
               │   • 清理 stale __pycache__   │
               │   • 幂等注入，失败绝不覆盖   │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │     Hermes Agent 核心就绪    │
               │  [Token全计量 | 原生表格    │
               │   DB锁自愈   | 汉化快捷菜单  │
               │   流式静默   | 思考过程净化  │
               │   段落切分   | 零配置全生效] │
               └──────────────────────────────┘
```

---

<a id="safety"></a>
## 🛡️ 生产级安全防护机制 (Safety First)

为防止生产环境意外损坏，引擎内置多重安全防护：

1. **🔬 字节码编译预检 (Atomic Compile Check)**：所有代码修改先在隔离临时文件中执行，并强制通过 Python 原生 `py_compile.compile(..., doraise=True)` 编译。语法校验 100% 通过后方可原子置换（`os.replace`），绝不产生损坏或半成品文件。
2. **🔄 原生备份与一键还原 (Instant Rollback)**：首次修改自动生成 `.bak` 物理备份。执行 `--uninstall` 即可瞬间无损回滚。
3. **♻️ 幂等性保障 (Idempotent)**：多次运行或重复执行自动跳过已应用补丁，绝不重复追加或破坏代码结构。
4. **🧹 字节码强制刷新 (Bytecode Cache Invalidation)**：安装后自动递归清理 `__pycache__` 与 `.pyc` 编译缓存，防止 Python 加载陈旧字节码。

---

<a id="installation"></a>
## 🚀 极速安装与部署 (Installation)

### 选项 A：零配置一键安装并自动生效（强力推荐）

直接在运行 Hermes Agent 的服务器上执行：

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

> **✨ 全自动一键搞定**：
> 1. 🔍 **全自动寻径**：通过运行进程、systemd 配置、CLI shebang 与虚拟环境智能识别当前活跃的 Hermes 源码路径；
> 2. 💉 **全量注入补丁**：编译检查并原子注入全部 8 项增强补丁；
> 3. ⚙️ **零配置初始化**：自动校验并配置 `~/.hermes/config.yaml`（激活页脚全量计量与参数）；
> 4. 🧹 **字节码刷新**：清理全部 `__pycache__` 缓存；
> 5. 🚀 **升级自愈守护**：配置 systemd `ExecStartPre` 守护，Hermes 源码更新后自动重应用；
> 6. 🔄 **自动平滑重启**：自动平滑重启 `hermes-gateway` 服务，**即刻生效，无需任何多余设置**！

---

### 选项 B：交互式中文数字菜单

直接在终端运行 `install.sh` 即可打开中文交互式控制台：

```bash
git clone https://github.com/shali10/hermes-patches.git
cd hermes-patches
bash install.sh
```

```text
=====================================================
   🛠️  Hermes Agent 体验增强补丁管理套件 (v1.3.0)   
=====================================================
 目标路径: /usr/local/lib/hermes-agent

 [1] 🚀 全量一键安装、自动配置并平滑重启 (推荐 / 直接回车)
 ---------------------------------------------------
 [2] 📊 Runtime Footer (Token 全量计量、缓存与耗时)
 [3] 📑 Telegram CJK 原生 Markdown 表格放行
 [4] 🇨🇳 Telegram 快捷命令中文菜单汉化
 [5] 🛡️ SQLite 生产级外键自愈与高并发防锁死
 [6] ⚡ Tirith 低风险扫描审批免打扰
 [7] 🚫 流式输出静默控制与 429 频控防护
 [8] 🧠 全链路深度思考过程强力净化
 [9] ✂️ Telegram 4096 长消息智能段落切分
 ---------------------------------------------------
 [10] 🔍 预览变更 (Dry Run，不写入磁盘)
 [11] ↩️ 卸载补丁并无损还原 (.bak 原生回滚)
 [0]  🚪 退出脚本
=====================================================
```

---

### 选项 C：进阶命令行参数 (Advanced CLI Flags)

```bash
# 1. 预览即将执行的改动 (Dry Run，不写入磁盘)
python3 hermes_patches.py --dry-run -v

# 2. 仅应用特定补丁（如：流式控制、思考净化、表格放行）并自动配置重启
python3 hermes_patches.py --only nostream clean-think table --auto-config --restart

# 3. 应用除中文菜单外的所有补丁
python3 hermes_patches.py --skip menu --auto-config --restart
```

---

<a id="patches"></a>
## 📦 可用补丁清单 (Patch Registry)

| 补丁 ID | 别名 (Aliases) | 作用目标 | 说明 |
|---|---|---|---|
| `footer` | `runtime-footer`, `token`, `stats` | `gateway/runtime_footer.py`<br>`gateway/run.py` | 渲染 Prompt 总量、缓存命中、输出 Token、耗时与上下文占用 |
| `table` | `cjk-table`, `telegram-table`, `pipe-table` | `plugins/platforms/telegram/adapter.py` | 绕过桌面端 CJK 拦截检查，放行原生 Markdown 表格 |
| `menu` | `telegram-menu`, `menu-zh`, `i18n` | `hermes_cli/commands.py` | 汉化 Telegram Bot `/start`, `/new`, `/status`... 命令说明 |
| `db` | `state-db`, `sqlite`, `durability` | `hermes_state.py` | 注入 `busy_timeout=5000` 与会话外键自动补齐自愈 |
| `tirith` | `approval`, `security`, `low-warn` | `tools/approval.py` | 自动放行 LOW/INFO 级别低危扫描提示，免除弹窗打扰 |
| `nostream` | `no-stream`, `quiet-stream`, `stream-shield` | `gateway/run.py` | 修复全局 `display.streaming: false` 生效机制，屏蔽 429 频控 |
| `clean-think` | `think`, `reasoning`, `suppress-thinking` | `cli.py`<br>`gateway/stream_consumer.py` | 净化思考过程与变体标签，默认静音终端冗长思维链弹框 |
| `smart-split` | `split`, `chunking`, `telegram-split` | `gateway/platforms/base.py` | 4096+ 长消息优先在自然段落切分，保护代码块与表格无损 |

---

<a id="faq"></a>
## ❓ 常见问题与排障指南 (FAQ & Troubleshooting)

### Q1: 为什么安装并重启后，消息末尾依然看不到 Token 统计页脚？
* **v1.3.0 现已全自动解决**：最新版本的 `install.sh` 会在安装时**自动修改 `~/.hermes/config.yaml` 开启 `runtime_footer` 并注入全量参数字段**。
* **手动检查**：执行 `hermes config get display.runtime_footer` 确认 `enabled: true`，或在 Telegram 机器人直接发送 `/footer on`。

### Q2: 为什么输入 `/` 看到的快捷指令依然是英文？
* **原因**：Telegram 客户端在本地有较强的 Bot Commands 缓存机制。虽然服务端在启动时已通过 `setMyCommands` 同步更新，但本地客户端可能未立即重新拉取。
* **解决办法**：在聊天窗口给 Bot 发送任意消息，或**彻底退出 Telegram 客户端（杀死后台进程）重新打开**即可刷新。

### Q3: 在 Docker / 容器化环境中如何应用补丁？
* **解决办法**：
  ```bash
  # 进入容器执行一键安装
  docker exec -it <容器名或ID> bash -c "curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash"
  # 重启容器
  docker restart <容器名或ID>
  ```

### Q4: 如何验证补丁是否真正打入当前运行的 Hermes 源码？
* **解决办法**：在服务器终端执行 Dry-Run 预检命令：
  ```bash
  curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --dry-run -v
  ```
  若显示 `⚪ [已是最新/无需变更 (UNCHANGED)]` 或 `🟢 [已应用 (APPLIED)]`，说明补丁已 100% 注入。

---

<a id="changelog"></a>
## 📝 更新日志 (Changelog)

| 版本 | 发布日期 | 重点更新摘要 | 详情链接 |
|:---:|:---:|---|:---:|
| **`v1.3.0`** | 2026-08-29 | **🚀 零配置开箱即用 + 自动平滑重启 + 终极自适应寻径引擎 + 字节码全量清理** | [查看详情 📄](CHANGELOG.md#v130---2026-08-29) |
| **`v1.2.0`** | 2026-08-29 | 增加流式静默控制（429 护盾）、思考过程深度净化、4096 智能切分、交互式中文数字菜单与排障 FAQ | [查看详情 📄](CHANGELOG.md#v120---2026-08-29) |
| **`v1.1.0`** | 2026-08-29 | 增加 `--only` / `--skip` 模块化选择、Tirith 低危审批放行、双语文档与 CI | [查看详情 📄](CHANGELOG.md#v110---2026-08-29) |
| **`v1.0.0`** | 2026-08-29 | Token 全量指标页脚、Telegram CJK 原生表格、命令汉化、SQLite 锁死自愈 | [查看详情 📄](CHANGELOG.md#v100---2026-08-29) |

👉 **完整版本演进与发布历史请参阅**：[CHANGELOG.md 完整日志文件](CHANGELOG.md) 或 [GitHub Releases 页面](https://github.com/shali10/hermes-patches/releases)

---

<a id="uninstall"></a>
## ↩️ 卸载与恢复 (Uninstall)

若需还原至官方原生代码：

```bash
bash install.sh --uninstall
```

---

<a id="contributing"></a>
## 🤝 参与贡献与开发 (Contributing)

我们非常欢迎社区提交 Issue 与 Pull Request！

1. Fork 本仓库并新建分支：`git checkout -b feature/awesome-patch`
2. 添加补丁逻辑并确保通过 `python3 hermes_patches.py --dry-run -v`
3. 提交代码并推送：`git push origin feature/awesome-patch`
4. 创建 Pull Request，CI 将自动对 upstream 最新代码执行编译测试与幂等性验证。

---

## 📄 开源协议 (License)

本项目基于 [MIT License](LICENSE) 协议开源。
