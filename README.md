# 🛠️ Hermes Patches

> **Non-intrusive Enhancement Patches for Hermes Agent**  
> 给 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 插上全功能之翼 —— **Token 消耗精准计量、Telegram 原生富文本表格放行、中文菜单汉化与生产级 SQLite 稳定性加固**。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Hermes Agent](https://img.shields.io/badge/Hermes_Agent-v0.20%2B-orange.svg)](https://github.com/NousResearch/hermes-agent)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-green.svg)](https://github.com/shali10/hermes-patches/pulls)

---

## ✨ 核心特性一览

| 模块 | 官方原生状态 | 安装 hermes-patches 后 ✨ |
|---|---|---|
| **📊 Token 消耗计量** | 仅显示精简模型与百分比（`gpt-4o · 7%`） | **全指标精准展示**：Prompt 总量、缓存命中数及百分比、输出 Token、执行耗时、上下文占用（带千分位格式化） |
| **📑 Telegram 原生表格** | CJK 中文字符下 Markdown 表格易被拦截或退化为无序列表 | **100% 放行原生 Pipe Table**，享受 Telegram 桌面与移动端现代表格富文本排版 |
| **🇨🇳 Telegram 快捷菜单** | 官方全英文菜单（`/start`, `/new`, `/reset`...） | **原生中文本地化**，常用命令功能一目了然 |
| **🛡️ 生产数据库自愈** | 高并发或并发读写时易报外键缺失或 SQLite 锁死 | **自动外键补齐自愈 + 连接级 `busy_timeout=5000` 争用保护**，避免会话中断 |
| **🚀 升级自愈守护** | 升级 Hermes 源码会丢失个性化补丁 | **systemd `ExecStartPre` 自动守护**，版本更新后自动重应用，**永不失效** |

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

## 🚀 极速安装 (One-line Install)

在运行 Hermes Agent 的 Linux 服务器上执行以下一行命令即可：

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

### 脚本全自动完成：
1. 🔍 **智能寻径**：自动识别 `/usr/local/lib/hermes-agent`、`/opt/hermes-agent` 或 Python `site-packages`；
2. 🛡️ **安全备份**：对被修改的文件保留 `.bak` 备份；
3. ⚙️ **自动配置**：确保 `~/.hermes/config.yaml` 中启用了页脚全字段；
4. 🔄 **系统守护**：若检测到 `hermes-gateway.service`，自动注入 `ExecStartPre` 钩子，**升级 Hermes 后重启依旧自动生效**。

---

## ⚙️ 配置文件说明 (`~/.hermes/config.yaml`)

安装脚本会自动配置，如需手动调整页脚显示字段，可在配置中声明：

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

## 🗑️ 一键卸载与恢复 (Uninstall)

如果想完全恢复到官方原生状态：

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash -s -- --uninstall
```

---

## 🤝 参与贡献与致谢

欢迎提交 Issue 和 Pull Request！如果你有更实用的 Hermes 生产补丁，欢迎分享与合并。

- **Upstream Project**: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **License**: [MIT](LICENSE)
