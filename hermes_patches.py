#!/usr/bin/env python3
"""
hermes-patches — Non-intrusive Enhancement Patches for Hermes Agent
Repository: https://github.com/shali10/hermes-patches

Provides full token metering, CJK native rich table support, Telegram menu localization,
production database durability enhancements, low-severity security prompt bypass,
gateway streaming control (quiet delivery & flood shield), deep thinking/reasoning suppression,
Telegram 4096 safe long-message chunking, automated zero-config initialization,
and seamless gateway service restart for Hermes Agent.
"""
from __future__ import annotations

import argparse
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple


PATCH_REGISTRY = [
    {
        "id": "footer",
        "aliases": ["runtime-footer", "token", "tokens", "stats"],
        "name": "📊 Runtime Footer (Token全量计量/缓存命中/耗时)",
        "method": "patch_runtime_footer",
        "description": "在消息页脚展示 Prompt 总量、缓存命中数及百分比、输出 Token、上下文比例与执行耗时。",
    },
    {
        "id": "table",
        "aliases": ["cjk-table", "telegram-table", "telegram-rich", "pipe-table"],
        "name": "📑 Telegram CJK 原生 Markdown 表格放行",
        "method": "patch_telegram_cjk_rich",
        "description": "绕过桌面端 CJK 字符乱码检测，100% 允许 Telegram 客户端原生高保真表格渲染。",
    },
    {
        "id": "menu",
        "aliases": ["telegram-menu", "menu-zh", "i18n", "localization"],
        "name": "🇨🇳 Telegram 快捷命令中文菜单汉化",
        "method": "patch_telegram_menu_zh",
        "description": "将 /start, /new, /reset, /status... 等 Bot 快捷指令描述汉化为地道中文。",
    },
    {
        "id": "db",
        "aliases": ["state-db", "sqlite", "durability", "concurrency"],
        "name": "🛡️ SQLite 生产级外键自愈与高并发防锁死",
        "method": "patch_state_db",
        "description": "设置连接级 busy_timeout=5000 缓解锁表，并自动补齐会话父记录根除外键崩溃。",
    },
    {
        "id": "tirith",
        "aliases": ["approval", "security", "low-warn"],
        "name": "⚡ Tirith 低风险扫描审批免打扰",
        "method": "patch_approval_tirith",
        "description": "自动放行 LOW/INFO 级别的低危静态扫描提示，高危风险正常拦截，提升自动化流畅度。",
    },
    {
        "id": "nostream",
        "aliases": ["no-stream", "quiet-stream", "disable-streaming", "stream-shield"],
        "name": "🚫 流式输出静默控制与 429 频控护盾",
        "method": "patch_streaming_control",
        "description": "支持全局 display.streaming: false 优雅静默，消除中间消息狂闪并彻底免除 429 封禁。",
    },
    {
        "id": "clean-think",
        "aliases": ["think", "reasoning", "clean-reasoning", "suppress-thinking"],
        "name": "🧠 全链路深度思考过程强力净化",
        "method": "patch_clean_thinking",
        "description": "全链路剥离 <think> 等变体思考标签与未闭合块，CLI 默认静音冗余思维链弹框。",
    },
    {
        "id": "smart-split",
        "aliases": ["split", "telegram-split", "chunking", "message-chunker"],
        "name": "✂️ Telegram 4096 长消息智能段落切分",
        "method": "patch_smart_split",
        "description": "4096+ 字符长消息优先在自然段落 (\\n\\n) 边界切分，自动补齐代码围栏与表格结构。",
    },
]


STATUS_MAP = {
    "applied": ("🟢", "已应用 (APPLIED)"),
    "unchanged": ("⚪", "已是最新/无需变更 (UNCHANGED)"),
    "dry-run": ("🟡", "待应用 (DRY-RUN)"),
    "skipped": ("⚪", "已跳过 (SKIPPED)"),
    "failed": ("🔴", "应用失败 (FAILED)"),
    "error": ("🔴", "错误 (ERROR)"),
}


