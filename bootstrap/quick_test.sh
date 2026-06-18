#!/bin/bash
# Quick test script for H# bootstrap modules

echo "=========================================="
echo "H# Bootstrap Quick Test"
echo "=========================================="
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Run module tests
echo "Running module tests..."
python3 bootstrap/test_all_modules.py

echo ""
echo "=========================================="
echo "Testing individual modules with hsharp.py"
echo "=========================================="
echo ""

# Test formatter (known to work)
echo "1. Testing formatter.hto..."
python3 hsharp.py bootstrap/formatter.hto 2>&1 | head -20

echo ""
echo "=========================================="
echo "Quick test complete!"
echo "=========================================="
