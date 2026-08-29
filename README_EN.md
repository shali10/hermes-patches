# 🛠️ Hermes Patches

> **Non-intrusive Turnkey Production Enhancement Patches for Hermes Agent**  
> Supercharge your [Hermes Agent](https://github.com/NousResearch/hermes-agent) deployment with **exact token telemetry & cache hit metering, Telegram native Markdown pipe table bypass, localized bot command menu, SQLite production concurrency auto-healing, gateway streaming control & rate-limit shield, deep thinking cleaner, 4096 safe message chunking, zero-config initialization, and seamless auto-restart**.

<p align="center">
  <b>English</b> | <a href="README.md"><b>简体中文</b></a> | <a href="CHANGELOG.md"><b>📝 Changelog</b></a> | <a href="https://github.com/shali10/hermes-patches/releases"><b>🏷️ Releases</b></a>
</p>

<p align="center">
  <a href="https://github.com/shali10/hermes-patches/releases"><img src="https://img.shields.io/github/v/release/shali10/hermes-patches?color=blue&label=Release" alt="Latest Release" /></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/Changelog-v1.3.2-orange.svg" alt="Changelog" /></a>
  <a href="https://github.com/shali10/hermes-patches/actions/workflows/test.yml"><img src="https://github.com/shali10/hermes-patches/actions/workflows/test.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg" alt="Python 3.10+" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes_Agent-v0.20%2B-orange.svg" alt="Hermes Agent" /></a>
  <a href="https://github.com/shali10/hermes-patches/pulls"><img src="https://img.shields.io/badge/PRs-welcome-green.svg" alt="PRs Welcome" /></a>
</p>

> 🧭 **Quick Navigation**: [✨ Features](#features) · [🔍 Showcase](#showcase) · [🚀 Installation](#installation) · [📦 Patches](#patches) · [❓ FAQ](#faq) · [📝 Changelog](#changelog) · [↩️ Uninstall](#uninstall)

---

<a id="features"></a>
## ✨ Features & Comparison

| Module | Upstream Vanilla | With hermes-patches (v1.3.0) ✨ |
|---|---|---|
| **📊 Token Telemetry** | Minimal model & percentage only (`gpt-4o · 7%`) | **Full telemetry**: Prompt total, cache hits & hit rate (%), output tokens, context %, and execution latency with formatted integers. |
| **📑 Telegram Pipe Tables** | Markdown tables often degraded to plain unordered lists | **100% bypass for native pipe tables**, rendering modern rich text tables on desktop & mobile Telegram clients. |
| **🇨🇳 Telegram Menu i18n** | English default descriptions only | **Localized command descriptions** for clearer command quick-actions. |
| **🛡️ SQLite Durability** | Prone to `database is locked` or `FOREIGN KEY` crashes during high concurrency | **Automatic `busy_timeout=5000` contention queue + foreign key session auto-healing**. |
| **⚡ Approval Optimization** | Low-severity static analysis warnings interrupt execution | **Automatic pass-through for non-blocking LOW/INFO scanner warnings**. |
| **🚫 Streaming Control & 429 Shield** | Rapid `editMessageText` causes UI flickering and triggers Telegram 429 Flood Limits | **Honors global `display.streaming: false`**, delivering complete clean responses in one final delivery without rate-limits. |
| **🧠 Deep Thinking Cleaner** | Reasoning models spam large `<think>` blocks in CLI and leak partial drafts | **Full suppression of thinking tags** (`<think>`, `<thought>`, `<antml:thought>` & unclosed blocks), leaving only clean responses. |
| **✂️ 4096 Smart Message Split** | Truncating 4096+ chars breaks code fences or causes `can't parse entities` | **Splits at natural paragraph boundaries (`\n\n`)**, automatically closing and reopening code fences & tables. |
| **⚙️ Zero-Config Out-of-the-Box** | Requires manual config tweaks to show footers | **Automatically initializes `~/.hermes/config.yaml`** with all telemetry metrics pre-configured. |
| **🔄 Seamless Auto-Restart** | Users have to manually find processes and restart | **Automatically reloads and restarts `hermes-gateway` service**, effective immediately in 1 step. |
| **🚀 Upgrade-Immune Guard** | Hermes source updates overwrite local patches | **systemd `ExecStartPre` supervision hook**, automatically re-applying patches on restart. |

---

<a id="showcase"></a>
## 🔍 Showcase

### 1. 📊 Full Runtime Footer Telemetry

* **Vanilla Default**:
  ```text
  LongCat-2.0 · 7%
  ```

* **With hermes-patches**:
  ```text
  🤖 gemini-3.7-flash-high | 🧠 Prompt总量: 45,210 | 💾 缓存命中: 40,000 (88%) | 📤 输出: 280 | 🎯 上下文: 4% | ⏱️ 耗时: 3.2s
  ```

---

### 2. 📑 Native Telegram Markdown Pipe Table Rendering

<p align="center">
  <img src="docs/images/telegram_pipe_table_demo.png" alt="Telegram Markdown Pipe Table Demonstration" width="760" />
</p>

---

### 3. 🚫 Quiet Streaming & Telegram 429 Shield

Setting `display.streaming: false` in `~/.hermes/config.yaml` cleanly disables interim edits:
* **Zero Message Flickers**: Waits for completion and delivers full, high-fidelity Markdown formatting.
* **No Telegram 429 Errors**: Eliminates the risk of Telegram `Flood control exceeded. Retry in N seconds`.

---

### 4. 🧠 Deep Thinking & Reasoning Suppression

For DeepSeek-R1, QwQ, Claude 3.7 Thinking, or Gemini Thinking models:
* **CLI Mode**: Mutes the verbose thinking box popup by default.
* **Messaging Mode**: Strips `<think>`, `<thought>`, `<thinking>`, `<reflection>`, `<antml:thought>`, and unclosed partial reasoning blocks.

---

<a id="architecture"></a>
## 🏗️ Architecture & How It Works

`hermes-patches` uses **safe code injection validated by Python's bytecode compiler** coupled with **systemd startup supervision**:

```text
               ┌──────────────────────────────┐
               │    Hermes Gateway Service    │
               └──────────────┬───────────────┘
                              │
                    (systemd ExecStartPre)
                              ▼
               ┌──────────────────────────────┐
               │   hermes-patches Engine      │
               │   • Inspects source files    │
               │   • py_compile syntax test   │
               │   • Auto-updates config.yaml │
               │   • Cleans stale __pycache__ │
               │   • Idempotent atomic update │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │     Hermes Agent Ready       │
               │  [Tokens | Tables | DB Heal  │
               │   Quiet Stream | Clean Think │
               │   Smart Split | Zero Config] │
               └──────────────────────────────┘
```

---

<a id="safety"></a>
## 🛡️ Safety Mechanisms

1. **🔬 Atomic Bytecode Pre-compilation**: Modifications undergo strict `py_compile.compile(..., doraise=True)` checks in isolated temporary files before atomic `os.replace`.
2. **🔄 Instant Rollback**: Backups (`.bak`) are preserved automatically. Use `--uninstall` to restore stock upstream code.
3. **♻️ 100% Idempotent**: Safe to run repeatedly; existing signatures are skipped cleanly.
4. **🧹 Bytecode Invalidation**: Purges stale `__pycache__` and `.pyc` files on completion.

---

<a id="installation"></a>
## 🚀 Installation

### Option A: Turnkey One-Liner (Recommended)

Run directly on the server hosting Hermes Agent:

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

> **✨ What happens automatically**:
> 1. 🔍 **Adaptive Probing**: Detects active Hermes install path across running processes, systemd, shebangs & virtualenvs.
> 2. 💉 **Injects All Patches**: Applies and verifies all 8 enhancement modules.
> 3. ⚙️ **Auto-Configures**: Updates `~/.hermes/config.yaml` to ensure footers & parameters are enabled.
> 4. 🧹 **Cache Purging**: Cleans all stale `.pyc` and `__pycache__` bytecode directories.
> 5. 🚀 **Systemd Hook**: Installs `ExecStartPre` auto-healing guard.
> 6. 🔄 **Smooth Restart**: Restarts `hermes-gateway` service automatically — instant effect without manual effort!

---

### Option B: Interactive Menu

```bash
git clone https://github.com/shali10/hermes-patches.git
cd hermes-patches
bash install.sh
```

---

### Option C: Advanced CLI Flags

```bash
# 1. Preview changes (Dry Run)
python3 hermes_patches.py --dry-run -v

# 2. Select specific patches with auto-config and auto-restart
python3 hermes_patches.py --only nostream clean-think table --auto-config --restart

# 3. Apply all except menu localization
python3 hermes_patches.py --skip menu --auto-config --restart
```

---

<a id="patches"></a>
## 📦 Patch Registry

| Patch ID | Aliases | Target Files | Description |
|---|---|---|---|
| `footer` | `runtime-footer`, `token`, `stats` | `gateway/runtime_footer.py`<br>`gateway/run.py` | Renders Prompt totals, cache read tokens, outputs, latency, and context %. |
| `table` | `cjk-table`, `telegram-table`, `pipe-table` | `plugins/platforms/telegram/adapter.py` | Allows Telegram desktop/mobile native Markdown pipe table rendering. |
| `menu` | `telegram-menu`, `menu-zh`, `i18n` | `hermes_cli/commands.py` | Localizes Telegram bot `/start`, `/new`, `/status`... command descriptions. |
| `db` | `state-db`, `sqlite`, `durability` | `hermes_state.py` | Adds `busy_timeout=5000` & auto-heals missing session parent rows. |
| `tirith` | `approval`, `security`, `low-warn` | `tools/approval.py` | Auto-approves LOW/INFO security scanner warnings. |
| `nostream` | `no-stream`, `quiet-stream`, `stream-shield` | `gateway/run.py` | Honors `display.streaming: false` to eliminate message flickers & 429 flood errors. |
| `clean-think` | `think`, `reasoning`, `suppress-thinking` | `cli.py`<br>`gateway/stream_consumer.py` | Strips `<think>` tags and suppresses verbose CLI thinking popups. |
| `smart-split` | `split`, `chunking`, `telegram-split` | `gateway/platforms/base.py` | Splits 4096+ char messages at paragraph breaks (`\n\n`) and repairs code fences. |

---

<a id="faq"></a>
## ❓ FAQ & Troubleshooting

### Q1: Why wasn't the footer appearing previously after a reboot?
* **Resolved in v1.3.0**: The installer now automatically initializes `~/.hermes/config.yaml` with `display.runtime_footer.enabled: true` and all metric fields.
* **Manual check**: Run `hermes config get display.runtime_footer` or send `/footer on` in Telegram.

### Q2: Why are bot commands still in English in Telegram?
* Telegram caches bot command lists locally. Send a message to the bot or fully close/kill the Telegram client and restart it to refresh the cache.

### Q3: How to apply patches in Docker containers?
```bash
docker exec -it <container_name> bash -c "curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash"
docker restart <container_name>
```

---

<a id="changelog"></a>
## 📝 Changelog

| Version | Date | Highlights | Details |
|:---:|:---:|---|:---:|
| **`v1.3.0`** | 2026-08-29 | **🚀 Turnkey zero-config init + automatic service restart + multi-stage path probe + bytecode purging** | [View 📄](CHANGELOG.md#v130---2026-08-29) |
| **`v1.2.0`** | 2026-08-29 | Added quiet streaming (429 shield), deep thinking cleaner, 4096 smart chunker, interactive menu & FAQ | [View 📄](CHANGELOG.md#v120---2026-08-29) |
| **`v1.1.0`** | 2026-08-29 | Added `--only` / `--skip` modular selection, Tirith low-risk bypass, bilingual docs & CI | [View 📄](CHANGELOG.md#v110---2026-08-29) |
| **`v1.0.0`** | 2026-08-29 | Initial release: Full token telemetry, Telegram pipe tables, menu i18n, SQLite durability | [View 📄](CHANGELOG.md#v100---2026-08-29) |

---

<a id="uninstall"></a>
## ↩️ Uninstall & Rollback

```bash
bash install.sh --uninstall
```

---

## 📄 License

Licensed under the [MIT License](LICENSE).
