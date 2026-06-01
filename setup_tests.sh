#!/bin/bash
# Script para configurar ambiente de testes (usando uv)

set -e  # Exit on error

echo "=========================================="
echo "  Configurando Ambiente de Testes (uv)"
echo "=========================================="
echo ""

# Verificar se uv está instalado
if ! command -v uv &> /dev/null; then
    echo "❌ uv não encontrado. Por favor, instale uv primeiro:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   ou visite: https://docs.astral.sh/uv/"
    exit 1
fi

echo "✅ uv encontrado: $(uv --version)"
echo ""

# Sincronizar dependências do projeto
echo "📦 Sincronizando dependências do projeto com uv sync..."
uv sync
echo "✅ Dependências sincronizadas"
echo ""

# Adicionar dependências de teste
echo "📦 Adicionando dependências de teste (pytest, pytest-asyncio, httpx)..."
uv add --dev pytest pytest-asyncio httpx
echo "✅ Dependências de teste adicionadas"
echo ""

# Verificar instalação
echo "🧪 Verificando instalação..."
uv run pytest --version
echo ""

# Sugerir próximos passos
echo "=========================================="
echo "  ✨ Ambiente de Testes Configurado!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Executar todos os testes:"
echo "   uv run pytest"
echo ""
echo "2. Executar testes com cobertura:"
echo "   uv add --dev pytest-cov"
echo "   uv run pytest --cov=src --cov-report=html"
echo ""
echo "3. Executar testes específicos:"
echo "   uv run pytest tests/test_auth_service.py"
echo ""
echo "4. Ver documentação:"
echo "   cat TESTING.md"
echo ""
