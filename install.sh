#!/bin/bash

# 港美股量化交易通知系统 - 自动安装脚本
# Author: Quantitative Trading Team
# Description: 自动检测环境并安装所有必要的依赖

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    echo "======================================"
    echo "  港美股量化交易通知系统"
    echo "  自动安装脚本 v1.0"
    echo "======================================"
    echo ""
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        log_info "检测到操作系统: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "检测到操作系统: macOS"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        log_info "检测到操作系统: Windows"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    
    # 尝试不同的Python命令
    for cmd in python3 python; do
        if command -v $cmd &> /dev/null; then
            PYTHON_CMD=$cmd
            PYTHON_VERSION=$($cmd --version 2>&1 | cut -d' ' -f2)
            log_info "找到Python: $cmd (版本 $PYTHON_VERSION)"
            break
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        log_error "未找到Python！请先安装Python 3.8+"
        echo ""
        echo "安装方法："
        if [ "$OS" = "linux" ]; then
            echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
            echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
        elif [ "$OS" = "macos" ]; then
            echo "  方式1: brew install python3"
            echo "  方式2: 从 https://python.org 下载安装包"
        else
            echo "  从 https://python.org 下载并安装Python"
        fi
        exit 1
    fi
    
    # 检查Python版本
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        log_error "Python版本过低！需要Python 3.8+，当前版本: $PYTHON_VERSION"
        exit 1
    fi
    
    log_success "Python版本检查通过: $PYTHON_VERSION"
}

# 检查pip
check_pip() {
    log_info "检查pip..."
    
    for cmd in pip3 pip; do
        if command -v $cmd &> /dev/null; then
            PIP_CMD=$cmd
            PIP_VERSION=$($cmd --version 2>&1 | cut -d' ' -f2)
            log_info "找到pip: $cmd (版本 $PIP_VERSION)"
            break
        fi
    done
    
    if [ -z "$PIP_CMD" ]; then
        log_warning "未找到pip，尝试安装..."
        
        # 尝试安装pip
        if command -v curl &> /dev/null; then
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            $PYTHON_CMD get-pip.py --user
            rm get-pip.py
            PIP_CMD="pip3"
        else
            log_error "无法安装pip，请手动安装"
            exit 1
        fi
    fi
    
    log_success "pip检查通过"
}

# 创建虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    
    if [ -d "venv" ]; then
        log_warning "虚拟环境已存在，跳过创建"
    else
        $PYTHON_CMD -m venv venv
        log_success "虚拟环境创建成功"
    fi
    
    # 激活虚拟环境
    log_info "激活虚拟环境..."
    if [ "$OS" = "windows" ]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # 更新pip
    log_info "更新pip到最新版本..."
    python -m pip install --upgrade pip
    
    log_success "虚拟环境准备完成"
}

# 检查网络连接
check_network() {
    log_info "检查网络连接..."
    
    if command -v ping &> /dev/null; then
        if ping -c 1 pypi.org &> /dev/null; then
            log_success "网络连接正常"
            USE_MIRROR=false
        else
            log_warning "连接PyPI超时，将使用国内镜像"
            USE_MIRROR=true
        fi
    else
        log_warning "无法检查网络，默认使用国内镜像"
        USE_MIRROR=true
    fi
}

# 安装Python依赖
install_dependencies() {
    log_info "开始安装Python依赖包..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt文件不存在！"
        exit 1
    fi
    
    # 选择镜像源
    if [ "$USE_MIRROR" = true ]; then
        log_info "使用清华大学PyPI镜像源..."
        MIRROR_URL="-i https://pypi.tuna.tsinghua.edu.cn/simple/"
    else
        MIRROR_URL=""
    fi
    
    # 安装依赖
    log_info "安装基础依赖..."
    python -m pip install $MIRROR_URL --upgrade setuptools wheel
    
    log_info "安装项目依赖（这可能需要几分钟）..."
    python -m pip install $MIRROR_URL -r requirements.txt
    
    log_success "依赖安装完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装结果..."
    
    # 检查关键包
    critical_packages=("pandas" "numpy" "backtrader" "requests" "websocket-client" "PyYAML" "click" "psutil")
    
    for package in "${critical_packages[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            log_success "✓ $package"
        else
            log_error "✗ $package 安装失败"
            INSTALL_FAILED=true
        fi
    done
    
    if [ "$INSTALL_FAILED" = true ]; then
        log_error "部分关键包安装失败，请检查错误信息"
        exit 1
    fi
    
    log_success "所有关键包验证通过"
}

