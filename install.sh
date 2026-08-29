#!/usr/bin/env bash
# hermes-patches installer
# Hermes Agent 体验增强补丁管理、零配置初始化与自动化守护脚本
# Repository: https://github.com/shali10/hermes-patches

set -eo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Detect Python
PYTHON_BIN="$(which python3 || which python || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}错误: 未在系统 PATH 中找到 python3 环境。${NC}"
    exit 1
fi

# Multi-stage adaptive detection for active Hermes install directory
detect_hermes_dir() {
    # 1. Environment variables
    for ev in "$HERMES_PATCH_SOURCE_ROOT" "$HERMES_SOURCE_DIR" "$HERMES_DIR" "$HERMES_HOME"; do
        if [ -n "$ev" ] && [ -d "$ev" ] && [ -f "$ev/hermes_state.py" ]; then
            echo "$ev"
            return 0
        fi
    done

    # 2. Check running processes
    local running_py
    running_py=$(ps -eo command 2>/dev/null | grep -E "(hermes_cli|gateway\.run|run_agent\.py)" | grep -v grep | awk '{print $1}' | head -n 1 || true)
    if [ -n "$running_py" ] && [ -x "$running_py" ]; then
        local p_cand
        p_cand=$("$running_py" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
        if [ -n "$p_cand" ] && [ -d "$p_cand" ] && [ -f "$p_cand/hermes_state.py" ]; then
            echo "$p_cand"
            return 0
        fi
    fi

    # 3. Check systemd service ExecStart
    if command -v systemctl >/dev/null 2>&1; then
        local sys_exec
        sys_exec=$(systemctl show hermes-gateway --property=ExecStart 2>/dev/null | grep -o 'path=[^ ;]*' | cut -d= -f2 || true)
        if [ -n "$sys_exec" ] && [ -x "$sys_exec" ]; then
            local s_cand
            s_cand=$("$sys_exec" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
            if [ -n "$s_cand" ] && [ -d "$s_cand" ] && [ -f "$s_cand/hermes_state.py" ]; then
                echo "$s_cand"
                return 0
            fi
        fi
    fi

    # 4. Probe via `which hermes` shebang & binary path
    if command -v hermes >/dev/null 2>&1; then
        local h_bin
        h_bin=$(readlink -f "$(command -v hermes)" 2>/dev/null || true)
        if [ -n "$h_bin" ] && [ -f "$h_bin" ]; then
            local shebang_py
            shebang_py=$(head -n 1 "$h_bin" 2>/dev/null | sed -n 's/^#!//p' | awk '{print $1}' || true)
            if [ -n "$shebang_py" ] && [ -x "$shebang_py" ]; then
                local b_cand
                b_cand=$("$shebang_py" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
                if [ -n "$b_cand" ] && [ -d "$b_cand" ] && [ -f "$b_cand/hermes_state.py" ]; then
                    echo "$b_cand"
                    return 0
                fi
            fi

            for depth in 1 2 3 4; do
                local h_cand
                h_cand="$(cd "$(dirname "$h_bin")/$(printf '../%.0s' $(seq 1 $depth))" 2>/dev/null && pwd)"
                if [ -d "$h_cand" ] && [ -f "$h_cand/hermes_state.py" ]; then
                    echo "$h_cand"
                    return 0
                fi
            done
        fi
    fi

    # 5. Probing common virtualenvs
    local py_venvs=(
        "/usr/local/lib/hermes-agent/venv/bin/python"
        "/opt/hermes-agent/venv/bin/python"
        "$HOME/.local/share/uv/tools/hermes-agent/bin/python"
        "$HOME/.local/pipx/venvs/hermes-agent/bin/python"
        "$HOME/.hermes/venv/bin/python"
        "$PYTHON_BIN"
    )
    for vpy in "${py_venvs[@]}"; do
        if [ -x "$vpy" ]; then
            local v_cand
            v_cand=$("$vpy" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
            if [ -n "$v_cand" ] && [ -d "$v_cand" ] && [ -f "$v_cand/hermes_state.py" ]; then
                echo "$v_cand"
                return 0
            fi
        fi
    done

    # 6. Standard system locations
    local candidates=(
        "/usr/local/lib/hermes-agent"
        "/opt/hermes-agent"
        "$HOME/.local/lib/hermes-agent"
        "$HOME/.local/share/hermes-agent"
        "$HOME/.hermes/hermes-agent"
        "/usr/lib/hermes-agent"
        "$HOME/hermes-agent"
    )
    for c in "${candidates[@]}"; do
        if [ -d "$c" ] && [ -f "$c/hermes_state.py" ]; then
            echo "$c"
            return 0
        fi
    done

    echo ""
}

HERMES_DIR="$(detect_hermes_dir)"

if [ -z "$HERMES_DIR" ]; then
    echo -e "${RED}错误: 未能自动检测到 Hermes Agent 安装目录。${NC}"
    echo -e "请通过环境变量手动指定: ${BOLD}HERMES_SOURCE_DIR=/path/to/hermes-agent bash install.sh${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
PATCH_SCRIPT="${SCRIPT_DIR}/hermes_patches.py"

# If running directly from curl pipe or standalone script missing, download to temp
if [ ! -f "$PATCH_SCRIPT" ]; then
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
    curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/hermes_patches.py -o "$TEMP_DIR/hermes_patches.py"
    PATCH_SCRIPT="$TEMP_DIR/hermes_patches.py"
fi

# Function to perform clean uninstallation
do_uninstall() {
    echo -e "\n${YELLOW}正在恢复原始备份文件 (*.bak)...${NC}"
    find "$HERMES_DIR" -name "*.bak" | while read -r bak; do
        orig="${bak%.bak}"
        mv -f "$bak" "$orig"
        echo -e "  • 还原文件: ${CYAN}$orig${NC}"
    done
    
    # Purge __pycache__
    find "$HERMES_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    if [ -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf ]; then
        rm -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
        if command -v systemctl >/dev/null 2>&1; then
            systemctl daemon-reload || true
        fi
        echo -e "  • 清理 systemd 守护配置"
    fi

    if [ -f "$HOME/.hermes/scripts/hermes-local-patches.py" ]; then
        rm -f "$HOME/.hermes/scripts/hermes-local-patches.py"
        echo -e "  • 清理 $HOME/.hermes/scripts/hermes-local-patches.py"
    fi

    if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet hermes-gateway 2>/dev/null; then
        echo -e "  • 正在重启服务以完成还原..."
        systemctl restart hermes-gateway || true
    fi

    echo -e "\n${GREEN}✓ 卸载与无损回滚完成。${NC}"
    exit 0
}

# Check for --uninstall / -u in CLI args
for arg in "$@"; do
    if [ "$arg" == "--uninstall" ] || [ "$arg" == "-u" ]; then
        do_uninstall
    fi
done

# Function to setup systemd auto-healing hook
setup_systemd_hook() {
    if command -v systemctl >/dev/null 2>&1 && (systemctl list-unit-files 2>/dev/null | grep -q "hermes-gateway.service" || systemctl status hermes-gateway >/dev/null 2>&1); then
        mkdir -p "$HOME/.hermes/scripts"
        cp -f "$PATCH_SCRIPT" "$HOME/.hermes/scripts/hermes-local-patches.py"
        chmod +x "$HOME/.hermes/scripts/hermes-local-patches.py"

        if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
            mkdir -p /etc/systemd/system/hermes-gateway.service.d
            cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
Environment="HERMES_SOURCE_DIR=${HERMES_DIR}"
ExecStartPre=-/usr/bin/env python3 $HOME/.hermes/scripts/hermes-local-patches.py --target ${HERMES_DIR}
EOF
            systemctl reset-failed hermes-gateway 2>/dev/null || true
            systemctl daemon-reload 2>/dev/null || true
            echo -e "${GREEN}✓ 升级自愈守护已就绪 (/etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf)${NC}"
        fi
    fi
}

# Pre-sync the patch script and harden systemd hook before running patches/restart
setup_systemd_hook

# If CLI arguments are provided, bypass interactive menu and execute directly
if [ "$#" -gt 0 ]; then
    echo -e "${BOLD}${BLUE}=== Hermes Agent 体验增强补丁 (hermes-patches) ===${NC}"
    echo -e "${GREEN}✓ 目标 Hermes 目录: ${BOLD}${HERMES_DIR}${NC}\n"
    "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart "$@"

    for arg in "$@"; do
        if [ "$arg" == "--list-patches" ] || [ "$arg" == "--dry-run" ]; then
            exit 0
        fi
    done

    echo -e "\n${BOLD}${GREEN}🎉 补丁操作执行完毕，已全量生效！${NC}\n"
    exit 0
fi

# =====================================================
# Interactive Numbered Menu (交互式中文数字菜单)
# =====================================================
show_menu() {
    clear 2>/dev/null || true
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    echo -e "${BOLD}${BLUE}   🛠️  Hermes Agent 体验增强补丁管理套件 (v1.3.4)   ${NC}"
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    echo -e " 目标路径: ${GREEN}${HERMES_DIR}${NC}\n"
    echo -e " ${BOLD}${GREEN}[1] 🚀 全量一键安装、自动配置并平滑重启 (推荐 / 直接回车)${NC}"
    echo -e " ---------------------------------------------------"
    echo -e " [2] 📊 Runtime Footer (Token 全量计量、缓存与耗时)"
    echo -e " [3] 📑 Telegram CJK 原生 Markdown 表格放行"
    echo -e " [4] 🇨🇳 Telegram 快捷菜单与 /help /commands 全中文汉化"
    echo -e " [5] 🛡️ SQLite 生产级外键自愈与高并发防锁死"
    echo -e " [6] ⚡ Tirith 低风险扫描审批免打扰"
    echo -e " [7] 🚫 流式输出静默控制与 429 频控防护"
    echo -e " [8] 🧠 全链路深度思考过程强力净化"
    echo -e " [9] ✂️ Telegram 4096 长消息智能段落切分"
    echo -e " ---------------------------------------------------"
    echo -e " [10] 🔍 预览变更 (Dry Run，不写入磁盘)"
    echo -e " [11] ↩️ 卸载补丁并无损还原 (.bak 原生回滚)"
    echo -e " [0]  🚪 退出脚本"
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
}

show_menu

# Read user input safely from TTY
CHOICE=""
if [ -t 0 ]; then
    read -r -p "请输入选项数字编号 [默认: 1]: " CHOICE || CHOICE="1"
elif (exec < /dev/tty) 2>/dev/null; then
    read -r -p "请输入选项数字编号 [默认: 1]: " CHOICE < /dev/tty || CHOICE="1"
else
    CHOICE="1"
    echo -e "非交互式终端环境，默认执行: [1] 全量一键安装、自动配置并平滑重启"
fi

CHOICE="${CHOICE:-1}"
echo ""

# Number to Patch ID mapping
map_num_to_patch() {
    case "$1" in
        2) echo "footer" ;;
        3) echo "table" ;;
        4) echo "menu" ;;
        5) echo "db" ;;
        6) echo "tirith" ;;
        7) echo "nostream" ;;
        8) echo "clean-think" ;;
        9) echo "smart-split" ;;
        *) echo "" ;;
    esac
}