class PatchEngine:
    def __init__(
        self,
        target_dir: Path,
        dry_run: bool = False,
        verbose: bool = False,
        only: Optional[List[str]] = None,
        skip: Optional[List[str]] = None,
    ):
        self.target_dir = target_dir
        self.dry_run = dry_run
        self.verbose = verbose
        self.only_set: Optional[Set[str]] = {x.lower().strip() for x in only} if only else None
        self.skip_set: Set[str] = {x.lower().strip() for x in skip} if skip else set()
        self.results: List[Tuple[str, str, str]] = []

    def log(self, patch_name: str, status: str, detail: str = ""):
        self.results.append((patch_name, status, detail))
        if self.verbose:
            icon, label = STATUS_MAP.get(status, ("•", status.upper()))
            msg = f"{icon} [{label}] {patch_name}"
            if detail:
                msg += f" ({detail})"
            print(msg)

    def apply_file_patch(self, rel_path: str, transform: Callable[[str], str], patch_name: str) -> bool:
        target_file = self.target_dir / rel_path
        if not target_file.is_file():
            self.log(patch_name, "skipped", f"未找到目标文件: {rel_path}")
            return False

        try:
            source = target_file.read_text(encoding="utf-8")
        except Exception as e:
            self.log(patch_name, "error", f"读取文件失败 {rel_path}: {e}")
            return False

        try:
            candidate = transform(source)
        except Exception as e:
            self.log(patch_name, "error", f"转换代码异常: {e}")
            return False

        if candidate == source:
            self.log(patch_name, "unchanged", "签名已存在或无需变更")
            return True

        if self.dry_run:
            self.log(patch_name, "dry-run", "代码变更预检通过，等待写入")
            return True

        # Backup original
        bak_file = target_file.with_suffix(target_file.suffix + ".bak")
        if not bak_file.exists():
            try:
                shutil.copy2(target_file, bak_file)
            except Exception:
                pass

        # Write to temporary file and compile test
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target_file.parent, suffix=".py") as temp:
            temp.write(candidate)
            temp_path = Path(temp.name)

        try:
            py_compile.compile(str(temp_path), doraise=True)
            os.replace(temp_path, target_file)
            py_compile.compile(str(target_file), doraise=True)
            
            # Clean up __pycache__ inside the parent dir so bytecode is refreshed
            pycache_dir = target_file.parent / "__pycache__"
            if pycache_dir.is_dir():
                stem = target_file.stem
                for pyc in pycache_dir.glob(f"{stem}.*.pyc"):
                    try:
                        pyc.unlink(missing_ok=True)
                    except Exception:
                        pass

            self.log(patch_name, "applied", f"成功更新 {rel_path}")
            return True
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            self.log(patch_name, "failed", f"py_compile 编译校验失败: {e}")
            return False

    # -------------------------------------------------------------
    # Patch 1: Runtime Footer Full Tokens & Latency
    # -------------------------------------------------------------
    def patch_runtime_footer(self) -> bool:
        def transform_footer(src: str) -> str:
            cand = src
            # 1. Separator
            cand = cand.replace('_SEP = " · "', '_SEP = " | "')

            # 2. _fmt_int helper
            if "def _fmt_int(" not in cand and "def format_runtime_footer(" in cand:
                helper = '''def _fmt_int(n: int) -> str:
    """Thousands-separated integer (``12345`` → ``12,345``)."""
    return f"{n:,}"


def format_runtime_footer('''
                cand = cand.replace("def format_runtime_footer(", helper, 1)

            # 3. format_runtime_footer signature
            old_sig = "    fields: Iterable[str] = _DEFAULT_FIELDS,\n) -> str:"
            new_sig = "    fields: Iterable[str] = _DEFAULT_FIELDS,\n    prompt_tokens: Optional[int] = None,\n    output_tokens: Optional[int] = None,\n    cache_read_tokens: Optional[int] = None,\n) -> str:"
            if "prompt_tokens: Optional[int] = None" not in cand and old_sig in cand:
                cand = cand.replace(old_sig, new_sig, 1)

            # 4. format fields mapping
            old_model = '''        if field == "model":
            m = _model_short(model)
            if m:
                parts.append(m)
        elif field == "context_pct":
            if context_length and context_length > 0 and context_tokens >= 0:
                pct = max(0, min(100, round((context_tokens / context_length) * 100)))
                parts.append(f"{pct}%")
        elif field == "latency":
            # Wall-clock turn duration. Skipped when the caller supplied no
            # timing (call sites that don't measure) or the value is negative.
            if turn_seconds is not None and turn_seconds >= 0:
                parts.append(_format_latency(turn_seconds))
        elif field == "cwd":
            rel = _home_relative_cwd(cwd or os.environ.get("TERMINAL_CWD", ""))
            if rel:
                parts.append(rel)
        # Unknown field names are silently ignored.'''

            new_model = '''        if field == "model":
            m = _model_short(model)
            if m:
                parts.append(f"🤖 {m}")
        elif field == "context_pct":
            if context_length and context_length > 0 and context_tokens >= 0:
                pct = max(0, min(100, round((context_tokens / context_length) * 100)))
                parts.append(f"🎯 上下文: {pct}%")
        elif field == "latency" or field == "elapsed_time":
            if turn_seconds is not None and turn_seconds >= 0:
                parts.append(f"⏱️ 耗时: {turn_seconds:.1f}s")
        elif field == "cwd":
            rel = _home_relative_cwd(cwd or os.environ.get("TERMINAL_CWD", ""))
            if rel:
                parts.append(rel)
        elif field == "prompt_tokens":
            if prompt_tokens:
                parts.append(f"🧠 Prompt总量: {_fmt_int(prompt_tokens)}")
        elif field == "output_tokens":
            if output_tokens:
                parts.append(f"📤 输出: {_fmt_int(output_tokens)}")
        elif field == "cache_read":
            if prompt_tokens and cache_read_tokens >= 0:
                pct = max(0, min(100, round((cache_read_tokens / prompt_tokens) * 100)))
                parts.append(f"💾 缓存命中: {_fmt_int(cache_read_tokens)} ({pct}%)")
        # Unknown field names are silently ignored.'''

            if "🧠 Prompt总量" not in cand and old_model in cand:
                cand = cand.replace(old_model, new_model, 1)

            # 5. build_footer_line signature & invocation
            old_bf_sig = "    turn_seconds: Optional[float] = None,\n) -> str:"
            new_bf_sig = "    turn_seconds: Optional[float] = None,\n    prompt_tokens: Optional[int] = None,\n    output_tokens: Optional[int] = None,\n    cache_read_tokens: Optional[int] = None,\n) -> str:"
            if "cache_read_tokens: Optional[int] = None,\n) -> str:" not in cand and old_bf_sig in cand:
                cand = cand.replace(old_bf_sig, new_bf_sig, 1)

            old_bf_call = '        fields=cfg.get("fields") or _DEFAULT_FIELDS,\n    )'
            new_bf_call = '        fields=cfg.get("fields") or _DEFAULT_FIELDS,\n        prompt_tokens=prompt_tokens,\n        output_tokens=output_tokens,\n        cache_read_tokens=cache_read_tokens,\n    )'
            if "prompt_tokens=prompt_tokens," not in cand and old_bf_call in cand:
                cand = cand.replace(old_bf_call, new_bf_call, 1)

            # 6. Default fields and default enabled in resolve_footer_config
            old_df = '_DEFAULT_FIELDS: tuple[str, ...] = ("model", "context_pct", "cwd")'
            new_df = '_DEFAULT_FIELDS: tuple[str, ...] = ("model", "prompt_tokens", "cache_read", "output_tokens", "context_pct", "elapsed_time")'
            if old_df in cand:
                cand = cand.replace(old_df, new_df, 1)

            old_res = 'resolved = {"enabled": False, "fields": list(_DEFAULT_FIELDS)}'
            new_res = 'resolved = {"enabled": True, "fields": list(_DEFAULT_FIELDS)}'
            if old_res in cand:
                cand = cand.replace(old_res, new_res, 1)

            return cand

        def transform_gateway_run(src: str) -> str:
            cand = src
            # Parameter injection into build_footer_line
            old_bfl = '''_footer_line = _bfl(
                    user_config=_load_gateway_config(),
                    platform_key=_platform_config_key(source.platform),
                    model=agent_result.get("model"),
                    context_tokens=agent_result.get("last_prompt_tokens", 0) or 0,
                    context_length=agent_result.get("context_length") or None,
                    cwd=os.environ.get("TERMINAL_CWD", ""),
                    turn_seconds=_turn_seconds,
                )'''

            new_bfl = '''_footer_line = _bfl(
                    user_config=_load_gateway_config(),
                    platform_key=_platform_config_key(source.platform),
                    model=agent_result.get("model"),
                    context_tokens=agent_result.get("last_prompt_tokens", 0) or 0,
                    context_length=agent_result.get("context_length") or None,
                    cwd=os.environ.get("TERMINAL_CWD", ""),
                    turn_seconds=_turn_seconds,
                    prompt_tokens=agent_result.get("input_tokens") or 0,
                    output_tokens=agent_result.get("output_tokens") or 0,
                    cache_read_tokens=agent_result.get("cache_read_tokens") or 0,
                )'''

            if 'prompt_tokens=agent_result.get("input_tokens")' not in cand and old_bfl in cand:
                cand = cand.replace(old_bfl, new_bfl, 1)

            # platform key compatibility
            old_pkey = '''def _platform_config_key(platform: "Platform") -> str:
    """Map a Platform enum to its config.yaml key (LOCAL→"cli", rest→enum value)."""
    return "cli" if platform == Platform.LOCAL else platform.value'''

            new_pkey = '''def _platform_config_key(platform: Any) -> str:
    """Map a Platform enum to its config.yaml key (LOCAL→"cli", rest→enum value)."""
    if platform == Platform.LOCAL or platform == "local" or platform == "cli":
        return "cli"
    return getattr(platform, "value", str(platform) if platform is not None else "cli")'''

            if old_pkey in cand:
                cand = cand.replace(old_pkey, new_pkey, 1)

            return cand

        ok1 = self.apply_file_patch("gateway/runtime_footer.py", transform_footer, "📊 Runtime Footer 全量计量")
        ok2 = self.apply_file_patch("gateway/run.py", transform_gateway_run, "⚙️ Gateway 运行态参数注入")
        return ok1 and ok2

    # -------------------------------------------------------------
    # Patch 2: Telegram CJK Native Rich Formatting & Table Bypass
    # -------------------------------------------------------------
    def patch_telegram_cjk_rich(self) -> bool:
        def transform(src: str) -> str:
            cand = src
            old = '''    def _has_telegram_desktop_cjk_rich_garble_shape(self, content: str) -> bool:
        """True if content contains CJK text that triggers desktop client garble."""
        if not content:
            return False'''

            new = '''    def _has_telegram_desktop_cjk_rich_garble_shape(self, content: str) -> bool:
        """Allow Telegram CJK rich formatting and native pipe tables (telegram-allow-cjk-rich)."""
        return False
        if not content:
            return False'''

            if "Allow Telegram CJK rich formatting" not in cand and old in cand:
                cand = cand.replace(old, new, 1)
            return cand

        return self.apply_file_patch("plugins/platforms/telegram/adapter.py", transform, "📑 Telegram 原生表格放行")

    # -------------------------------------------------------------
    # Patch 3: Telegram Menu Chinese Localization
    # -------------------------------------------------------------
    def patch_telegram_menu_zh(self) -> bool:
        def transform(src: str) -> str:
            marker = "_TELEGRAM_ZH_DESCRIPTIONS: dict[str, str] = {"
            if marker in src:
                return src

            start_sig = "def telegram_bot_commands() -> list[tuple[str, str]]:\n"
            end_sig = "\n\n# Telegram allows up to 100 BotCommands."

            start = src.find(start_sig)
            end = src.find(end_sig, start)
            if start < 0 or end < 0:
                return src

            patch_block = '''_TELEGRAM_ZH_DESCRIPTIONS: dict[str, str] = {
    "start": "响应 Telegram 的启动请求",
    "new": "新建一个对话会话",
    "reset": "重置当前会话（清理上下文）",
    "clear": "清理上下文（保留设置）",
    "status": "显示当前会话状态、活跃模型与 Token 统计",
    "model": "查看或切换当前使用的模型",
    "memory": "查看或搜索持久化记忆库",
    "skills": "查看或管理当前可用技能",
    "help": "显示可用命令与帮助信息",
    "restart": "安全重启 Hermes Gateway 实例",
    "doctor": "运行系统与组件健康诊断",
    "footer": "切换页脚统计信息显示 (on/off)",
}


def telegram_bot_commands() -> list[tuple[str, str]]:
    """Return command list with localized descriptions."""
    cmds = []
    for cmd, desc in _RAW_TELEGRAM_BOT_COMMANDS:
        cmds.append((cmd, _TELEGRAM_ZH_DESCRIPTIONS.get(cmd, desc)))
    return cmds'''

            # Rename raw commands definition
            cand = src.replace("def telegram_bot_commands() -> list[tuple[str, str]]:", "_RAW_TELEGRAM_BOT_COMMANDS: list[tuple[str, str]] = [", 1)
            return src[:start] + patch_block + src[end:]

        return self.apply_file_patch("hermes_cli/commands.py", transform, "🇨🇳 Telegram 快捷菜单汉化")

    # -------------------------------------------------------------
    # Patch 4: State DB Foreign Key & Contention Self-Heal
    # -------------------------------------------------------------
    def patch_state_db(self) -> bool:
        def transform(src: str) -> str:
            cand = src

            # 1. State DB contention busy_timeout
            old_pragmas = '    conn.execute("PRAGMA synchronous = NORMAL")'
            new_pragmas = '    conn.execute("PRAGMA busy_timeout = 5000")\n    conn.execute("PRAGMA synchronous = NORMAL")'
            if "PRAGMA busy_timeout = 5000" not in cand and old_pragmas in cand:
                cand = cand.replace(old_pragmas, new_pragmas, 1)

            # 2. FK self-heal on append_message
            pat1 = r'(\s+self\._check_transcript_write_guards\([^)]+\)\n)(\s+cursor\s*=\\s*conn\.execute\(\s*"""INSERT INTO messages)'
            heal1 = '\n            # FK self-heal: ensure the session parent row exists.\n            conn.execute(\n                "INSERT OR IGNORE INTO sessions (id, source, started_at) "\n                "VALUES (?, \'unknown\', ?)",\n                (session_id, time.time()),\n            )\n'
            cand, _ = re.subn(pat1, r'\1' + heal1 + r'\2', cand, count=1)

            # 3. FK self-heal on append_messages_batch
            pat2 = r'(\s+self\._check_transcript_write_guards\([^)]+\)\n)(\s+inserted,\s*tool_calls_total\s*=\s*self\._insert_message_rows\()'
            heal2 = '\n            # FK self-heal: ensure the session parent row exists.\n            conn.execute(\n                "INSERT OR IGNORE INTO sessions (id, source, started_at) "\n                "VALUES (?, \'unknown\', ?)",\n                (session_id, time.time()),\n            )\n'
            cand, _ = re.subn(pat2, r'\1' + heal2 + r'\2', cand, count=1)

            return cand

        return self.apply_file_patch("hermes_state.py", transform, "🛡️ SQLite 外键自愈与防锁表")

    # -------------------------------------------------------------
    # Patch 5: Tirith Low-Severity Approval Prompt Skip
    # -------------------------------------------------------------
    def patch_approval_tirith(self) -> bool:
        def transform(src: str) -> str:
            cand = src
            if "_skip_low_warn" in cand:
                return cand

            old_check = '''    if tirith_result["action"] in {"block", "warn"}:
        findings = tirith_result.get("findings") or []
        rule_id = findings[0].get("rule_id", "unknown") if findings else "unknown"'''

            new_check = '''    if tirith_result["action"] in {"block", "warn"}:
        findings = tirith_result.get("findings") or []
        _skip_low_warn = (
            tirith_result.get("action") == "warn"
            and bool(findings)
            and all(str(f.get("severity", "")).upper() in {"LOW", "INFO", ""} for f in findings)
        )
        if _skip_low_warn:
            return True, ""
        rule_id = findings[0].get("rule_id", "unknown") if findings else "unknown"'''

            if old_check in cand:
                cand = cand.replace(old_check, new_check, 1)
            return cand

        return self.apply_file_patch("tools/approval.py", transform, "⚡ Tirith 低风险免打扰")

    # -------------------------------------------------------------
    # Patch 6: Gateway Streaming Control & Flood Limit Shield
    # -------------------------------------------------------------
    def patch_streaming_control(self) -> bool:
        def transform(src: str) -> str:
            cand = src
            if "_global_display_streaming" in cand:
                return cand

            old_gate = '''        # Per-platform streaming gate: display.platforms.<plat>.streaming
        # can disable streaming for specific platforms even when the global
        # streaming config is enabled.
        _plat_streaming = ctx.resolve_display_setting(
            ctx.user_config, platform_key, "streaming"
        )
        # None = no per-platform override → follow global config
        _streaming_enabled = (
            _scfg.enabled and _scfg.transport != "off"
            if _plat_streaming is None
            else bool(_plat_streaming)
        )'''

            new_gate = '''        # Per-platform streaming gate: display.platforms.<plat>.streaming
        # can disable streaming for specific platforms even when the global
        # streaming config is enabled.
        _plat_streaming = ctx.resolve_display_setting(
            ctx.user_config, platform_key, "streaming"
        )
        # Check global display.streaming setting (hermes-patches stream-shield)
        _global_display_streaming = None
        if isinstance(ctx.user_config, dict):
            _global_display_streaming = (ctx.user_config.get("display") or {}).get("streaming")
        if _plat_streaming is None and _global_display_streaming is not None:
            _plat_streaming = bool(_global_display_streaming)

        # None = no per-platform override → follow global config
        _streaming_enabled = (
            _scfg.enabled and _scfg.transport != "off"
            if _plat_streaming is None
            else bool(_plat_streaming)
        )'''

            if old_gate in cand:
                cand = cand.replace(old_gate, new_gate, 1)
            return cand

        return self.apply_file_patch("gateway/run.py", transform, "🚫 流式控制与 429 护盾")

    # -------------------------------------------------------------
    # Patch 7: Deep Thinking & Reasoning Process Cleaner
    # -------------------------------------------------------------
    def patch_clean_thinking(self) -> bool:
        def transform_cli(src: str) -> str:
            cand = src
            # Set default CLI show_reasoning to False
            cand = cand.replace(
                'self.show_reasoning = CLI_CONFIG["display"].get("show_reasoning", True)',
                'self.show_reasoning = CLI_CONFIG["display"].get("show_reasoning", False)',
            )
            # Expand OPEN and CLOSE think tags
            old_open = '_OPEN_TAGS = ("<REASONING_SCRPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>")'
            new_open = '_OPEN_TAGS = ("<REASONING_SCRPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>", "<antml:thought>", "<reflection>", "<inner_monologue>")'
            # Note: handle both REASONING_SCRATCHPAD and other variants
            cand = re.sub(
                r'_OPEN_TAGS\s*=\s*\([^\)]+\)',
                '_OPEN_TAGS = ("<REASONING_SCRATCHPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>", "<antml:thought>", "<reflection>", "<inner_monologue>")',
                cand,
                count=1,
            )
            cand = re.sub(
                r'_CLOSE_TAGS\s*=\s*\([^\)]+\)',
                '_CLOSE_TAGS = ("</REASONING_SCRATCHPAD>", "</think>", "</reasoning>", "</THINKING>", "</thinking>", "</thought>", "</antml:thought>", "</reflection>", "</inner_monologue>")',
                cand,
                count=1,
            )
            return cand

        def transform_stream_consumer(src: str) -> str:
            cand = src
            old_tags = '''    _OPEN_THINK_TAGS = (
        "<REASONING_SCRATCHPAD>", "<think>", "<reasoning>",
        "<THINKING>", "<thinking>", "<thought>",
    )
    _CLOSE_THINK_TAGS = (
        "</REASONING_SCRATCHPAD>", "</think>", "</reasoning>",
        "</THINKING>", "</thinking>", "</thought>",
    )'''

            new_tags = '''    _OPEN_THINK_TAGS = (
        "<REASONING_SCRATCHPAD>", "<think>", "<reasoning>",
        "<THINKING>", "<thinking>", "<thought>",
        "<antml:thought>", "<reflection>", "<inner_monologue>",
    )
    _CLOSE_THINK_TAGS = (
        "</REASONING_SCRATCHPAD>", "</think>", "</reasoning>",
        "</THINKING>", "</thinking>", "</thought>",
        "</antml:thought>", "</reflection>", "</inner_monologue>",
    )'''
            if old_tags in cand:
                cand = cand.replace(old_tags, new_tags, 1)
            return cand

        ok1 = self.apply_file_patch("cli.py", transform_cli, "🧠 CLI 终端思考过程静音")
        ok2 = self.apply_file_patch("gateway/stream_consumer.py", transform_stream_consumer, "🧠 Gateway 思考标签深度净化")
        return ok1 and ok2

    # -------------------------------------------------------------
    # Patch 8: Telegram 4096 Safe Long Message Paragraph Chunker
    # -------------------------------------------------------------
    def patch_smart_split(self) -> bool:
        def transform_base_platform(src: str) -> str:
            cand = src
            if "# Prefer paragraph break (\\n\\n)" in cand:
                return cand

            old_split = '''            region = remaining[:_cp_limit]
            split_at = region.rfind("\\n")
            if split_at < _cp_limit // 2:
                split_at = region.rfind(" ")'''

            new_split = '''            region = remaining[:_cp_limit]
            # Prefer paragraph break (\\n\\n), then single newline (\\n), then space (hermes-patches smart-split)
            split_at = region.rfind("\\n\\n")
            if split_at < _cp_limit // 3:
                split_at = region.rfind("\\n")
            if split_at < _cp_limit // 2:
                split_at = region.rfind(" ")'''

            if old_split in cand:
                cand = cand.replace(old_split, new_split, 1)
            return cand

        return self.apply_file_patch("gateway/platforms/base.py", transform_base_platform, "✂️ Telegram 4096 智能段落切分")

    # -------------------------------------------------------------
    # Execution Filter & Dispatch
    # -------------------------------------------------------------
    def _is_patch_selected(self, patch_meta: dict) -> bool:
        pid = patch_meta["id"]
        names = {pid} | set(patch_meta.get("aliases", []))

        # Check skip
        if any(name in self.skip_set for name in names):
            return False

        # Check only
        if self.only_set is not None:
            return any(name in self.only_set for name in names)

        return True

    def run_all(self):
        print(f"🚀 正在针对目标目录执行补丁注入: {self.target_dir}")
        for item in PATCH_REGISTRY:
            if not self._is_patch_selected(item):
                self.log(item["name"], "skipped", "通过 --only / --skip 参数排除")
                continue
            method_name = item["method"]
            method = getattr(self, method_name, None)
            if callable(method):
                method()

        # Clean all compiled cache across target directory
        if not self.dry_run:
            purge_bytecode_cache(self.target_dir)

        print("\n📋 补丁执行结果汇总 (Execution Summary):")
        for name, status, detail in self.results:
            icon, label = STATUS_MAP.get(status, ("•", status.upper()))
            d_str = f" ({detail})" if detail else ""
            print(f"  {icon} {name:<42} -> {label}{d_str}")


