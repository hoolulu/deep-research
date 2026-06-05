#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="deep-research"
REPO_URL="https://github.com/hoolulu/deep-research"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { printf "${CYAN}[*]${NC} %s\n" "$1"; }
ok()   { printf "${GREEN}[✓]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$1"; }

detect_skills_dir() {
    for dir in "$HOME/.opencode/skills" "$HOME/.config/opencode/skills" "$XDG_DATA_HOME/opencode/skills"; do
        eval dir="$dir"
        [ -d "$dir" ] && echo "$dir" && return 0
    done
    return 1
}

install_skill() {
    local target="$1"
    if [ -d "$target" ]; then
        if [ -d "$target/.git" ]; then
            (cd "$target" && git pull)
        else
            warn "已存在 $target，建议备份后重新克隆"
        fi
    else
        git clone "$REPO_URL" "$target"
    fi
    ok "$SKILL_NAME 已安装到 $target"
}

check_omo() {
    if grep -q "oh-my-opencode" "$HOME/.opencode/opencode.json" 2>/dev/null || \
       grep -q "oh-my-opencode" "$HOME/.config/opencode/opencode.json" 2>/dev/null; then
        ok "oh-my-opencode（OMO）已安装"
        return 0
    fi
    warn "未检测到 oh-my-opencode（OMO）。本 skill 依赖 OMO 的 oracle 子 agent"
    warn "安装 OMO：opencode plugins add oh-my-opencode"
    warn "或者把你的 OpenCode API Key 配置到 OMO 后重启"
    return 1
}

check_mcp() {
    local name="$1"
    local config="$2"
    if grep -q "\"$name\"" "$config" 2>/dev/null; then
        ok "$name MCP 已配置"
        return 0
    fi
    return 1
}

check_python() {
    if command -v python3 &>/dev/null; then
        ok "Python3 可用: $(python3 --version 2>&1)"
        PYTHON=python3
    elif command -v python &>/dev/null; then
        ok "Python 可用: $(python --version 2>&1)"
        PYTHON=python
    else
        warn "未检测到 Python。Scrapling 需要 Python 环境"
        warn "安装 Python：https://www.python.org/downloads/"
        return 1
    fi
}

check_scrapling() {
    if $PYTHON -c "import scrapling" 2>/dev/null; then
        local ver=$($PYTHON -c "import scrapling; print(getattr(scrapling, '__version__', '?'))")
        ok "Scrapling 已安装 ($ver)"
        return 0
    fi
    warn "Scrapling 未安装（网页抓取需要）"
    warn "安装：pip install scrapling"
    return 1
}

main() {
    log "检测 OpenCode 环境..."
    local skills_dir
    skills_dir=$(detect_skills_dir) || true

    if [ -z "$skills_dir" ]; then
        if command -v opencode &>/dev/null; then
            skills_dir="$HOME/.opencode/skills"
            mkdir -p "$skills_dir"
            ok "创建 skill 目录 $skills_dir"
        else
            warn "未安装 OpenCode。先安装：curl -fsSL https://opencode.ai/install | bash"
            exit 1
        fi
    fi
    ok "OpenCode 技能目录: $skills_dir"

    install_skill "$skills_dir/$SKILL_NAME"

    check_omo

    log "检查 Python 环境..."
    check_python || true
    check_scrapling || true

    local oc_config=""
    for cfg in "$HOME/.opencode/opencode.json" "$HOME/.opencode/opencode.jsonc" \
               "$HOME/.config/opencode/opencode.json" "$HOME/.config/opencode/opencode.jsonc"; do
        eval cfg="$cfg"
        [ -f "$cfg" ] && oc_config="$cfg" && break
    done

    if [ -n "$oc_config" ]; then
        log "检查 MCP 配置..."
        check_mcp "exa" "$oc_config" || warn "Exa MCP 未配置（搜索需要）"
        check_mcp "scrapling" "$oc_config" || warn "Scrapling MCP 未配置（抓取需要）"
    fi

    log "注册 /research 命令..."
    local cmd_src="$skills_dir/$SKILL_NAME/command/research.md"
    local cmd_dirs=("$HOME/.config/opencode/command" "$HOME/.opencode/command")
    if [ -n "${XDG_DATA_HOME:-}" ]; then
        cmd_dirs+=("$XDG_DATA_HOME/opencode/command")
    fi
    local installed_cmd=false
    for cmd_dir in "${cmd_dirs[@]}"; do
        eval cmd_dir="$cmd_dir"
        if [ -d "$(dirname "$cmd_dir")" ] || [ -d "$cmd_dir" ]; then
            mkdir -p "$cmd_dir"
            cp "$cmd_src" "$cmd_dir/research.md"
            ok "/research 命令已注册到 $cmd_dir/research.md"
            installed_cmd=true
            break
        fi
    done
    if [ "$installed_cmd" = false ]; then
        warn "未找到 OpenCode 配置目录，手动复制 command/research.md 到 .opencode/command/ 下"
    fi

    echo ""
    echo "────────────────────────────────────────"
    printf "${GREEN}安装完成！${NC}\n"
    echo "重启 OpenCode 后输入：/research 你的主题"
}

main