case "$CHOICE" in
    1)
        echo -e "${BLUE}正在全量应用所有增强补丁、自动配置并平滑重启...${NC}\n"
        "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart --verbose
        ;;
    10)
        echo -e "${YELLOW}正在执行 Dry-Run 预检分析...${NC}\n"
        "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --dry-run --verbose
        exit 0
        ;;
    11)
        do_uninstall
        ;;
    0)
        echo -e "${YELLOW}已退出操作。${NC}"
        exit 0
        ;;
    *)
        # Support single or multiple space/comma-separated numbers (e.g. "2 3 7" or "2,3,7")
        SELECTED_PATCHES=()
        CLEANED_INPUT=$(echo "$CHOICE" | tr ',' ' ')
        for item in $CLEANED_INPUT; do
            p_id=$(map_num_to_patch "$item")
            if [ -n "$p_id" ]; then
                SELECTED_PATCHES+=("$p_id")
            fi
        done

        if [ "${#SELECTED_PATCHES[@]}" -gt 0 ]; then
            echo -e "${BLUE}正在应用选定补丁: ${BOLD}${SELECTED_PATCHES[*]}${NC}\n"
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --only "${SELECTED_PATCHES[@]}" --auto-config --restart --verbose
        else
            echo -e "${RED}输入无效，默认全量应用所有补丁...${NC}\n"
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart --verbose
        fi
        ;;
esac

echo -e "\n${BOLD}${GREEN}🎉 补丁操作已全部完成并实时生效！${NC}\n"
