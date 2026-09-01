#!/usr/bin/env python3
"""
hermes-patches — Non-intrusive Enhancement Patches for Hermes Agent
Repository: https://github.com/shali10/hermes-patches

Provides full token metering, CJK native rich table support, Telegram menu & /help /commands full localization,
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
        "aliases": ["telegram-menu", "menu-zh", "help-zh", "i18n", "localization"],
        "name": "🇨🇳 Telegram 快捷菜单与 /help /commands 全中文汉化",
        "method": "patch_telegram_menu_zh",
        "description": "全量汉化 Telegram Bot 指令菜单以及 /help、/commands 全部 99 个斜杠命令说明与用法提示。",
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
    {
        "id": "terminal-cwd",
        "aliases": ["cwd", "terminal", "deleted-workdir", "cwd-recovery"],
        "name": "📁 Terminal 失效工作目录自动回退",
        "method": "patch_terminal_cwd_recovery",
        "description": "显式 workdir 被删除后，在构建命令 wrapper 前回退到可用父目录，避免 exit 126。",
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

        # Backup original outside the source tree so upgrades and git status stay clean.
        try:
            backup_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
            backup_root = backup_home / ".backup" / "local-patches"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_name = rel_path.replace("/", "__") + f".bak.{int(time.time())}"
            bak_file = backup_root / backup_name
            shutil.copy2(target_file, bak_file)
            siblings = sorted(backup_root.glob(rel_path.replace("/", "__") + ".bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_backup in siblings[3:]:
                old_backup.unlink(missing_ok=True)
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
            new_loop = '''for field in fields:
        _p_in = prompt_tokens or 0
        _c_in = cache_read_tokens or 0
        _total_prompt = _p_in if _p_in >= _c_in else _p_in + _c_in
        if field == "model":
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
            if _total_prompt:
                parts.append(f"🧠 Prompt总量: {_fmt_int(_total_prompt)}")
        elif field == "output_tokens":
            if output_tokens:
                parts.append(f"📤 输出: {_fmt_int(output_tokens)}")
        elif field == "cache_read":
            if _total_prompt and cache_read_tokens is not None and cache_read_tokens >= 0:
                pct = max(0, min(100, round((cache_read_tokens / _total_prompt) * 100)))
                parts.append(f"💾 缓存命中: {_fmt_int(cache_read_tokens)} ({pct}%)")'''

            loop_pat = r'for field in fields:.*?(?=\s*# Unknown field names are silently ignored\.)'
            if re.search(loop_pat, cand, flags=re.DOTALL):
                cand = re.sub(loop_pat, new_loop, cand, count=1, flags=re.DOTALL)

            # 5. build_footer_line signature & invocation
            old_bf_sig = "def build_footer_line(\n    *,\n    user_config: dict[str, Any] | None,\n    platform_key: str | None,\n    model: Optional[str],\n    context_tokens: int,\n    context_length: Optional[int],\n    cwd: Optional[str] = None,\n    turn_seconds: Optional[float] = None,\n) -> str:"
            new_bf_sig = "def build_footer_line(\n    *,\n    user_config: dict[str, Any] | None,\n    platform_key: str | None,\n    model: Optional[str],\n    context_tokens: int,\n    context_length: Optional[int],\n    cwd: Optional[str] = None,\n    turn_seconds: Optional[float] = None,\n    prompt_tokens: Optional[int] = None,\n    output_tokens: Optional[int] = None,\n    cache_read_tokens: Optional[int] = None,\n    **kwargs: Any,\n) -> str:"
            if old_bf_sig in cand:
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

            # 1. Ensure _cache_read_toks variable is declared
            if '_cache_read_toks = 0' not in cand and '_output_toks = 0' in cand:
                cand = cand.replace('_output_toks = 0', '_output_toks = 0\n        _cache_read_toks = 0', 1)

            # 2. Extract _cache_read_toks from agent in extraction blocks
            target_extract = '_output_toks = getattr(_agent, "session_completion_tokens", 0)'
            replacement_extract = '''_output_toks = getattr(_agent, "session_completion_tokens", 0)
            _cache_read_toks = getattr(_agent, "session_cache_read_tokens", 0) or 0'''
            if target_extract in cand and '_cache_read_toks = getattr(_agent' not in cand:
                cand = cand.replace(target_extract, replacement_extract)

            # 3. Inject "cache_read_tokens": _cache_read_toks into return dicts
            target_ret1 = '''                "input_tokens": _input_toks,
                "output_tokens": _output_toks,'''
            replacement_ret1 = '''                "input_tokens": _input_toks,
                "output_tokens": _output_toks,
                "cache_read_tokens": _cache_read_toks,'''
            if target_ret1 in cand and '"cache_read_tokens": _cache_read_toks' not in cand:
                cand = cand.replace(target_ret1, replacement_ret1)

            target_ret2 = '''            "last_prompt_tokens": _last_prompt_toks,
            "input_tokens": _input_toks,
            "output_tokens": _output_toks,
            "model": _resolved_model,'''
            replacement_ret2 = '''            "last_prompt_tokens": _last_prompt_toks,
            "input_tokens": _input_toks,
            "output_tokens": _output_toks,
            "cache_read_tokens": _cache_read_toks,
            "model": _resolved_model,'''
            if target_ret2 in cand:
                cand = cand.replace(target_ret2, replacement_ret2, 1)

            # 4. Parameter injection into build_footer_line
            new_bfl = '''_footer_line = _bfl(
                    user_config=_load_gateway_config(),
                    platform_key=_platform_config_key(source.platform),
                    model=agent_result.get("model"),
                    context_tokens=agent_result.get("last_prompt_tokens", 0) or 0,
                    context_length=agent_result.get("context_length") or None,
                    cwd=os.environ.get("TERMINAL_CWD", ""),
                    turn_seconds=_turn_seconds,
                    prompt_tokens=agent_result.get("prompt_tokens") or agent_result.get("input_tokens") or 0,
                    output_tokens=agent_result.get("output_tokens") or 0,
                    cache_read_tokens=agent_result.get("cache_read_tokens") or 0,
                )'''

            bfl_block_pat = r'_footer_line\s*=\s*_bfl\(.*?\n\s*\)(?=\s*except Exception as _footer_err:)'
            if re.search(bfl_block_pat, cand, flags=re.DOTALL):
                cand = re.sub(bfl_block_pat, new_bfl, cand, count=1, flags=re.DOTALL)

            # 5. platform key compatibility
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

        def transform_usage_pricing(src: str) -> str:
            cand = src
            if "cached_content_token_count" in cand:
                return cand
            
            old_kw = """        if not cache_read_tokens:
            # Kimi/Moonshot's native API (api.moonshot.cn / .ai) reports
            # context-cache hits as a top-level usage.cached_tokens, not the
            # OpenAI nested prompt_tokens_details.cached_tokens shape. Without
            # this, direct Kimi sessions always showed 0 cache-hit tokens and
            # the hits were billed at the full input rate (#65722).
            cache_read_tokens = _usage_count(
                _usage_get(response_usage, "cached_tokens", 0)
            )"""
            
            new_kw = """        if not cache_read_tokens:
            # Kimi/Moonshot's native API (api.moonshot.cn / .ai) reports
            # context-cache hits as a top-level usage.cached_tokens, not the
            # OpenAI nested prompt_tokens_details.cached_tokens shape. Without
            # this, direct Kimi sessions always showed 0 cache-hit tokens and
            # the hits were billed at the full input rate (#65722).
            cache_read_tokens = _usage_count(
                _usage_get(response_usage, "cached_tokens", 0)
            )
        if not cache_read_tokens:
            cache_read_tokens = _usage_count(
                _usage_get(response_usage, "cached_content_token_count", 0)
            )
        if not cache_read_tokens:
            cache_read_tokens = _usage_count(
                _usage_get(response_usage, "cachedContentTokenCount", 0)
            )
        if not cache_read_tokens:
            cache_read_tokens = _usage_count(
                _usage_get(response_usage, "cached_prompt_tokens", 0)
            )
        if not cache_read_tokens and details:
            cache_read_tokens = _usage_count(
                _usage_get(details, "cache_read_tokens", 0)
            ) or _usage_count(
                _usage_get(details, "cached_content_token_count", 0)
            ) or _usage_count(
                _usage_get(details, "cached_prompt_tokens", 0)
            )"""
            
            if old_kw in cand:
                cand = cand.replace(old_kw, new_kw, 1)
            return cand

        def transform_conversation_loop(src: str) -> str:
            cand = src
            if "# Initialize base prompt cache tokens from previous conversation history" in cand and "from agent.usage_pricing import CanonicalUsage" in cand:
                return cand
            
            # 1. Base initialization from conversation_history in run_conversation
            base_anchor = """    agent._last_compaction_in_place = False
    agent._last_compression_attempt_recorded = False
    agent._last_compression_attempt_in_place = None"""

            base_init = """    agent._last_compaction_in_place = False
    agent._last_compression_attempt_recorded = False
    agent._last_compression_attempt_in_place = None
    # Initialize base prompt cache tokens from previous conversation history
    if conversation_history:
        try:
            from agent.model_metadata import estimate_request_tokens_rough
            _tools = getattr(agent, "tools", None) or None
            _sys = getattr(agent, "_cached_system_prompt", "") or getattr(agent, "system_prompt", "") or ""
            agent._session_base_prompt_tokens = estimate_request_tokens_rough(
                conversation_history, system_prompt=_sys, tools=_tools
            )
        except Exception:
            agent._session_base_prompt_tokens = 0
    else:
        agent._session_base_prompt_tokens = 0
    agent._last_iter_prompt_tokens = 0"""

            if base_anchor in cand and "# Initialize base prompt cache tokens from previous conversation history" not in cand:
                cand = cand.replace(base_anchor, base_init, 1)

            # 2. Immutable CanonicalUsage reconstruction on cache derivation
            old_norm = """                if hasattr(response, 'usage') and response.usage:
                    canonical_usage = normalize_usage(
                        response.usage,
                        provider=agent.provider,
                        api_mode=agent.api_mode,
                    )"""
                    
            new_norm = """                if hasattr(response, 'usage') and response.usage:
                    canonical_usage = normalize_usage(
                        response.usage,
                        provider=agent.provider,
                        api_mode=agent.api_mode,
                    )
                    # Adaptive prompt cache derivation when upstream proxy/provider omits cache stats
                    if canonical_usage.cache_read_tokens == 0:
                        _p_raw = canonical_usage.prompt_tokens or getattr(response.usage, "prompt_tokens", 0) or getattr(response.usage, "input_tokens", 0)
                        _prev_p = getattr(agent, "_last_iter_prompt_tokens", 0) or getattr(agent, "_session_base_prompt_tokens", 0) or 0
                        if _prev_p > 0 and _p_raw >= _prev_p:
                            from agent.usage_pricing import CanonicalUsage
                            _inf_cache = min(_p_raw, _prev_p)
                            canonical_usage = CanonicalUsage(
                                input_tokens=max(0, _p_raw - _inf_cache),
                                output_tokens=canonical_usage.output_tokens,
                                cache_read_tokens=_inf_cache,
                                cache_write_tokens=canonical_usage.cache_write_tokens,
                                reasoning_tokens=canonical_usage.reasoning_tokens,
                                request_count=canonical_usage.request_count,
                                raw_usage=canonical_usage.raw_usage,
                            )
                    agent._last_iter_prompt_tokens = canonical_usage.prompt_tokens
                    agent._session_base_prompt_tokens = canonical_usage.prompt_tokens"""

            # Replace either the clean original or the previous patch iteration
            if old_norm in cand:
                cand = cand.replace(old_norm, new_norm, 1)
            elif "# Adaptive prompt cache derivation when upstream proxy/provider omits cache stats" in cand:
                pat = r"if hasattr\(response, 'usage'\) and response\.usage:\s+canonical_usage = normalize_usage\(.*?agent\._session_base_prompt_tokens = canonical_usage\.prompt_tokens"
                cand = re.sub(pat, new_norm.strip(), cand, count=1, flags=re.DOTALL)
            return cand

        ok1 = self.apply_file_patch("gateway/runtime_footer.py", transform_footer, "📊 Runtime Footer 全量计量")
        ok2 = self.apply_file_patch("gateway/run.py", transform_gateway_run, "⚙️ Gateway 运行态参数注入")
        ok3 = self.apply_file_patch("agent/usage_pricing.py", transform_usage_pricing, "🧠 多模型厂商全字段缓存解析")
        ok4 = self.apply_file_patch("agent/conversation_loop.py", transform_conversation_loop, "⚡ 代理会话级智能前缀缓存补齐")
        return ok1 and ok2 and ok3 and ok4

    # -------------------------------------------------------------
    # Patch 2: Telegram CJK Native Rich Formatting & Table Bypass
    # -------------------------------------------------------------
    def patch_telegram_cjk_rich(self) -> bool:
        def transform(src: str) -> str:
            cand = src
            if "Allow Telegram CJK rich formatting" in cand:
                return cand

            old_fn = "def _has_telegram_desktop_cjk_rich_garble_shape(self, content: str) -> bool:"
            new_fn = """def _has_telegram_desktop_cjk_rich_garble_shape(self, content: str) -> bool:
        \"\"\"Allow Telegram CJK rich formatting and native pipe tables (telegram-allow-cjk-rich).\"\"\"
        return False"""

            if old_fn in cand:
                start_idx = cand.find(old_fn)
                next_fn_idx = cand.find("def _needs_rich_rendering", start_idx)
                if start_idx >= 0 and next_fn_idx > start_idx:
                    cand = cand[:start_idx] + new_fn + "\n\n    " + cand[next_fn_idx:]
            return cand

        return self.apply_file_patch("plugins/platforms/telegram/adapter.py", transform, "📑 Telegram 原生表格放行")

    # -------------------------------------------------------------
    # Patch 3: Telegram Menu & /help /commands Full Chinese Localization
    # -------------------------------------------------------------
    def patch_telegram_menu_zh(self) -> bool:
        def transform(src: str) -> str:
            cand = src
            if "alias_note_zh" in cand and "响应平台启动请求" in cand:
                return cand

            zh_dict_block = '''_TELEGRAM_ZH_DESCRIPTIONS: dict[str, str] = {
    "start": "响应平台启动请求（静默确认）",
    "new": "新建对话会话（重置会话 ID 与历史）",
    "topic": "开启或管理 Telegram 私聊话题会话",
    "clear": "清屏并开启全新会话",
    "redraw": "强制重绘终端界面（修复终端显示漂移）",
    "history": "查看当前会话的历史对话记录",
    "save": "导出当前对话记录 (JSON/MD/HTML)",
    "retry": "重新发送上一条消息给 Agent",
    "prompt": "在 $EDITOR 中编辑 Markdown 提示词并发送",
    "undo": "回退最近 N 轮对话并重新提问（默认 1）",
    "title": "为当前会话设置或重命名标题",
    "handoff": "将当前会话转交至即时通讯平台 (Telegram/Discord 等)",
    "branch": "从当前对话分叉创建新会话（探索不同路径）",
    "worktree": "查看、创建或清理隔离的 git worktree 工作区",
    "compress": "压缩对话上下文（保留最近 N 轮上下文）",
    "rollback": "查看或恢复文件系统快照检查点",
    "snapshot": "创建或恢复 Hermes 配置与状态快照",
    "export": "导出当前配置档案（配置、技能与主题包）",
    "import": "导入外部配置档案并作为新 Profile",
    "stop": "终止当前所有正在运行的后台进程与任务",
    "pause": "全局紧急暂停新任务执行（/pause off 恢复）",
    "approve": "手动批准待执行的敏感/危险命令",
    "deny": "拒绝待执行的危险命令（可附带原因）",
    "background": "在后台异步执行一条提示词任务",
    "agents": "查看当前活跃的子代理与运行中任务",
    "journey": "打开自主学习与进化时间线 (Learning Journey)",
    "queue": "将提示词加入下一轮执行队列（不打断当前运行）",
    "steer": "在下次工具调用后插入实时干预指令",
    "goal": "设置跨轮次持续自动推进的长期目标",
    "heartbeat": "设置空闲时自动唤醒执行的周期性提示词",
    "refine": "立即复盘当前对话并将经验沉淀至记忆与技能",
    "review": "指派独立子代理评审当前工作 (PR/代码/文档)",
    "loop": "在当前会话中按固定时间间隔循环执行任务",
    "moa": "通过多代理混合架构 (MoA) 预设运行一次提示词",
    "subgoal": "为当前活跃目标添加或管理子验收标准",
    "status": "查看当前会话状态、活跃模型、Token 与上下文",
    "egress": "查看 Docker 出口代理与网络转发状态",
    "context": "查看上下文窗口占用仪表盘、分类细项与吞吐量",
    "whoami": "查看当前用户的斜杠命令权限 (Admin / User)",
    "profile": "查看当前活跃的 Profile 名称与主目录路径",
    "sethome": "将当前聊天会话设置为主频道 (Home Channel)",
    "resume": "恢复之前命名的历史会话",
    "sessions": "浏览、检索并恢复历史会话列表",
    "config": "查看或检查当前系统配置",
    "model": "切换模型（仅当前会话生效；--global 全局生效）",
    "codex-runtime": "切换 OpenAI/Codex 模型的 Codex App-Server 运行时",
    "personality": "设置或切换预定义人格设定",
    "statusbar": "切换底部模型与上下文状态栏显示",
    "battery": "在状态栏切换彩色电量/资源指示器",
    "timestamps": "切换消息与历史记录的时间戳显示 [HH:MM]",
    "diff": "查看工作区中的 Git 变更与 Diff 差异",
    "verbose": "循环切换工具执行进度显示档位 (off/new/all/verbose)",
    "focus": "切换专注视图（仅展示用户提示与最终答复）",
    "footer": "切换回复末尾的运行信息与 Token 统计页脚 (on/off)",
    "yolo": "切换 YOLO 极速模式（自动跳过危险命令审批）",
    "approvals": "查看或设置持久化危险命令审批策略 (manual/smart/off)",
    "reasoning": "管理思考/推理强度级别与显示方式",
    "fast": "切换快速处理模式（OpenAI Priority / Anthropic Fast）",
    "skin": "查看或更换终端显示皮肤与主题",
    "indicator": "选择终端等待指示器样式 (ascii/emoji/kaomoji/unicode)",
    "voice": "切换语音模式（纯文本 / 语音回复 / TTS 播报）",
    "wake": "切换 'Hey Hermes' 语音唤醒词监听",
    "busy": "配置当 Agent 正在执行时按回车的行为策略",
    "tools": "管理工具集：查看、禁用或启用指定工具",
    "toolsets": "列出当前可用的工具集 (Toolsets)",
    "skills": "搜索、安装、查看或管理可用技能库 (Skills)",
    "memory": "查看待确认的记忆写入 / 切换记忆写入审批门禁",
    "bundles": "查看技能组合包列表 (通过 /<name> 批量加载)",
    "pet": "切换或领养终端 Petdex 宠物助手",
    "hatch": "根据描述孵化并生成全新的 Petdex 宠物",
    "learn": "从任意内容（目录、URL、对话、笔记）自主学习技能",
    "init": "扫描仓库代码并自动生成/更新 AGENTS.md 指南",
    "cron": "管理系统定时计划任务 (Cron Jobs)",
    "suggestions": "查看系统智能推荐的自动化任务建议",
    "blueprint": "从 Blueprint 模板快速配置自动化任务",
    "curator": "管理后台技能自动维护与提炼系统",
    "kanban": "多 Profile 协作看板（任务、关联、评论）",
    "reload": "将 .env 环境变量热重载到当前运行会话",
    "reload-mcp": "重新加载配置文件中的 MCP 服务器连接",
    "reload-skills": "重新扫描 ~/.hermes/skills/ 目录下的技能变更",
    "browser": "连接 Chromium 浏览器 CDP 或切换 Browser Use 模式",
    "plugins": "列出已安装的插件清单及其运行状态",
    "commands": "分页浏览全部可用命令与技能列表",
    "help": "查看可用命令指南（/help skills 查看技能，/help <文本> 搜索）",
    "palette": "打开模糊搜索命令面板 (Command Palette / Ctrl+P)",
    "restart": "安全平滑重启 Hermes Gateway 实例",
    "usage": "查看 Token 使用量统计与 Rate Limits 限额",
    "subscription": "查看 Nous 账户订阅计划并在浏览器中管理",
    "topup": "查看 Nous 账户余额并前往控制台充值",
    "insights": "生成使用习惯、开销与效率分析洞察报告",
    "platforms": "查看 Gateway 消息平台连接状态汇总",
    "platform": "管理异常 Gateway 平台（暂停、恢复或列出）",
    "copy": "复制上一条助手回复到系统剪贴板",
    "paste": "从系统剪贴板粘贴图片并附加到下一轮对话",
    "image": "附加本地图片文件到下一轮提示词",
    "update": "将 Hermes Agent 检查并升级到最新版本",
    "version": "查看 Hermes Agent 当前版本与环境信息",
    "debug": "上传系统与日志调试报告并生成分享链接",
    "quit": "退出 CLI 终端（--delete 同步删除会话历史）",
}'''

            # Clean any legacy _TELEGRAM_ZH_DESCRIPTIONS block if present
            if "_TELEGRAM_ZH_DESCRIPTIONS: dict[str, str] = {" in cand:
                cand = re.sub(r'_TELEGRAM_ZH_DESCRIPTIONS:\s*dict\[str,\s*str\]\s*=\s*\{.*?\n\}', '', cand, flags=re.DOTALL)

            # 1. Update _build_description with zh_dict_block
            old_bd_pat = r'def _build_description\(cmd:\s*CommandDef\)\s*->\s*str:.*?(?=\n\n# Backwards-compatible|\n# Backwards-compatible)'
            new_bd_code = zh_dict_block + '''\n\n\ndef _build_description(cmd: CommandDef) -> str:
    """Build a CLI-facing description string including usage hint."""
    desc = _TELEGRAM_ZH_DESCRIPTIONS.get(cmd.name, cmd.description)
    if cmd.args_hint:
        return f"{desc} (用法: /{cmd.name} {cmd.args_hint})"
    return desc'''
            cand, count = re.subn(old_bd_pat, new_bd_code, cand, count=1, flags=re.DOTALL)
            if count == 0 and "def _build_description(" in cand:
                # Direct replacement fallback
                bd_start = cand.find("def _build_description(")
                bd_end = cand.find("\n\n# Backwards-compatible", bd_start)
                if bd_start >= 0 and bd_end >= 0:
                    cand = cand[:bd_start] + new_bd_code + cand[bd_end:]

            # 2. Update gateway_help_lines to translate descriptions & alias note
            old_ghl = '        lines.append(f"`/{cmd.name}{args}` -- {cmd.description}{alias_note}")'
            new_ghl = '''        alias_note_zh = alias_note.replace("alias:", "别名:") if alias_note else ""
        desc = _TELEGRAM_ZH_DESCRIPTIONS.get(cmd.name, cmd.description)
        lines.append(f"`/{cmd.name}{args}` -- {desc}{alias_note_zh}")'''
            if old_ghl in cand:
                cand = cand.replace(old_ghl, new_ghl, 1)

            # 3. Localize telegram_bot_commands while preserving the current
            # registry-derived implementation. Never replace the function with
            # a stale snapshot such as _RAW_TELEGRAM_BOT_COMMANDS (removed
            # upstream), which breaks command-menu registration at runtime.
            old_tg_append = '            result.append((tg_name, cmd.description))'
            new_tg_append = '            result.append((tg_name, _TELEGRAM_ZH_DESCRIPTIONS.get(cmd.name, cmd.description)))'
            if old_tg_append in cand:
                cand = cand.replace(old_tg_append, new_tg_append, 1)

            old_command_append = '            result.append((tg_name, command.description))'
            new_command_append = '''            result.append(
                (tg_name, _TELEGRAM_ZH_DESCRIPTIONS.get(command.name, command.description))
            )'''
            if old_command_append in cand:
                cand = cand.replace(old_command_append, new_command_append, 1)

            old_plugin_append = '            result.append((tg_name, description))'
            new_plugin_append = '            result.append((tg_name, _TELEGRAM_ZH_DESCRIPTIONS.get(name, description)))'
            if old_plugin_append in cand:
                cand = cand.replace(old_plugin_append, new_plugin_append, 1)

            return cand

        return self.apply_file_patch("hermes_cli/commands.py", transform, "🇨🇳 Telegram 快捷菜单与 /help /commands 汉化")

    # -------------------------------------------------------------
    # Patch 4: State DB Foreign Key & Contention Self-Heal
    # -------------------------------------------------------------
    def patch_state_db(self) -> bool:
        def transform(src: str) -> str:
            cand = src

            # 1. State DB contention busy_timeout in apply_database_pragmas
            if "PRAGMA busy_timeout = 5000" not in cand:
                pragma_anchor = "def apply_database_pragmas("
                if pragma_anchor in cand:
                    p_start = cand.find(pragma_anchor)
                    doc_end = cand.find('\"\"\"\n    try:', p_start)
                    if doc_end > p_start:
                        bt_code = '''\"\"\"\n    try:\n        conn.execute(\"PRAGMA busy_timeout = 5000\")\n    except Exception:\n        pass\n\n    try:'''
                        cand = cand[:doc_end] + bt_code + cand[doc_end + len('\"\"\"\n    try:'):]

            # 2. FK self-heal in append_message
            msg_anchor = "def append_message("
            if msg_anchor in cand and "FK self-heal: ensure the session parent row exists" not in cand:
                m_start = cand.find(msg_anchor)
                ins_idx = cand.find('cursor = conn.execute(\n                \"\"\"INSERT INTO messages', m_start)
                if ins_idx > m_start:
                    heal_code = '''# FK self-heal: ensure the session parent row exists.
            try:
                conn.execute(
                    \"INSERT OR IGNORE INTO sessions (id, source, started_at) VALUES (?, 'unknown', ?)\",
                    (session_id, time.time()),
                )
            except Exception:
                pass\n\n            '''
                    cand = cand[:ins_idx] + heal_code + cand[ins_idx:]

            # 3. FK self-heal in append_messages_batch
            batch_anchor = "def append_messages_batch("
            if batch_anchor in cand and "FK batch self-heal" not in cand:
                b_start = cand.find(batch_anchor)
                ins_idx = cand.find('inserted, tool_calls_total = self._insert_message_rows(', b_start)
                if ins_idx > b_start:
                    heal_batch = '''# FK batch self-heal: ensure session exists
                try:
                    conn.execute(
                        \"INSERT OR IGNORE INTO sessions (id, source, started_at) VALUES (?, 'unknown', ?)\",
                        (session_id, time.time()),
                    )
                except Exception:
                    pass\n\n                '''
                    cand = cand[:ins_idx] + heal_batch + cand[ins_idx:]

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
            if "hermes-patches smart-split" in cand:
                return cand

            anchor = "region = remaining[:_cp_limit]\n            split_at = region.rfind("
            if anchor in cand:
                start_idx = cand.find(anchor)
                target_end = cand.find('split_at = region.rfind(" ")', start_idx)
                if start_idx >= 0 and target_end > start_idx:
                    end_idx = target_end + len('split_at = region.rfind(" ")')
                    new_code = 'region = remaining[:_cp_limit]\n            # Prefer paragraph break, then single newline, then space (hermes-patches smart-split)\n            split_at = region.rfind("\\n\\n")\n            if split_at < _cp_limit // 3:\n                split_at = region.rfind("\\n")\n            if split_at < _cp_limit // 2:\n                split_at = region.rfind(" ")'
                    cand = cand[:start_idx] + new_code + cand[end_idx:]
            return cand

        return self.apply_file_patch("gateway/platforms/base.py", transform_base_platform, "✂️ Telegram 4096 智能段落切分")

    # -------------------------------------------------------------
    # Patch 9: Local terminal explicit cwd recovery
    # -------------------------------------------------------------
    def patch_terminal_cwd_recovery(self) -> bool:
        def transform_base_env(src: str) -> str:
            marker = "# hermes-patches terminal-cwd-recovery"
            if marker in src:
                return src
            old = """        effective_timeout = timeout or self.timeout
        effective_cwd = cwd or self.cwd

        # Merge sudo stdin with caller stdin"""
            new = """        effective_timeout = timeout or self.timeout
        effective_cwd = cwd or self.cwd
        # hermes-patches terminal-cwd-recovery
        # Explicit per-command workdirs can be deleted after routing records
        # them. Resolve a safe local ancestor before _wrap_command emits cd;
        # LocalEnvironment's Popen-only recovery is otherwise too late.
        if self.is_local:
            try:
                from tools.environments.local import _resolve_safe_cwd
                effective_cwd = _resolve_safe_cwd(effective_cwd)
            except Exception:
                logger.debug(\"Could not resolve safe local command cwd\", exc_info=True)

        # Merge sudo stdin with caller stdin"""
            if old in src:
                return src.replace(old, new, 1)
            # Current production source may already contain the equivalent fix
            # without the persistence marker; tag it idempotently.
            existing = """        if self.is_local:
            try:
                from tools.environments.local import _resolve_safe_cwd

                effective_cwd = _resolve_safe_cwd(effective_cwd)"""
            if existing in src:
                return src.replace("        if self.is_local:\n", f"        {marker}\n        if self.is_local:\n", 1)
            return src

        return self.apply_file_patch(
            "tools/environments/base.py",
            transform_base_env,
            "📁 Terminal 失效工作目录自动回退",
        )

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
    - display.language = zh
    - display.final_response_markdown = keep
    - display.streaming = false
    - display.platforms.telegram.streaming = false (quiet delivery & flood shield)
    - display.runtime_footer.enabled = true
    - display.runtime_footer.fields = [model, prompt_tokens, cache_read, output_tokens, context_pct, elapsed_time]
    - telegram.extra.rich_messages = true
    - telegram.extra.allow_cjk_rich = true
    - telegram.extra.rich_drafts = false
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

    try:
        import yaml
        cfg = {}
        if config_file.is_file():
            try:
                cfg = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            except Exception:
                cfg = {}

        changed = False
        display = cfg.setdefault("display", {})
        if display.get("language") != "zh":
            display["language"] = "zh"
            changed = True
        if display.get("final_response_markdown") != "keep":
            display["final_response_markdown"] = "keep"
            changed = True
        if display.get("streaming") is not False:
            display["streaming"] = False
            changed = True

        platforms = display.setdefault("platforms", {})
        tg_plat = platforms.setdefault("telegram", {})
        if tg_plat.get("streaming") is not False:
            tg_plat["streaming"] = False
            changed = True

        footer = display.setdefault("runtime_footer", {})
        if not footer.get("enabled"):
            footer["enabled"] = True
            changed = True
        desired_fields = ["model", "prompt_tokens", "cache_read", "output_tokens", "context_pct", "elapsed_time"]
        if footer.get("fields") != desired_fields:
            footer["fields"] = desired_fields
            changed = True

        tg = cfg.setdefault("telegram", {})
        tg_extra = tg.setdefault("extra", {})
        if tg_extra.get("rich_messages") is not True:
            tg_extra["rich_messages"] = True
            changed = True
        if tg_extra.get("allow_cjk_rich") is not True:
            tg_extra["allow_cjk_rich"] = True
            changed = True
        if tg_extra.get("rich_drafts") is not False:
            tg_extra["rich_drafts"] = False
            changed = True

        if changed:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(yaml.dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
            print(f"🟢 [已自动配置] 成功同步语言、表格放行、防 429 静默与全量 Footer 至 {config_file}")
        else:
            print(f"⚪ [已配置] 配置文件已处于最佳运行配置 ({config_file})")
        return True
    except Exception as e:
        print(f"⚠️ [配置提示] 自动修改配置文件跳过: {e}")
        return False


def sync_local_patch_script(target_dir: Optional[Path] = None) -> bool:
    """Sync the active hermes_patches.py to ~/.hermes/scripts/hermes-local-patches.py and harden systemd hook."""
    try:
        scripts_dir = Path.home() / ".hermes" / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        local_script = scripts_dir / "hermes-local-patches.py"
        cur_script = Path(__file__).resolve()

        if cur_script.is_file() and cur_script != local_script:
            shutil.copy2(cur_script, local_script)
            local_script.chmod(0o755)

        # Harden systemd unit drop-in with non-blocking ExecStartPre=-
        conf_dir = Path("/etc/systemd/system/hermes-gateway.service.d")
        if conf_dir.is_dir() or (hasattr(os, "geteuid") and os.geteuid() == 0 and Path("/etc/systemd/system").is_dir()):
            conf_dir.mkdir(parents=True, exist_ok=True)
            conf_file = conf_dir / "10-local-patches.conf"
            target_path = target_dir or find_default_hermes_dir()
            conf_content = f"""[Service]
Environment="HERMES_PATCH_SOURCE_ROOT={target_path}"
Environment="HERMES_SOURCE_DIR={target_path}"
ExecStartPre=-/usr/bin/env python3 {local_script} --target {target_path}
"""
            conf_file.write_text(conf_content, encoding="utf-8")
            if shutil.which("systemctl"):
                subprocess.run(["systemctl", "daemon-reload"], check=False, capture_output=True)
        return True
    except Exception:
        return False


def restart_gateway_services(target_dir: Optional[Path] = None) -> bool:
    """
    Seamlessly restart the active Hermes gateway service via systemd if present,
    or identify running standalone processes.
    """
    # 1. Sync script and ensure non-blocking ExecStartPre before triggering restart
    sync_local_patch_script(target_dir)

    # 2. Systemd service restart
    if shutil.which("systemctl"):
        try:
            status_proc = subprocess.run(["systemctl", "status", "hermes-gateway"], capture_output=True, text=True)
            if "hermes-gateway.service" in status_proc.stdout or "Loaded:" in status_proc.stdout:
                print("🔄 正在平滑重启 hermes-gateway 系统服务...")
                subprocess.run(["systemctl", "reset-failed", "hermes-gateway"], check=False, capture_output=True)
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
                    # Fallback retry with inspecting journal
                    journal_proc = subprocess.run(["journalctl", "-u", "hermes-gateway", "-n", "10", "--no-pager"], capture_output=True, text=True)
                    if journal_proc.stdout:
                        print("\n🔍 故障现场诊断日志:")
                        for l in journal_proc.stdout.splitlines():
                            print(f"   {l}")
        except Exception as e:
            print(f"⚠️ 重启服务时发生异常: {e}")

    # 3. Check running processes
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
        restart_gateway_services(target_dir=target)


if __name__ == "__main__":
    main()
