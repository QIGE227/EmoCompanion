#!/bin/bash
# ============================================================
# EmoCompanion APK 编译 — 多方案
# ============================================================
set -e
PROJECT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT"

echo "========================================"
echo "  EmoCompanion APK 编译器"
echo "========================================"
echo ""
echo "选择编译方式:"
echo "  1. Docker 一键编译 (推荐，最稳定)"
echo "  2. buildozer 本地编译"
echo "  3. 仅检查环境"
echo ""
read -p "输入选择 [1]: " CHOICE
CHOICE=${CHOICE:-1}

case $CHOICE in
  1)
    echo ""
    echo "🐳 Docker 编译模式"
    echo "----------------------------------------"
    if ! command -v docker &>/dev/null; then
      echo "❌ 需要安装 Docker: curl -fsSL https://get.docker.com | sh"
      exit 1
    fi
    echo "🔨 构建 Docker 镜像 (仅首次)..."
    docker build -t emocompanion-builder .
    echo "🔨 开始编译 APK..."
    docker run --rm \
      -v "$PROJECT":/app \
      -v emocompanion_cache:/root/.buildozer \
      emocompanion-builder
    echo ""
    echo "✅ APK 编译完成!"
    ls -lh bin/*.apk 2>/dev/null || echo "APK 在 bin/ 目录"
    ;;

  2)
    echo ""
    echo "🔧 buildozer 本地编译"
    echo "----------------------------------------"
    if ! command -v buildozer &>/dev/null; then
      echo "📦 安装 buildozer..."
      pip3 install buildozer
    fi
    # 检查 Java
    if ! command -v java &>/dev/null; then
      echo "❌ 需要安装 Java 17: sudo apt install openjdk-17-jdk"
      exit 1
    fi
    echo "🔨 开始编译 (首次需下载 SDK ~2GB，约30分钟)..."
    buildozer android debug
    echo ""
    echo "✅ 编译完成!"
    ls -lh bin/*.apk 2>/dev/null
    ;;

  3)
    echo ""
    echo "🔍 环境检查"
    echo "----------------------------------------"
    echo -n "Python3:   "; which python3 && python3 --version
    echo -n "pip3:      "; which pip3 && pip3 --version
    echo -n "Java:      "; java -version 2>&1 | head -1 || echo "❌ 未安装"
    echo -n "Docker:    "; docker --version 2>/dev/null || echo "❌ 未安装"
    echo -n "buildozer: "; buildozer version 2>/dev/null || echo "❌ 未安装"
    echo -n "磁盘空间:  "; df -h . | tail -1 | awk '{print $4}'
    echo ""
    echo "项目文件:"
    ls -lh models/*.gguf models/piper_zh_CN/*.onnx 2>/dev/null
    ;;
esac