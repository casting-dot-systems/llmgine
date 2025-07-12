#!/bin/bash
# Development setup script for LLMgine

set -e

echo "🚀 Setting up LLMgine development environment..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
min_version="3.11"

if [ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]; then
    echo "❌ Python 3.11+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv pip install -e ".[dev]"

# Set up pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual API keys!"
else
    echo "✅ .env file already exists"
fi


# Run a quick check
echo "🧪 Running quick validation..."
python -c "import llmgine; print('✅ LLMgine package imports successfully')"
pytest --collect-only > /dev/null && echo "✅ Tests can be discovered"

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run tests: make test"
echo "3. Try a demo: make demo"
echo ""
echo "Available commands:"
echo "  make help     # Show all available commands"
echo "  make check    # Run all quality checks"
echo "  python scripts/dev.py --help  # Alternative dev script"