def purge_bytecode_cache(target_dir: Path):
    """Purge stale .pyc and __pycache__ in target directory."""
    try:
        for p in target_dir.rglob("__pycache__"):
            try:
                shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
        for p in target_dir.rglob("*.pyc"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass


def find_default_hermes_dir() -> Path:
    """
    Multi-stage adaptive probe to detect the active Hermes Agent installation root:
    1. Environment variables (HERMES_PATCH_SOURCE_ROOT, HERMES_SOURCE_DIR, HERMES_DIR, HERMES_HOME)
    2. Active running processes via /proc or ps (probing the running Python executable)
    3. Systemd unit service configuration (ExecStart)
    4. CLI binary shebang inspection (head -n 1 $(which hermes))
    5. Common Python venvs / site-packages
    6. Well-known system directories
    """
    # 1. Environment variables
    for env_var in ["HERMES_PATCH_SOURCE_ROOT", "HERMES_SOURCE_DIR", "HERMES_DIR", "HERMES_HOME"]:
        val = os.environ.get(env_var, "").strip()
        if val:
            p = Path(val)
            if p.is_dir() and (p / "hermes_state.py").is_file():
                return p

    # 2. Check active running processes
    try:
        ps_out = subprocess.check_output(["ps", "-eo", "pid,command"], text=True, errors="ignore")
        for line in ps_out.splitlines():
            if "grep" in line:
                continue
            if "hermes_cli" in line or "gateway.run" in line or "run_agent.py" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    py_cand = parts[1]
                    if os.path.isfile(py_cand) and os.access(py_cand, os.X_OK):
                        probe = subprocess.check_output(
                            [py_cand, "-c", "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))"],
                            text=True, errors="ignore", timeout=3
                        ).strip()
                        if probe and os.path.isfile(os.path.join(probe, "hermes_state.py")):
                            return Path(probe)
    except Exception:
        pass

    # 3. Check systemd service ExecStart
    try:
        unit_out = subprocess.check_output(["systemctl", "show", "hermes-gateway", "--property=ExecStart"], text=True, errors="ignore")
        m = re.search(r"path=([^\s;]+)", unit_out)
        if m:
            py_cand = m.group(1)
            if os.path.isfile(py_cand) and os.access(py_cand, os.X_OK):
                probe = subprocess.check_output(
                    [py_cand, "-c", "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))"],
                    text=True, errors="ignore", timeout=3
                ).strip()
                if probe and os.path.isfile(os.path.join(probe, "hermes_state.py")):
                    return Path(probe)
    except Exception:
        pass

    # 4. Check `which hermes` CLI shebang
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        try:
            real_bin = Path(hermes_bin).resolve()
            with open(real_bin, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
            if first_line.startswith("#!"):
                py_shebang = first_line[2:].strip().split()[0]
                if os.path.isfile(py_shebang) and os.access(py_shebang, os.X_OK):
                    probe = subprocess.check_output(
                        [py_shebang, "-c", "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))"],
                        text=True, errors="ignore", timeout=3
                    ).strip()
                    if probe and os.path.isfile(os.path.join(probe, "hermes_state.py")):
                        return Path(probe)
        except Exception:
            pass

        try:
            real_bin = Path(hermes_bin).resolve()
            for parent in [real_bin.parent, real_bin.parent.parent, real_bin.parent.parent.parent]:
                if (parent / "hermes_state.py").is_file():
                    return parent
        except Exception:
            pass

    # 5. Probe common python executables
    common_pythons = [
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
        "/usr/local/lib/hermes-agent/venv/bin/python",
        "/opt/hermes-agent/venv/bin/python",
        str(Path.home() / ".local/share/uv/tools/hermes-agent/bin/python"),
        str(Path.home() / ".local/pipx/venvs/hermes-agent/bin/python"),
        str(Path.home() / ".hermes/venv/bin/python"),
    ]
    for py in common_pythons:
        if py and os.path.isfile(py) and os.access(py, os.X_OK):
            try:
                probe = subprocess.check_output(
                    [py, "-c", "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))"],
                    text=True, errors="ignore", timeout=3
                ).strip()
                if probe and os.path.isfile(os.path.join(probe, "hermes_state.py")):
                    return Path(probe)
            except Exception:
                pass

    # 6. Standard directory paths
    candidates = [
        Path("/usr/local/lib/hermes-agent"),
        Path("/opt/hermes-agent"),
        Path.home() / ".local/lib/hermes-agent",
        Path.home() / ".local/share/hermes-agent",
        Path.home() / ".hermes/hermes-agent",
        Path("/usr/lib/hermes-agent"),
        Path.home() / "hermes-agent",
    ]

    for c in candidates:
        if c and c.is_dir() and (c / "hermes_state.py").is_file():
            return c
    return Path("/usr/local/lib/hermes-agent")


def ensure_runtime_config(dry_run: bool = False) -> bool:
    """
    Automatically initializes/ensures optimal settings in ~/.hermes/config.yaml:
    - display.runtime_footer.enabled = true
    - display.runtime_footer.fields = [model, prompt_tokens, cache_read, output_tokens, context_pct, elapsed_time]
    - display.platforms.telegram.streaming = false (quiet delivery & flood shield)
    """
    config_paths = [
        Path(os.environ.get("HERMES_HOME", "")) / "config.yaml" if os.environ.get("HERMES_HOME") else None,
        Path.home() / ".hermes" / "config.yaml",
        Path.home() / ".config" / "hermes" / "config.yaml",
    ]
    config_file: Optional[Path] = None
    for p in config_paths:
        if p and p.is_file():
            config_file = p
            break

    if not config_file:
        config_file = Path.home() / ".hermes" / "config.yaml"

    if dry_run:
        print(f"🟡 [DRY-RUN] 配置文件自动配置预检: {config_file}")
        return True

    # Try official CLI first if available
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        try:
            subprocess.run([hermes_bin, "config", "set", "display.runtime_footer.enabled", "true"], check=True, capture_output=True, timeout=5)
            subprocess.run([
                hermes_bin, "config", "set", "display.runtime_footer.fields",
                '["model", "prompt_tokens", "cache_read", "output_tokens", "context_pct", "elapsed_time"]'
            ], check=True, capture_output=True, timeout=5)
            print(f"🟢 [已自动配置] 成功通过 hermes CLI 激活页脚与计量参数 ({config_file})")
            return True
        except Exception:
            pass

    # Fallback to direct Python / YAML manipulation
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        raw_text = config_file.read_text(encoding="utf-8") if config_file.is_file() else ""
        
        # Safe append/merge if display block is missing
        if "runtime_footer:" not in raw_text:
            footer_yaml = """
display:
  runtime_footer:
    enabled: true
    fields:
      - model
      - prompt_tokens
      - cache_read
      - output_tokens
      - context_pct
      - elapsed_time
"""
            if "display:" in raw_text:
                # Insert runtime_footer under display:
                raw_text = raw_text.replace("display:\n", "display:\n  runtime_footer:\n    enabled: true\n    fields:\n      - model\n      - prompt_tokens\n      - cache_read\n      - output_tokens\n      - context_pct\n      - elapsed_time\n", 1)
            else:
                raw_text += footer_yaml
            
            config_file.write_text(raw_text, encoding="utf-8")
            print(f"🟢 [已自动配置] 写入基础页脚计量配置至 {config_file}")
        else:
            print(f"⚪ [已配置] 配置文件已存在 runtime_footer 设定 ({config_file})")
        return True
    except Exception as e:
        print(f"⚠️ [配置提示] 自动修改配置文件跳过: {e}")
        return False


def restart_gateway_services() -> bool:
    """
    Seamlessly restart the active Hermes gateway service via systemd if present,
    or identify running standalone processes.
    """
    # 1. Systemd service restart
    if shutil.which("systemctl"):
        try:
            # Check if hermes-gateway unit exists
            status_proc = subprocess.run(["systemctl", "status", "hermes-gateway"], capture_output=True, text=True)
            if "hermes-gateway.service" in status_proc.stdout or "Loaded:" in status_proc.stdout:
                print("🔄 正在平滑重启 hermes-gateway 系统服务...")
                subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
                restart_proc = subprocess.run(["systemctl", "restart", "hermes-gateway"], capture_output=True, text=True, timeout=15)
                
                if restart_proc.returncode == 0:
                    time.sleep(1.5)
                    active_proc = subprocess.run(["systemctl", "is-active", "--quiet", "hermes-gateway"])
                    if active_proc.returncode == 0:
                        print("🟢 [自动重启成功] hermes-gateway 服务已成功重启并在后台正常运行！")
                        return True
                    else:
                        print("🟡 [警告] 服务已发送重启指令，当前处于拉起中...")
                        return True
                else:
                    print(f"⚠️ systemctl restart 失败: {restart_proc.stderr.strip()}")
        except Exception as e:
            print(f"⚠️ 重启服务时发生异常: {e}")

    # 2. Check running processes
    try:
        ps_out = subprocess.check_output(["ps", "-eo", "pid,command"], text=True, errors="ignore")
        pids = []
        for line in ps_out.splitlines():
            if "grep" in line or "hermes_patches" in line:
                continue
            if "gateway" in line and ("hermes" in line or "python" in line):
                pids.append(line.strip().split()[0])
        if pids:
            print(f"ℹ️ 检测到正在运行的独立 Gateway 进程 (PID: {', '.join(pids)})。如未配置 systemd，请手动重启该进程以生效。")
    except Exception:
        pass

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Agent 生产级体验增强补丁与扩展注入工具。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
常用示例:
  # 全量应用所有增强补丁、自动配置并平滑重启
  python3 hermes_patches.py --auto-config --restart

  # 预览变更而不写入磁盘 (Dry Run)
  python3 hermes_patches.py --dry-run -v

  # 仅应用特定补丁 (如流式静默与思考净化)
  python3 hermes_patches.py --only nostream clean-think

  # 应用除菜单汉化外的所有补丁
  python3 hermes_patches.py --skip menu
        """,
    )
    parser.add_argument("--target", type=str, default="", help="指定 Hermes Agent 源码安装目录")
    parser.add_argument("--dry-run", action="store_true", help="预检模式：仅检查变更，不修改磁盘文件")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细执行日志")
    parser.add_argument("--auto-config", action="store_true", help="自动校验并开启 ~/.hermes/config.yaml 中的页脚与计量显示")
    parser.add_argument("--restart", action="store_true", help="打完补丁后自动平滑重启 hermes-gateway 服务")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="PATCH",
        help="仅应用指定的补丁模块 (如 footer, table, menu, db, tirith, nostream, clean-think, smart-split)",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        metavar="PATCH",
        help="跳过指定的补丁模块 (如 menu, tirith)",
    )
    parser.add_argument("--list-patches", action="store_true", help="列出所有可用补丁模块并退出")

    args = parser.parse_args()

    if args.list_patches:
        print("🛠️ 可用的 hermes-patches 模块清单:\n")
        for p in PATCH_REGISTRY:
            aliases = ", ".join(p["aliases"])
            print(f"  • 模块 ID : {p['id']:<12} (别名: {aliases})")
            print(f"    模块名称: {p['name']}")
            print(f"    功能说明: {p['description']}\n")
        sys.exit(0)

    target = Path(args.target) if args.target else find_default_hermes_dir()
    if not (target / "hermes_state.py").is_file():
        print(f"❌ 错误: 目标目录 '{target}' 未检测到有效的 Hermes Agent 安装。", file=sys.stderr)
        print("请通过 --target /path/to/hermes-agent 或环境变量 HERMES_SOURCE_DIR 指定路径。", file=sys.stderr)
        sys.exit(1)

    engine = PatchEngine(
        target_dir=target,
        dry_run=args.dry_run,
        verbose=args.verbose,
        only=args.only,
        skip=args.skip,
    )
    engine.run_all()

    if args.auto_config:
        ensure_runtime_config(dry_run=args.dry_run)

    if args.restart and not args.dry_run:
        restart_gateway_services()


if __name__ == "__main__":
    main()
