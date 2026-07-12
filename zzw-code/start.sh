#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ZZW Code - H# AI IDE                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "⚠️  错误: 未找到 Node.js，请先安装 Node.js"
    echo "   下载地址: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "⚠️  错误: 未找到 npm，请先安装 Node.js/npm"
    exit 1
fi

echo " Node.js 版本: $(node --version)"
echo " npm 版本: $(npm --version)"
echo ""

# 安装依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

if [ ! -d "server/node_modules" ]; then
    echo "📦 安装后端依赖..."
    cd server
    npm install
    cd ..
fi

echo ""
echo "🚀 启动后端服务器 (端口 3001)..."
cd server
node index.js &
SERVER_PID=$!
cd ..

sleep 1

echo ""
echo "🚀 启动前端开发服务器 (端口 5173)..."
npm run dev

# 前端退出后也关闭后端
kill $SERVER_PID 2>/dev/null
