@echo off
REM Script para configurar ambiente de testes no Windows (usando uv)

echo.
echo ==========================================
echo   Configurando Ambiente de Testes (uv)
echo ==========================================
echo.

REM Verificar se uv está instalado
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ uv nao encontrado. Por favor, instale uv primeiro:
    echo    powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    echo    ou visite: https://docs.astral.sh/uv/
    exit /b 1
)

echo ✅ uv encontrado:
uv --version
echo.

REM Sincronizar dependências do projeto
echo 📦 Sincronizando dependências do projeto com uv sync...
uv sync
if errorlevel 1 (
    echo ❌ Falha ao sincronizar dependências
    exit /b 1
)
echo ✅ Dependências sincronizadas
echo.

REM Adicionar dependências de teste
echo 📦 Adicionando dependências de teste (pytest, pytest-asyncio, httpx)...
uv add --dev pytest pytest-asyncio httpx
if errorlevel 1 (
    echo ❌ Falha ao adicionar dependências de teste
    exit /b 1
)
echo ✅ Dependências de teste adicionadas
echo.

REM Verificar instalação
echo 🧪 Verificando instalação...
uv run pytest --version
echo.

REM Sugerir próximos passos
echo ==========================================
echo   ✨ Ambiente de Testes Configurado!
echo ==========================================
echo.
echo Proximos passos:
echo 1. Executar todos os testes:
echo    uv run pytest
echo.
echo 2. Executar testes com cobertura:
echo    uv add --dev pytest-cov
echo    uv run pytest --cov=src --cov-report=html
echo.
echo 3. Executar testes especificos:
echo    uv run pytest tests/test_auth_service.py
echo.
echo 4. Ver documentacao:
echo    type TESTING.md
echo.
pause
