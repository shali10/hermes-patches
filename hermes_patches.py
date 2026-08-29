#!/usr/bin/env python3
"""
hermes-patches — Non-intrusive Enhancement Patches for Hermes Agent
Repository: https://github.com/shali10/hermes-patches

Provides full token metering, CJK native rich table support, Telegram menu localization,
production database durability enhancements, low-severity security prompt bypass,
gateway streaming control (quiet delivery & flood shield), deep thinking/reasoning suppression,
and Telegram 4096 safe long-message chunking for Hermes Agent.
"""
from __future__ import annotations

import argparse
import os
import py_compile
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple


PATCH_REGISTRY = [
    {
        "id": "footer",
        "aliases": ["runtime-footer", "token", "tokens", "stats"],
        "name": "Runtime Footer (Full Tokens, Cache Hit, Percent & Latency)",
        "method": "patch_runtime_footer",
        "description": "Exposes prompt tokens, cache hits, output tokens, context %, and latency in message footer.",
    },
    {
        "id": "table",
        "aliases": ["cjk-table", "telegram-table", "telegram-rich", "pipe-table"],
        "name": "Telegram CJK Native Pipe Table Bypass",
        "method": "patch_telegram_cjk_rich",
        "description": "Bypasses desktop CJK rich text garble check to allow modern native pipe tables.",
    },
    {
        "id": "menu",
        "aliases": ["telegram-menu", "menu-zh", "i18n", "localization"],
        "name": "Telegram Bot Command Menu Localization (Chinese)",
        "method": "patch_telegram_menu_zh",
        "description": "Translates default /start, /new, /reset, /status... bot menu descriptions to Chinese.",
    },
    {
        "id": "db",
        "aliases": ["state-db", "sqlite", "durability", "concurrency"],
        "name": "SQLite State DB Durability & Foreign Key Auto-Healing",
        "method": "patch_state_db",
        "description": "Sets busy_timeout=5000 and auto-heals orphan session rows during high concurrency.",
    },
    {
        "id": "tirith",
        "aliases": ["approval", "security", "low-warn"],
        "name": "Tirith Low-Severity Approval Prompt Bypass",
        "method": "patch_approval_tirith",
        "description": "Automatically approves non-blocking LOW/INFO security scanner warnings.",
    },
    {
        "id": "nostream",
        "aliases": ["no-stream", "quiet-stream", "disable-streaming", "stream-shield"],
        "name": "Gateway Streaming Control & Telegram Flood Limit Shield",
        "method": "patch_streaming_control",
        "description": "Honors global display.streaming configuration and prevents Telegram 429 Flood Control edits.",
    },
    {
        "id": "clean-think",
        "aliases": ["think", "reasoning", "clean-reasoning", "suppress-thinking"],
        "name": "Deep Thinking & Reasoning Process Cleaner",
        "method": "patch_clean_thinking",
        "description": "Suppresses noisy thinking/reasoning blocks (<think>, <thought>, etc.) in CLI and messaging platforms.",
    },
    {
        "id": "smart-split",
        "aliases": ["split", "telegram-split", "chunking", "message-chunker"],
        "name": "Telegram 4096 Safe Long Message Paragraph Chunker",
        "method": "patch_smart_split",
        "description": "Splits 4096+ char messages at paragraph breaks to preserve Markdown tables and code fences.",
    },
]


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
            msg = f"[{status.upper()}] {patch_name}"
            if detail:
                msg += f" ({detail})"
            print(msg)

    def apply_file_patch(self, rel_path: str, transform: Callable[[str], str], patch_name: str) -> bool:
        target_file = self.target_dir / rel_path
        if not target_file.is_file():
            self.log(patch_name, "skipped", f"file not found: {rel_path}")
            return False

        try:
            source = target_file.read_text(encoding="utf-8")
        except Exception as e:
            self.log(patch_name, "error", f"failed to read {rel_path}: {e}")
            return False

        try:
            candidate = transform(source)
        except Exception as e:
            self.log(patch_name, "error", f"transform exception: {e}")
            return False

        if candidate == source:
            self.log(patch_name, "unchanged", "already applied or shape not matched")
            return True

        if self.dry_run:
            self.log(patch_name, "dry-run", "changes ready to apply")
            return True

        # Backup original
        bak_file = target_file.with_suffix(target_file.suffix + ".bak")
        if not bak_file.exists():
            shutil.copy2(target_file, bak_file)

        # Write to temporary file and compile test
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target_file.parent, suffix=".py") as temp:
            temp.write(candidate)
            temp_path = Path(temp.name)

        try:
            py_compile.compile(str(temp_path), doraise=True)
            os.replace(temp_path, target_file)
            py_compile.compile(str(target_file), doraise=True)
            self.log(patch_name, "applied", f"updated {rel_path}")
            return True
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            self.log(patch_name, "failed", f"py_compile error: {e}")
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

        ok1 = self.apply_file_patch("gateway/runtime_footer.py", transform_footer, "runtime-footer-cjk")
        ok2 = self.apply_file_patch("gateway/run.py", transform_gateway_run, "gateway-run-footer-wiring")
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

        return self.apply_file_patch("plugins/platforms/telegram/adapter.py", transform, "telegram-allow-cjk-rich")

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

        return self.apply_file_patch("hermes_cli/commands.py", transform, "telegram-menu-zh")

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
            pat1 = r'(\s+self\._check_transcript_write_guards\([^)]+\)\n)(\s+cursor\s*=\s*conn\.execute\(\s*"""INSERT INTO messages)'
            heal1 = '\n            # FK self-heal: ensure the session parent row exists.\n            conn.execute(\n                "INSERT OR IGNORE INTO sessions (id, source, started_at) "\n                "VALUES (?, \'unknown\', ?)",\n                (session_id, time.time()),\n            )\n'
            cand, _ = re.subn(pat1, r'\1' + heal1 + r'\2', cand, count=1)

            # 3. FK self-heal on append_messages_batch
            pat2 = r'(\s+self\._check_transcript_write_guards\([^)]+\)\n)(\s+inserted,\s*tool_calls_total\s*=\s*self\._insert_message_rows\()'
            heal2 = '\n            # FK self-heal: ensure the session parent row exists.\n            conn.execute(\n                "INSERT OR IGNORE INTO sessions (id, source, started_at) "\n                "VALUES (?, \'unknown\', ?)",\n                (session_id, time.time()),\n            )\n'
            cand, _ = re.subn(pat2, r'\1' + heal2 + r'\2', cand, count=1)

            return cand

        return self.apply_file_patch("hermes_state.py", transform, "state-db-durability")

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

        return self.apply_file_patch("tools/approval.py", transform, "approval-low-tirith-warn-skip")

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

        return self.apply_file_patch("gateway/run.py", transform, "gateway-streaming-control")

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
            old_open = '_OPEN_TAGS = ("<REASONING_SCRATCHPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>")'
            new_open = '_OPEN_TAGS = ("<REASONING_SCRATCHPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>", "<antml:thought>", "<reflection>", "<inner_monologue>")'
            if old_open in cand:
                cand = cand.replace(old_open, new_open, 1)

            old_close = '_CLOSE_TAGS = ("</REASONING_SCRATCHPAD>", "</think>", "</reasoning>", "</THINKING>", "</thinking>", "</thought>")'
            new_close = '_CLOSE_TAGS = ("</REASONING_SCRATCHPAD>", "</think>", "</reasoning>", "</THINKING>", "</thinking>", "</thought>", "</antml:thought>", "</reflection>", "</inner_monologue>")'
            if old_close in cand:
                cand = cand.replace(old_close, new_close, 1)

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

        ok1 = self.apply_file_patch("cli.py", transform_cli, "cli-clean-thinking")
        ok2 = self.apply_file_patch("gateway/stream_consumer.py", transform_stream_consumer, "stream-consumer-clean-thinking")
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

        return self.apply_file_patch("gateway/platforms/base.py", transform_base_platform, "platform-smart-split")

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
        print(f"🚀 Running hermes-patches against: {self.target_dir}")
        for item in PATCH_REGISTRY:
            if not self._is_patch_selected(item):
                self.log(item["name"], "skipped", "excluded by --only / --skip")
                continue
            method_name = item["method"]
            method = getattr(self, method_name, None)
            if callable(method):
                method()

        print("\n📋 Execution Summary:")
        for name, status, detail in self.results:
            d_str = f" ({detail})" if detail else ""
            print(f"  • {name:<45} -> {status.upper()}{d_str}")


