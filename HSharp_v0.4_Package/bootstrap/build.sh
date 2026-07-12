#!/bin/bash
# H# Self-Hosting Bootstrap - Build Script
# Builds: C bytecode VM (Python-free H# runtime)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================================="
echo "  H# Self-Hosting Build"
echo "======================================================="

# Step 1: Generate bytecode using Python bootloader
echo ""
echo "[1/3] Generating bootstrap bytecode (Python bootloader)..."
cd "$ROOT_DIR"
python3 bootstrap/run_bootstrap.py

# Step 2: Build C VM
echo ""
echo "[2/3] Building C bytecode VM..."
cd "$SCRIPT_DIR"
gcc -O2 -Wall -o hsharp-vm hsharp_vm.c 2>&1
echo "  Binary: bootstrap/hsharp-vm"

# Step 3: Run C VM with bootstrap bytecode
echo ""
echo "[3/3] Testing H# C VM (Python-free)..."
echo ""
./hsharp-vm bootstrap_bytecode.json

echo ""
echo "======================================================="
echo "  BUILD COMPLETE"
echo "  H# now runs without Python!"
echo "  Run: ./bootstrap/hsharp-vm bootstrap/bootstrap_bytecode.json"
echo "======================================================="