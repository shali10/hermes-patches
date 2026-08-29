#!/usr/bin/env bash
# hermes-patches installer
# Hermes Agent 体验增强补丁管理与自动化守护脚本
# Repository: https://github.com/shali10/hermes-patches

set -eo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect Python
PYTHON_BIN="$(which python3 || which python || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}错误: 未在系统 PATH 中找到 python3 环境。${NC}"
    exit 1
fi

# Detect Hermes install directory
detect_hermes_dir() {
    if [ -n "$HERMES_SOURCE_DIR" ] && [ -d "$HERMES_SOURCE_DIR" ] && [ -f "$HERMES_SOURCE_DIR/hermes_state.py" ]; then
        echo "$HERMES_SOURCE_DIR"
        return 0
    fi

    # 1. Probe via `which hermes` CLI path resolution
    if command -v hermes >/dev/null 2>&1; then
        local h_bin
        h_bin=$(readlink -f "$(command -v hermes)" 2>/dev/null || true)
        if [ -n "$h_bin" ]; then
            for depth in 1 2 3; do
                local h_cand
                h_cand="$(cd "$(dirname "$h_bin")/$(printf '../%.0s' $(seq 1 $depth))" 2>/dev/null && pwd)"
                if [ -d "$h_cand" ] && [ -f "$h_cand/hermes_state.py" ]; then
                    echo "$h_cand"
                    return 0
                fi
            done
        fi
    fi

    # 2. Standard system locations
    local candidates=(
        "/usr/local/lib/hermes-agent"
        "/opt/hermes-agent"
        "$HOME/.local/lib/hermes-agent"
        "/usr/lib/hermes-agent"
    )
    for c in "${candidates[@]}"; do
        if [ -d "$c" ] && [ -f "$c/hermes_state.py" ]; then
            echo "$c"
            return 0
        fi
    done

    # 3. Pip site-packages probing
    local site_pkg
    site_pkg=$("$PYTHON_BIN" -c "import sys, site; print(site.getsitepackages()[0] if site.getsitepackages() else '')" 2>/dev/null || true)
    if [ -n "$site_pkg" ] && [ -f "$site_pkg/hermes_state.py" ]; then
        echo "$site_pkg"
        return 0
    fi

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

    echo -e "\n${GREEN}✓ 卸载与无损回滚完成。${NC}"
    exit 0
}

# Check for --uninstall / -u in CLI args
for arg in "$@"; do
    if [ "$arg" == "--uninstall" ] || [ "$arg" == "-u" ]; then
        do_uninstall
    fi
done

# If CLI arguments are provided, bypass interactive menu and execute directly
if [ "$#" -gt 0 ]; then
    echo -e "${BOLD}${BLUE}=== Hermes Agent 体验增强补丁 (hermes-patches) ===${NC}"
    echo -e "${GREEN}✓ 目标 Hermes 目录: ${BOLD}${HERMES_DIR}${NC}\n"
    "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" "$@"

    for arg in "$@"; do
        if [ "$arg" == "--list-patches" ] || [ "$arg" == "--dry-run" ]; then
            exit 0
        fi
    done

    # Setup systemd auto-healing hook
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "hermes-gateway.service"; then
        mkdir -p "$HOME/.hermes/scripts"
        cp -f "$PATCH_SCRIPT" "$HOME/.hermes/scripts/hermes-local-patches.py"
        chmod +x "$HOME/.hermes/scripts/hermes-local-patches.py"

        if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
            mkdir -p /etc/systemd/system/hermes-gateway.service.d
            cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
ExecStartPre=$HOME/.hermes/scripts/hermes-local-patches.py
EOF
            systemctl daemon-reload || true
            echo -e "\n${GREEN}✓ 升级自愈守护已就绪 (systemd ExecStartPre)。${NC}"
        fi
    fi

    echo -e "\n${BOLD}${GREEN}🎉 补丁操作执行完毕！${NC}"
    echo -e "可通过 Telegram 输入 ${BOLD}/restart${NC} 或执行 systemctl 重启生效。\n"
    exit 0
fi

# =====================================================
# Interactive Numbered Menu (交互式中文数字菜单)
# =====================================================
show_menu() {
    clear 2>/dev/null || true
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    echo -e "${BOLD}${BLUE}   🛠️  Hermes Agent 体验增强补丁管理套件 (v1.2.0)   ${NC}"
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    echo -e " 目标路径: ${GREEN}${HERMES_DIR}${NC}\n"
    echo -e " ${BOLD}${GREEN}[1] 🚀 全量一键安装所有增强补丁 (推荐 / 直接回车)${NC}"
    echo -e " ---------------------------------------------------"
    echo -e " [2] 📊 Runtime Footer (Token 全量计量、缓存与耗时)"
    echo -e " [3] 📑 Telegram CJK 原生 Markdown 表格放行"
    echo -e " [4] 🇨🇳 Telegram 快捷命令中文菜单汉化"
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
    echo -e "非交互式终端环境，默认执行: [1] 全量一键安装所有增强补丁"
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
        echo -e "${BLUE}正在全量应用所有增强补丁...${NC}\n"
        "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --verbose
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
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --only "${SELECTED_PATCHES[@]}" --verbose
        else
            echo -e "${RED}输入无效，默认全量应用所有补丁...${NC}\n"
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --verbose
        fi
        ;;
esac

# Configure systemd supervision hook if systemd is available
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "hermes-gateway.service"; then
    mkdir -p "$HOME/.hermes/scripts"
    cp -f "$PATCH_SCRIPT" "$HOME/.hermes/scripts/hermes-local-patches.py"
    chmod +x "$HOME/.hermes/scripts/hermes-local-patches.py"

    if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
        mkdir -p /etc/systemd/system/hermes-gateway.service.d
        cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
ExecStartPre=$HOME/.hermes/scripts/hermes-local-patches.py
EOF
        systemctl daemon-reload || true
        echo -e "\n${GREEN}✓ 升级自愈守护已就绪 (systemd ExecStartPre)。${NC}"
    fi
fi

echo -e "\n${BOLD}${GREEN}🎉 补丁操作已成功完成！${NC}"
echo -e "可通过 Telegram 输入 ${BOLD}/restart${NC} 重启生效。\n"