def find_default_hermes_dir() -> Path:
    candidates: List[Path] = []
    
    # 1. HERMES_SOURCE_DIR env
    env_dir = os.environ.get("HERMES_SOURCE_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir))

    # 2. Dynamic probe via `which hermes` CLI path
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        try:
            real_bin = Path(hermes_bin).resolve()
            for parent in [real_bin.parent, real_bin.parent.parent, real_bin.parent.parent.parent]:
                if (parent / "hermes_state.py").is_file():
                    candidates.append(parent)
        except Exception:
            pass

    # 3. Standard system locations
    candidates.extend([
        Path("/usr/local/lib/hermes-agent"),
        Path("/opt/hermes-agent"),
        Path.home() / ".local/lib/hermes-agent",
        Path("/usr/lib/hermes-agent"),
        Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    ])

    for c in candidates:
        if c and c.is_dir() and (c / "hermes_state.py").is_file():
            return c
    return Path("/usr/local/lib/hermes-agent")


def main():
    parser = argparse.ArgumentParser(
        description="Apply non-intrusive runtime enhancement patches to Hermes Agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply all patches to default Hermes Agent installation
  python3 hermes_patches.py

  # Preview changes without modifying files (Dry Run)
  python3 hermes_patches.py --dry-run -v

  # Apply only quiet streaming and clean thinking patches
  python3 hermes_patches.py --only nostream clean-think

  # Apply all patches EXCEPT Telegram command menu translation
  python3 hermes_patches.py --skip menu
        """,
    )
    parser.add_argument("--target", type=str, default="", help="Target Hermes Agent install directory")
    parser.add_argument("--dry-run", action="store_true", help="Inspect changes without writing to disk")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="PATCH",
        help="Apply only specified patches (e.g. footer, table, menu, db, tirith, nostream, clean-think, smart-split)",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        metavar="PATCH",
        help="Skip specified patches (e.g. menu, tirith)",
    )
    parser.add_argument("--list-patches", action="store_true", help="List all available patch modules and exit")

    args = parser.parse_args()

    if args.list_patches:
        print("🛠️ Available hermes-patches Modules:\n")
        for p in PATCH_REGISTRY:
            aliases = ", ".join(p["aliases"])
            print(f"  • ID: {p['id']:<12} (Aliases: {aliases})")
            print(f"    Name: {p['name']}")
            print(f"    Desc: {p['description']}\n")
        sys.exit(0)

    target = Path(args.target) if args.target else find_default_hermes_dir()
    if not (target / "hermes_state.py").is_file():
        print(f"❌ Error: Target directory '{target}' does not appear to be a valid Hermes Agent installation.", file=sys.stderr)
        print("Please provide --target /path/to/hermes-agent or set HERMES_SOURCE_DIR.", file=sys.stderr)
        sys.exit(1)

    engine = PatchEngine(
        target_dir=target,
        dry_run=args.dry_run,
        verbose=args.verbose,
        only=args.only,
        skip=args.skip,
    )
    engine.run_all()


if __name__ == "__main__":
    main()
