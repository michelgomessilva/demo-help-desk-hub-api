#!/bin/bash
# Script para configurar ambiente de testes

set -e  # Exit on error

echo "=========================================="
echo "  Configurando Ambiente de Testes"
echo "=========================================="
echo ""

# Verificar se Python está instalado
if ! command -v python &> /dev/null; then
    echo "❌ Python não encontrado. Por favor, instale Python 3.11+"
    exit 1
fi

echo "✅ Python encontrado: $(python --version)"
echo ""

# Criar venv se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando virtual environment..."
    python -m venv .venv
    echo "✅ Virtual environment criado"
else
    echo "✅ Virtual environment já existe"
fi

echo ""

# Ativar venv
if [ -f ".venv/Scripts/activate" ]; then
    # Windows
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    # Unix
    source .venv/bin/activate
fi

echo "✅ Virtual environment ativado"
echo ""

# Instalar dependências principais
echo "📦 Instalando dependências principais..."
pip install --upgrade pip setuptools wheel
pip install -e .
echo "✅ Dependências principais instaladas"
echo ""

# Instalar dependências de teste
echo "📦 Instalando dependências de teste..."
pip install pytest pytest-asyncio httpx
echo "✅ Dependências de teste instaladas"
echo ""

# Verificar instalação
echo "🧪 Verificando instalação..."
python -m pytest --version
echo ""

# Sugerir próximos passos
echo "=========================================="
echo "  ✨ Ambiente de Testes Configurado!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Executar todos os testes:"
echo "   pytest"
echo ""
echo "2. Executar testes com cobertura:"
echo "   pytest --cov=src --cov-report=html"
echo ""
echo "3. Executar testes específicos:"
echo "   pytest tests/test_auth_service.py"
echo ""
echo "4. Ver documentação:"
echo "   cat TESTING.md"
echo ""
