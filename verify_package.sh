#!/bin/bash
# Package verification script

echo "🔍 Verifying livekit-plugins-faseeh package..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

errors=0
warnings=0

# Check 1: Required files exist
echo "📁 Checking required files..."
files=("pyproject.toml" "README.md" "LICENSE" ".gitignore" "livekit/plugins/faseeh/__init__.py" "livekit/plugins/faseeh/tts.py")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file - MISSING"
        ((errors++))
    fi
done
echo ""

# Check 2: Python syntax
echo "🐍 Checking Python syntax..."
if command -v python3 &> /dev/null; then
    for pyfile in livekit/plugins/faseeh/*.py; do
        if python3 -m py_compile "$pyfile" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $pyfile"
        else
            echo -e "${RED}✗${NC} $pyfile - SYNTAX ERROR"
            ((errors++))
        fi
    done
else
    echo -e "${YELLOW}⚠${NC} Python3 not found, skipping syntax check"
    ((warnings++))
fi
echo ""

# Check 3: Build tools available
echo "🔧 Checking build tools..."
if command -v python3 &> /dev/null; then
    if python3 -c "import build" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} build module installed"
    else
        echo -e "${YELLOW}⚠${NC} build module not installed (run: pip install build)"
        ((warnings++))
    fi

    if python3 -c "import twine" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} twine module installed"
    else
        echo -e "${YELLOW}⚠${NC} twine module not installed (run: pip install twine)"
        ((warnings++))
    fi
else
    echo -e "${RED}✗${NC} Python3 not found"
    ((errors++))
fi
echo ""

# Check 4: Package metadata
echo "📝 Checking package metadata..."
if grep -q "khalid@actualize.ae" pyproject.toml; then
    echo -e "${GREEN}✓${NC} Author email set"
else
    echo -e "${YELLOW}⚠${NC} Author email not found in pyproject.toml"
    ((warnings++))
fi

if grep -q "actualize-ae" pyproject.toml; then
    echo -e "${GREEN}✓${NC} GitHub URLs updated"
else
    echo -e "${YELLOW}⚠${NC} GitHub URLs contain 'yourusername' placeholder"
    ((warnings++))
fi
echo ""

# Check 5: Try building (if tools available)
echo "🏗️  Attempting to build package..."
if command -v python3 &> /dev/null && python3 -c "import build" 2>/dev/null; then
    # Clean old builds
    rm -rf dist/ build/ *.egg-info

    if python3 -m build &> /tmp/build_output.txt; then
        echo -e "${GREEN}✓${NC} Package built successfully"
        if [ -d "dist" ]; then
            echo "   Generated files:"
            ls -lh dist/
        fi
    else
        echo -e "${RED}✗${NC} Build failed. Check /tmp/build_output.txt for details"
        ((errors++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping build (install tools: pip install build)"
    ((warnings++))
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Package is ready to publish.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. python -m twine upload --repository testpypi dist/*  # Test first"
    echo "  2. python -m twine upload dist/*                        # Then publish"
elif [ $errors -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Package is mostly ready but has $warnings warning(s).${NC}"
    echo "   You can still publish, but consider fixing warnings first."
else
    echo -e "${RED}❌ Found $errors error(s) and $warnings warning(s).${NC}"
    echo "   Please fix errors before publishing."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
