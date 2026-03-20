#!/bin/bash
set -e

echo "Publishing TokenBudget SDK to PyPI..."
echo ""

cd "$(dirname "$0")/../sdk"

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build
echo "Building package..."
python -m build

# Check
echo ""
echo "Checking package..."
twine check dist/*

echo ""
echo "Build successful! Package ready for upload."
echo ""
echo "To upload to PyPI:"
echo "  twine upload dist/*"
echo ""
echo "To upload to Test PyPI first:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "You will need PyPI credentials (API token recommended)."
