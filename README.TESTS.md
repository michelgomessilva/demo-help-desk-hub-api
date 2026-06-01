# 🧪 Guia Rápido de Testes

## Início Rápido (5 minutos)

### 1️⃣ Instalar Dependências de Teste

**Windows (PowerShell):**
```powershell
# Via script (recomendado)
.\setup_tests.bat

# Ou manualmente com uv
uv add --dev pytest pytest-asyncio httpx
```

**Linux/Mac (Bash):**
```bash
# Via script (recomendado)
bash setup_tests.sh

# Ou manualmente com uv
uv add --dev pytest pytest-asyncio httpx
```

### 2️⃣ Executar Testes

```bash
# Todos os testes
uv run pytest

# Com saída detalhada
uv run pytest -v

# Com cobertura de código
uv run pytest --cov=src --cov-report=html
```

### 3️⃣ Ver Resultado

```
======================== test session starts =========================
collected 188 items

tests/test_auth_service.py ............................ [ 14%]
tests/test_ticket_service.py ................................... [ 39%]
tests/test_in_memory_repository.py ........................... [ 56%]
tests/test_api_routes.py ............................... [ 68%]
tests/test_domain.py ...................................... [ 86%]
tests/test_app_configuration.py ............................ [100%]

======================== 188 passed in 2.34s ==========================
```

## 📋 Testes Disponíveis

| Arquivo | Testes | Descrição |
|---------|--------|-----------|
| `test_auth_service.py` | 37 | Autenticação, hash de senhas, registro |
| `test_ticket_service.py` | 68 | Criação, listagem, atualização de tickets |
| `test_in_memory_repository.py` | 45 | Operações com dados em memória |
| `test_api_routes.py` | 31 | Endpoints HTTP da API |
| `test_domain.py` | 47 | Modelos, enums e exceções |
| `test_app_configuration.py` | 35 | Configuração e inicialização |

**Total: 188 testes**

## 🎯 Comandos Úteis

### Testes Específicos

```bash
# Um arquivo
uv run pytest tests/test_auth_service.py

# Uma classe
uv run pytest tests/test_auth_service.py::TestPasswordHashing

# Um método
uv run pytest tests/test_auth_service.py::TestPasswordHashing::test_hash_password_returns_string

# Com padrão no nome
uv run pytest -k "test_hash"
uv run pytest -k "password and not verify"
```

### Controle de Execução

```bash
# Parar no primeiro erro
uv run pytest -x

# Mostrar últimos 3 testes que falharam
uv run pytest --lf -v

# Executar apenas testes rápidos
uv run pytest -m "not slow"

# Listar testes sem executar
uv run pytest --collect-only
```

### Análise de Cobertura

```bash
# Instalar pytest-cov (uma vez)
uv add --dev pytest-cov

# Gerar relatório HTML
uv run pytest --cov=src --cov-report=html

# Abrir relatório (Windows)
start htmlcov\index.html

# Abrir relatório (Mac)
open htmlcov/index.html

# Abrir relatório (Linux)
firefox htmlcov/index.html
```

### Debug

```bash
# Mostrar print statements
uv run pytest -s

# Debugger interativo
uv run pytest --pdb

# Verbose com traceback
uv run pytest -vv --tb=long
```

## 📖 Estrutura de Testes

```
tests/
├── conftest.py                  # Fixtures compartilhadas
├── test_auth_service.py         # Testes de autenticação
├── test_ticket_service.py       # Testes de tickets
├── test_in_memory_repository.py # Testes de dados
├── test_api_routes.py           # Testes de API
├── test_domain.py               # Testes de modelos
└── test_app_configuration.py    # Testes de config
```

## 🔧 Fixtures Úteis

Use estas fixtures nos seus testes:

```python
def test_example(self, ticket_service, auth_service, client):
    # ticket_service: TicketService pré-configurado
    # auth_service: AuthService pré-configurado
    # client: Cliente HTTP para testar rotas
    pass
```

## 🚀 Integrando com Git

Executar testes antes de fazer commit:

```bash
# Pre-commit hook
echo 'uv run pytest' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## ❓ FAQ

**P: Testes estão lentos?**
R: Isso é normal na primeira execução. Use `uv run pytest -x` para parar no primeiro erro.

**P: Como adicionar novos testes?**
R: Crie um arquivo `test_algo.py` em `tests/` e siga o padrão `test_o_que_testa()`.

**P: Preciso de dados reais nos testes?**
R: Use as fixtures em `conftest.py` - elas criam dados de teste automaticamente.

**P: Como mockar dependências?**
R: Use `unittest.mock.Mock` ou as fixtures já preparadas.

## 📚 Documentação Completa

Para guia detalhado, veja:
- [TESTING.md](TESTING.md) - Guia completo
- [TESTS_SUMMARY.md](TESTS_SUMMARY.md) - Resumo técnico

## ⚡ TL;DR

```bash
# Setup (primeira vez)
uv add --dev pytest pytest-asyncio httpx

# Executar testes
uv run pytest

# Verificar cobertura
uv run pytest --cov=src

# Feito! ✨
```

Perguntas? Consulte a documentação completa em [TESTING.md](TESTING.md)
