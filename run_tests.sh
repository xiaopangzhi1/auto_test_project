#!/usr/bin/env bash
# PyCharm 运行配置脚本
# 将此脚本添加到 PyCharm 运行配置中

# 设置项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Android UI 自动化测试 - PyCharm 启动脚本"
echo "=========================================="
echo "项目目录: $PROJECT_ROOT"
echo ""

# 检查 Python 环境
echo "检查 Python 环境..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python 未安装或不在 PATH 中"
    exit 1
fi

# 检查虚拟环境
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "✅ 检测到虚拟环境: $PROJECT_ROOT/.venv"
    # 激活虚拟环境（在 PyCharm 中通常不需要）
else
    echo "⚠️  未检测到虚拟环境，使用系统 Python"
fi

# 检查依赖
echo ""
echo "检查依赖..."
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "✅ 找到 requirements.txt"
    echo "   如需安装依赖: pip install -r requirements.txt"
else
    echo "⚠️  未找到 requirements.txt"
fi

# 运行测试
echo ""
echo "运行测试..."
echo "=========================================="

cd "$PROJECT_ROOT"
python run.py "$@"