# 创建配置文件
setup_config() {
    log_info "设置配置文件..."
    
    if [ ! -f "config/config_local.yaml" ]; then
        if [ -f "config/config.yaml" ]; then
            cp config/config.yaml config/config_local.yaml
            log_success "创建本地配置文件: config/config_local.yaml"
        else
            log_warning "未找到配置模板文件"
        fi
    else
        log_info "本地配置文件已存在，跳过创建"
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    directories=("logs" "data/historical")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "创建目录: $dir"
        fi
    done
}

# 测试系统
test_system() {
    log_info "测试系统基本功能..."
    
    # 测试配置加载
    if python -c "from src.core.config_manager import config_manager; print('配置加载测试:', '成功' if config_manager.config_data else '失败')" 2>/dev/null; then
        log_success "配置管理器测试通过"
    else
        log_warning "配置管理器测试失败，可能需要配置API Key"
    fi
    
    # 测试命令行工具
    if python cli.py --help &>/dev/null; then
        log_success "命令行工具测试通过"
    else
        log_warning "命令行工具测试失败"
    fi
}

# 显示安装结果和后续步骤
show_next_steps() {
    echo ""
    echo "======================================"
    log_success "安装完成！"
    echo "======================================"
    echo ""
    echo "后续步骤："
    echo ""
    echo "1. 配置系统："
    echo "   编辑 config/config_local.yaml"
    echo "   - 设置您的 iTick API Key"
    echo "   - 配置通知方式（飞书/微信）"
    echo ""
    echo "2. 测试配置："
    echo "   python cli.py config"
    echo "   python cli.py test-notifications"
    echo ""
    echo "3. 启动系统："
    echo "   python main.py"
    echo "   或 python cli.py run"
    echo ""
    echo "4. 查看帮助："
    echo "   python cli.py --help"
    echo ""
    echo "5. 查看文档："
    echo "   docs/quick_start.md - 快速入门"
    echo "   docs/configuration.md - 配置指南"
    echo "   docs/faq.md - 常见问题"
    echo ""
    if [ "$OS" != "windows" ]; then
        echo "激活虚拟环境："
        echo "   source venv/bin/activate"
    else
        echo "激活虚拟环境："
        echo "   venv\\Scripts\\activate"
    fi
    echo ""
    log_warning "重要提醒："
    echo "- 请确保设置正确的 iTick API Key"
    echo "- 系统仅生成信号，不会自动下单"
    echo "- 投资有风险，请谨慎决策"
    echo ""
}

# 主函数
main() {
    show_welcome
    
    # 检查是否在项目根目录
    if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
        log_error "请在项目根目录下运行此脚本！"
        exit 1
    fi
    
    # 执行安装步骤
    detect_os
    check_python
    check_pip
    check_network
    create_venv
    install_dependencies
    verify_installation
    setup_config
    create_directories
    test_system
    show_next_steps
}

# 错误处理
handle_error() {
    log_error "安装过程中发生错误，请检查上面的错误信息"
    echo ""
    echo "常见解决方法："
    echo "1. 检查网络连接"
    echo "2. 更新pip: python -m pip install --upgrade pip"
    echo "3. 使用国内镜像: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt"
    echo "4. 手动安装失败的包"
    echo ""
    echo "如需帮助，请查看 docs/faq.md 或提交 Issue"
    exit 1
}

# 设置错误处理
trap handle_error ERR

# 运行主函数
main "$@"