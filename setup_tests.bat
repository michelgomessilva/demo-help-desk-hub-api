@echo off
REM Script para configurar ambiente de testes no Windows

echo.
echo ==========================================
echo   Configurando Ambiente de Testes
echo ==========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python nao encontrado. Por favor, instale Python 3.11+
    exit /b 1
)

echo ✅ Python encontrado:
python --version
echo.

REM Criar venv se não existir
if not exist ".venv" (
    echo 📦 Criando virtual environment...
    python -m venv .venv
    echo ✅ Virtual environment criado
) else (
    echo ✅ Virtual environment ja existe
)

echo.

REM Ativar venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo ✅ Virtual environment ativado
echo.

REM Instalar dependências principais
echo 📦 Instalando dependências principais...
pip install --upgrade pip setuptools wheel
pip install -e .
echo ✅ Dependências principais instaladas
echo.

REM Instalar dependências de teste
echo 📦 Instalando dependências de teste...
pip install pytest pytest-asyncio httpx
echo ✅ Dependências de teste instaladas
echo.

REM Verificar instalação
echo 🧪 Verificando instalação...
python -m pytest --version
echo.

REM Sugerir próximos passos
echo ==========================================
echo   ✨ Ambiente de Testes Configurado!
echo ==========================================
echo.
echo Proximos passos:
echo 1. Executar todos os testes:
echo    pytest
echo.
echo 2. Executar testes com cobertura:
echo    pytest --cov=src --cov-report=html
echo.
echo 3. Executar testes especificos:
echo    pytest tests/test_auth_service.py
echo.
echo 4. Ver documentacao:
echo    type TESTING.md
echo.
pause
