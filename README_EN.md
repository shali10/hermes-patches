# 🛠️ Hermes Patches

> **Non-intrusive Production Enhancement Patches for Hermes Agent**  
> Supercharge your [Hermes Agent](https://github.com/NousResearch/hermes-agent) deployment with **exact token telemetry & cache hit metering, Telegram native Markdown pipe table bypass, localized bot command menu, SQLite production concurrency auto-healing, gateway streaming control & rate-limit shield, deep thinking cleaner, and 4096 safe message chunking**.

<p align="center">
  <b>English</b> | <a href="README.md"><b>简体中文</b></a> | <a href="CHANGELOG.md"><b>📝 Changelog</b></a> | <a href="https://github.com/shali10/hermes-patches/releases"><b>🏷️ Releases</b></a>
</p>

<p align="center">
  <a href="https://github.com/shali10/hermes-patches/releases"><img src="https://img.shields.io/github/v/release/shali10/hermes-patches?color=blue&label=Release" alt="Latest Release" /></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/Changelog-v1.2.0-orange.svg" alt="Changelog" /></a>
  <a href="https://github.com/shali10/hermes-patches/actions/workflows/test.yml"><img src="https://github.com/shali10/hermes-patches/actions/workflows/test.yml/badge.svg" alt="CI Status" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg" alt="Python 3.10+" /></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Hermes_Agent-v0.20%2B-orange.svg" alt="Hermes Agent" /></a>
  <a href="https://github.com/shali10/hermes-patches/pulls"><img src="https://img.shields.io/badge/PRs-welcome-green.svg" alt="PRs Welcome" /></a>
</p>

> 🧭 **Quick Navigation**: [✨ Features](#features) · [🔍 Showcase](#showcase) · [🚀 Installation](#installation) · [📦 Patches](#patches) · [📝 Changelog](#changelog) · [↩️ Uninstall](#uninstall)

---

<a id="features"></a>
## ✨ Features & Comparison

| Module | Upstream Vanilla | With hermes-patches ✨ |
|---|---|---|
| **📊 Token Telemetry** | Minimal model & percentage only (`gpt-4o · 7%`) | **Full telemetry**: Prompt total, cache hits & hit rate (%), output tokens, context %, and execution latency with formatted integers. |
| **📑 Telegram Pipe Tables** | Markdown tables often degraded to plain unordered lists | **100% bypass for native pipe tables**, rendering modern rich text tables on desktop & mobile Telegram clients. |
| **🇨🇳 Telegram Menu i18n** | English default descriptions only | **Localized command descriptions** for clearer command quick-actions. |
| **🛡️ SQLite Durability** | Prone to `database is locked` or `FOREIGN KEY` crashes during high concurrency | **Automatic `busy_timeout=5000` contention queue + foreign key session auto-healing**. |
| **⚡ Approval Optimization** | Low-severity static analysis warnings interrupt execution | **Automatic pass-through for non-blocking LOW/INFO scanner warnings**. |
| **🚫 Streaming Control & 429 Shield** | Rapid `editMessageText` causes UI flickering and triggers Telegram 429 Flood Limits | **Honors global `display.streaming: false`**, delivering complete clean responses in one final delivery without rate-limits. |
| **🧠 Deep Thinking Cleaner** | Reasoning models spam large `<think>` blocks in CLI and leak partial drafts | **Full suppression of thinking tags** (`<think>`, `<thought>`, `<antml:thought>` & unclosed blocks), leaving only clean responses. |
| **✂️ 4096 Smart Message Split** | Truncating 4096+ chars breaks code fences or causes `can't parse entities` | **Splits at natural paragraph boundaries (`\n\n`)**, automatically closing and reopening code fences & tables. |
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
               │   • Idempotent atomic update │
               └──────────────┬───────────────┘
                              │
                              ▼
               ┌──────────────────────────────┐
               │     Hermes Core Ready        │
               │  [Telemetry | Pipe Tables    │
               │   DB Healing | Quiet Stream  │
               │   Clean Think | Smart Split] │
               └──────────────────────────────┘
```

---

<a id="safety"></a>
## 🛡️ Production Safety Design

1. **🔬 Atomic Compilation Verification**: All transformations are performed in isolated temporary files and checked via Python's native `py_compile.compile(..., doraise=True)`. The target file is replaced atomically (`os.replace`) ONLY when syntax passes.
2. **🔄 100% Idempotent**: Safe to run repeatedly; signatures prevent duplicate code injection.
3. **💾 Automatic Mirror Backups (`.bak`)**: Automatically creates `.bak` backups before modifying any files, enabling instantaneous rollback.

---

<a id="installation"></a>
## 🚀 Quick Start (Installation)

### 1. Standard One-Line Install

Run on your Linux server hosting Hermes Agent:

```bash
curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/install.sh | bash
```

---

### 2. Selective & Modular Patching (Advanced)

Clone and run locally:

```bash
git clone https://github.com/shali10/hermes-patches.git
cd hermes-patches

# 1. List all available patch modules
python3 hermes_patches.py --list-patches

# 2. Preview changes (Dry Run)
python3 hermes_patches.py --dry-run -v

# 3. Apply only streaming control, clean thinking, and rich table bypass
python3 hermes_patches.py --only nostream clean-think table

# 4. Apply all patches EXCEPT menu localization
python3 hermes_patches.py --skip menu
```

---

<a id="patches"></a>
## 📦 Patch Registry

| Patch ID | Aliases | Target Files | Description |
|---|---|---|---|
| `footer` | `runtime-footer`, `token`, `stats` | `gateway/runtime_footer.py`<br>`gateway/run.py` | Full prompt, cache hit, output token, context %, and latency telemetry. |
| `table` | `cjk-table`, `telegram-table`, `pipe-table` | `plugins/platforms/telegram/adapter.py` | Bypasses desktop CJK rich text garble check to allow native pipe tables. |
| `menu` | `telegram-menu`, `menu-zh`, `i18n` | `hermes_cli/commands.py` | Localizes Telegram bot command descriptions into Chinese. |
| `db` | `state-db`, `sqlite`, `durability` | `hermes_state.py` | Injects `busy_timeout=5000` and session foreign key auto-healing. |
| `tirith` | `approval`, `security`, `low-warn` | `tools/approval.py` | Automatically passes through LOW/INFO static security warnings. |
| `nostream` | `no-stream`, `quiet-stream`, `stream-shield` | `gateway/run.py` | Honors `display.streaming: false` and shields against Telegram 429 flood limits. |
| `clean-think` | `think`, `reasoning`, `suppress-thinking` | `cli.py`<br>`gateway/stream_consumer.py` | Cleans thinking/reasoning tags and mutes noisy CLI thinking popups. |
| `smart-split` | `split`, `chunking`, `telegram-split` | `gateway/platforms/base.py` | Splits 4096+ char messages at paragraph breaks (`\n\n`) to preserve Markdown structure. |

---

<a id="changelog"></a>
## 📝 Changelog

| Version | Release Date | Key Updates | Link |
|:---:|:---:|---|:---:|
| **`v1.2.0`** | 2026-08-29 | Quiet streaming control (Telegram 429 shield), deep thinking suppression, 4096 smart chunking | [Details 📄](CHANGELOG.md#v120---2026-08-29) |
| **`v1.1.0`** | 2026-08-29 | Modular `--only` / `--skip` selection, Tirith low-warn bypass, bilingual docs & upstream CI | [Details 📄](CHANGELOG.md#v110---2026-08-29) |
| **`v1.0.0`** | 2026-08-29 | Token runtime footer, Telegram CJK native tables, menu localization, SQLite lock self-healing | [Details 📄](CHANGELOG.md#v100---2026-08-29) |

👉 **For complete release notes and history, see**: [CHANGELOG.md](CHANGELOG.md) or [GitHub Releases](https://github.com/shali10/hermes-patches/releases)

---

<a id="uninstall"></a>
## ↩️ Rollback & Uninstall

To cleanly revert all modifications:

```bash
bash install.sh --uninstall
```

---

<a id="contributing"></a>
## 📄 License

This project is licensed under the [MIT License](LICENSE).
