#requires -Version 5.1
<#
.SYNOPSIS
    Simulador de carga para a HelpDesk Hub API — gera tráfego contínuo para
    observar logs, traces e métricas no Grafana.

.DESCRIPTION
    Corre INDEFINIDAMENTE até ser interrompido com Ctrl+C.

    O que faz em cada iteração (ação escolhida aleatoriamente por peso):
      - Cria utilizadores via POST /auth/register e autentica-os (POST /auth/login),
        mantendo uma "pool" de utilizadores com token JWT.
      - Chama endpoints PÚBLICOS:  GET / , GET /categories , GET /health/ready
      - Chama endpoints AUTENTICADOS (com Bearer token de um utilizador da pool):
          POST   /tickets/                 (criar ticket)
          GET    /tickets/                 (listar, com filtros/paginação aleatórios)
          GET    /tickets/{id}             (obter)
          PATCH  /tickets/{id}             (atualizar estado/prioridade)
          POST   /tickets/{id}/comments    (comentar)
          GET    /tickets/{id_inexistente} (gera 404 de propósito)

    O token de cada utilizador é renovado automaticamente em caso de 401 ou
    expiração. Mostra cada pedido com cor por código de status e imprime um
    resumo periódico (e um resumo final ao parar com Ctrl+C).

.PARAMETER BaseUrl
    URL base da API. Default: http://localhost:8000

.PARAMETER MinDelayMs / MaxDelayMs
    Intervalo (jitter) aleatório entre pedidos, em milissegundos.

.PARAMETER MaxUsers
    Tamanho máximo da pool de utilizadores em memória.

.PARAMETER SummaryEvery
    De quantas em quantas iterações imprime o resumo parcial.

.EXAMPLE
    ./scripts/load-test.ps1

.EXAMPLE
    # Mais intenso (menos pausa entre pedidos)
    ./scripts/load-test.ps1 -MinDelayMs 50 -MaxDelayMs 200

.EXAMPLE
    # Apontar para outra instância
    ./scripts/load-test.ps1 -BaseUrl http://localhost:8000

.NOTES
    Para MAIS carga, abre vários terminais e corre o script em cada um.
    Pára com Ctrl+C — verás um resumo dos pedidos efetuados.
#>

[CmdletBinding()]
param(
    [string] $BaseUrl = "http://localhost:8000",
    [int]    $MinDelayMs = 150,
    [int]    $MaxDelayMs = 600,
    [int]    $MaxUsers = 50,
    [int]    $SummaryEvery = 20,
    [string] $Password = "LoadTest123!",
    [int]    $TimeoutSec = 10
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

# ---------------------------------------------------------------------------
# Estado partilhado
# ---------------------------------------------------------------------------
$script:Users      = New-Object System.Collections.ArrayList   # @{ Email; Token; TokenTime }
$script:TicketIds  = New-Object System.Collections.ArrayList   # ids de tickets criados
$script:StartTime  = Get-Date
$script:Iter       = 0
$script:UsersCreated  = 0
$script:TicketsCreated = 0
$script:Stats = @{ "2xx" = 0; "3xx" = 0; "4xx" = 0; "5xx" = 0; "err" = 0 }

# Dados para gerar nomes (apenas letras/espaços — validados pela API)
$FirstNames = @("Ana","Bruno","Carla","Diogo","Eva","Filipe","Gabriela","Hugo",
                "Ines","Joao","Katia","Luis","Marta","Nuno","Olga","Pedro",
                "Rita","Sofia","Tiago","Vera")
$LastNames  = @("Silva","Santos","Ferreira","Pereira","Costa","Martins","Rocha",
                "Carvalho","Gomes","Lopes","Marques","Almeida","Ribeiro","Pinto")

$TicketTitles = @(
    "Nao consigo fazer login","Ecra azul ao arrancar","Impressora nao responde",
    "Email nao sincroniza","VPN cai constantemente","Aplicacao muito lenta",
    "Erro 500 ao gravar","Rato sem funcionar","Wifi instavel no piso 3",
    "Pedido de novo acesso","Disco cheio","Atualizacao falhou"
)
$Priorities  = @("low","medium","high","urgent")
$Categories  = @("access","hardware","software","network")
$Statuses    = @("open","in_progress","resolved","closed")
$CommentTxts = @(
    "A investigar o problema.","Pode reiniciar a maquina, por favor?",
    "Resolvido apos limpar a cache.","Escalado para a equipa de redes.",
    "A aguardar resposta do utilizador.","Confirmado, vou tratar disto hoje."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Log {
    param([int]$Status, [string]$Method, [string]$Path, [string]$Extra = "")
    $ts = (Get-Date).ToString("HH:mm:ss")
    if     ($Status -ge 200 -and $Status -lt 300) { $color = "Green" }
    elseif ($Status -ge 300 -and $Status -lt 400) { $color = "Cyan" }
    elseif ($Status -ge 400 -and $Status -lt 500) { $color = "Yellow" }
    elseif ($Status -ge 500)                       { $color = "Red" }
    else                                           { $color = "DarkGray" }  # 0 = erro de rede
    $code = if ($Status -eq 0) { "ERR" } else { "$Status" }
    Write-Host ("[{0}] {1,3}  {2,-6} {3,-28} {4}" -f $ts, $code, $Method, $Path, $Extra) -ForegroundColor $color
}

function Update-Stats {
    param([int]$Status)
    if     ($Status -ge 200 -and $Status -lt 300) { $script:Stats["2xx"]++ }
    elseif ($Status -ge 300 -and $Status -lt 400) { $script:Stats["3xx"]++ }
    elseif ($Status -ge 400 -and $Status -lt 500) { $script:Stats["4xx"]++ }
    elseif ($Status -ge 500)                       { $script:Stats["5xx"]++ }
    else                                           { $script:Stats["err"]++ }
}

function Invoke-Api {
    <#
      Wrapper compatível com PS 5.1 e 7. Devolve sempre um objeto:
        @{ Ok = $bool; Status = <int>; Data = <obj|$null>; Error = <string> }
      Nunca lança — códigos 4xx/5xx são tratados como resultado normal.
    #>
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [string]$Token = $null
    )
    $uri = "$BaseUrl$Path"
    $headers = @{}
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }

    $params = @{
        Uri         = $uri
        Method      = $Method
        Headers     = $headers
        TimeoutSec  = $TimeoutSec
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params["Body"]        = ($Body | ConvertTo-Json -Depth 6 -Compress)
        $params["ContentType"] = "application/json"
    }

    try {
        $resp = Invoke-RestMethod @params
        return @{ Ok = $true; Status = 200; Data = $resp; Error = $null }
    }
    catch {
        $status = 0
        $resp = $_.Exception.Response
        if ($resp -ne $null) {
            try {
                # PS7: HttpResponseException.Response.StatusCode (enum) ; PS5.1: WebException
                $status = [int]$resp.StatusCode
            } catch { $status = 0 }
        }
        return @{ Ok = $false; Status = $status; Data = $null; Error = $_.Exception.Message }
    }
}

function Get-RandomItem { param($Arr) return $Arr[(Get-Random -Minimum 0 -Maximum $Arr.Count)] }

function New-RandomName {
    return ("{0} {1}" -f (Get-RandomItem $FirstNames), (Get-RandomItem $LastNames))
}

function New-RandomEmail {
    $suffix = ([guid]::NewGuid().ToString("N")).Substring(0, 8)
    return "loadtest_$suffix@example.com"
}

# ---------------------------------------------------------------------------
# Ações
# ---------------------------------------------------------------------------
function Action-RegisterUser {
    if ($script:Users.Count -ge $MaxUsers) {
        # Pool cheia: em vez de registar, faz uma listagem pública para variar.
        return (Action-PublicCategories)
    }
    $email = New-RandomEmail
    $body  = @{ name = (New-RandomName); email = $email; password = $Password }
    $r = Invoke-Api -Method "POST" -Path "/auth/register" -Body $body
    Write-Log -Status $r.Status -Method "POST" -Path "/auth/register" -Extra $email
    Update-Stats $r.Status
    if (-not $r.Ok) { return }

    # Login imediato para obter token
    $login = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{ email = $email; password = $Password }
    Write-Log -Status $login.Status -Method "POST" -Path "/auth/login" -Extra $email
    Update-Stats $login.Status
    if ($login.Ok -and $login.Data.access_token) {
        [void]$script:Users.Add(@{ Email = $email; Token = $login.Data.access_token; TokenTime = (Get-Date) })
        $script:UsersCreated++
    }
}

function Get-AuthUser {
    <# Devolve um utilizador da pool com token válido (renova se preciso), ou $null. #>
    if ($script:Users.Count -eq 0) { Action-RegisterUser }
    if ($script:Users.Count -eq 0) { return $null }

    $u = Get-RandomItem $script:Users
    $ageMin = ((Get-Date) - $u.TokenTime).TotalMinutes
    if (-not $u.Token -or $ageMin -gt 25) {
        $login = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{ email = $u.Email; password = $Password }
        Update-Stats $login.Status
        if ($login.Ok -and $login.Data.access_token) {
            $u.Token = $login.Data.access_token
            $u.TokenTime = (Get-Date)
        } else {
            return $null
        }
    }
    return $u
}

function Invoke-AuthApi {
    <# Como Invoke-Api mas com retry único em 401 (re-login). #>
    param([string]$Method, [string]$Path, [object]$Body = $null, $User)
    $r = Invoke-Api -Method $Method -Path $Path -Body $Body -Token $User.Token
    if ($r.Status -eq 401) {
        $User.Token = $null
        $u2 = Get-AuthUser
        if ($u2) { $r = Invoke-Api -Method $Method -Path $Path -Body $Body -Token $u2.Token }
    }
    return $r
}

function Action-PublicRoot {
    $r = Invoke-Api -Method "GET" -Path "/"
    Write-Log -Status $r.Status -Method "GET" -Path "/"
    Update-Stats $r.Status
}

function Action-PublicCategories {
    $r = Invoke-Api -Method "GET" -Path "/categories"
    Write-Log -Status $r.Status -Method "GET" -Path "/categories"
    Update-Stats $r.Status
}

function Action-Readiness {
    $r = Invoke-Api -Method "GET" -Path "/health/ready"
    Write-Log -Status $r.Status -Method "GET" -Path "/health/ready"
    Update-Stats $r.Status
}

function Action-CreateTicket {
    $u = Get-AuthUser; if (-not $u) { return }
    $body = @{
        title       = (Get-RandomItem $TicketTitles)
        description = "Reportado automaticamente pelo simulador de carga. Detalhe #" + (Get-Random -Minimum 1000 -Maximum 9999)
        priority    = (Get-RandomItem $Priorities)
        category    = (Get-RandomItem $Categories)
    }
    $r = Invoke-AuthApi -Method "POST" -Path "/tickets/" -Body $body -User $u
    $extra = ""
    if ($r.Ok -and $r.Data.id) {
        [void]$script:TicketIds.Add([int]$r.Data.id)
        $script:TicketsCreated++
        $extra = "id=$($r.Data.id)"
        # Limitar memória de ids guardados
        if ($script:TicketIds.Count -gt 500) { $script:TicketIds.RemoveAt(0) }
    }
    Write-Log -Status $r.Status -Method "POST" -Path "/tickets/" -Extra $extra
    Update-Stats $r.Status
}

function Action-ListTickets {
    $u = Get-AuthUser; if (-not $u) { return }
    $qs = New-Object System.Collections.ArrayList
    if ((Get-Random -Maximum 2) -eq 1) { [void]$qs.Add("status="   + (Get-RandomItem $Statuses)) }
    if ((Get-Random -Maximum 2) -eq 1) { [void]$qs.Add("priority=" + (Get-RandomItem $Priorities)) }
    if ((Get-Random -Maximum 2) -eq 1) { [void]$qs.Add("category=" + (Get-RandomItem $Categories)) }
    [void]$qs.Add("page=" + (Get-Random -Minimum 1 -Maximum 4))
    [void]$qs.Add("size=" + (Get-RandomItem @(5,10,20)))
    $path = "/tickets/?" + ($qs -join "&")
    $r = Invoke-AuthApi -Method "GET" -Path $path -User $u
    $extra = if ($r.Ok -and $null -ne $r.Data.total) { "total=$($r.Data.total)" } else { "" }
    Write-Log -Status $r.Status -Method "GET" -Path $path -Extra $extra
    Update-Stats $r.Status
}

function Action-GetTicket {
    $u = Get-AuthUser; if (-not $u) { return }
    if ($script:TicketIds.Count -eq 0) { return (Action-CreateTicket) }
    $id = Get-RandomItem $script:TicketIds
    $r = Invoke-AuthApi -Method "GET" -Path "/tickets/$id" -User $u
    Write-Log -Status $r.Status -Method "GET" -Path "/tickets/$id"
    Update-Stats $r.Status
}

function Action-UpdateTicket {
    $u = Get-AuthUser; if (-not $u) { return }
    if ($script:TicketIds.Count -eq 0) { return (Action-CreateTicket) }
    $id = Get-RandomItem $script:TicketIds
    $body = @{ status = (Get-RandomItem $Statuses); priority = (Get-RandomItem $Priorities) }
    $r = Invoke-AuthApi -Method "PATCH" -Path "/tickets/$id" -Body $body -User $u
    Write-Log -Status $r.Status -Method "PATCH" -Path "/tickets/$id" -Extra ("-> " + $body.status)
    Update-Stats $r.Status
}

function Action-AddComment {
    $u = Get-AuthUser; if (-not $u) { return }
    if ($script:TicketIds.Count -eq 0) { return (Action-CreateTicket) }
    $id = Get-RandomItem $script:TicketIds
    $body = @{ content = (Get-RandomItem $CommentTxts) }
    $r = Invoke-AuthApi -Method "POST" -Path "/tickets/$id/comments" -Body $body -User $u
    Write-Log -Status $r.Status -Method "POST" -Path "/tickets/$id/comments"
    Update-Stats $r.Status
}

function Action-GetMissingTicket {
    # Gera 404 de propósito (logs de warning + traces de erro)
    $u = Get-AuthUser; if (-not $u) { return }
    $id = Get-Random -Minimum 900000 -Maximum 999999
    $r = Invoke-AuthApi -Method "GET" -Path "/tickets/$id" -User $u
    Write-Log -Status $r.Status -Method "GET" -Path "/tickets/$id" -Extra "(inexistente)"
    Update-Stats $r.Status
}

# Tabela de ações com pesos (quanto maior o peso, mais frequente)
$ActionTable = @(
    @{ Fn = "Action-RegisterUser";     Weight = 2 }
    @{ Fn = "Action-PublicRoot";       Weight = 2 }
    @{ Fn = "Action-PublicCategories"; Weight = 2 }
    @{ Fn = "Action-Readiness";        Weight = 1 }
    @{ Fn = "Action-CreateTicket";     Weight = 4 }
    @{ Fn = "Action-ListTickets";      Weight = 5 }
    @{ Fn = "Action-GetTicket";        Weight = 4 }
    @{ Fn = "Action-UpdateTicket";     Weight = 3 }
    @{ Fn = "Action-AddComment";       Weight = 3 }
    @{ Fn = "Action-GetMissingTicket"; Weight = 1 }
)
# Expandir por peso para sorteio simples
$ActionPool = New-Object System.Collections.ArrayList
foreach ($a in $ActionTable) { for ($i = 0; $i -lt $a.Weight; $i++) { [void]$ActionPool.Add($a.Fn) } }

function Show-Summary {
    param([string]$Title = "RESUMO PARCIAL")
    $elapsed = (Get-Date) - $script:StartTime
    $total = $script:Stats["2xx"] + $script:Stats["3xx"] + $script:Stats["4xx"] + $script:Stats["5xx"] + $script:Stats["err"]
    $rate = if ($elapsed.TotalSeconds -gt 0) { [math]::Round($total / $elapsed.TotalSeconds, 2) } else { 0 }
    Write-Host ""
    Write-Host ("===== $Title =====") -ForegroundColor Magenta
    Write-Host ("  Tempo decorrido : {0:hh\:mm\:ss}" -f $elapsed)
    Write-Host ("  Iteracoes       : {0}" -f $script:Iter)
    Write-Host ("  Pedidos totais  : {0}  (~{1}/s)" -f $total, $rate)
    Write-Host ("  2xx={0}  3xx={1}  4xx={2}  5xx={3}  err={4}" -f `
        $script:Stats["2xx"], $script:Stats["3xx"], $script:Stats["4xx"], $script:Stats["5xx"], $script:Stats["err"])
    Write-Host ("  Users na pool   : {0} (criados no total: {1})" -f $script:Users.Count, $script:UsersCreated)
    Write-Host ("  Tickets criados : {0} (ids em memoria: {1})" -f $script:TicketsCreated, $script:TicketIds.Count)
    Write-Host ("=========================================") -ForegroundColor Magenta
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Arranque: esperar pela API
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Simulador de carga - HelpDesk Hub API" -ForegroundColor Cyan
Write-Host "  Alvo      : $BaseUrl" -ForegroundColor Cyan
Write-Host "  Delay     : ${MinDelayMs}-${MaxDelayMs} ms entre pedidos" -ForegroundColor Cyan
Write-Host "  Pool max  : $MaxUsers utilizadores" -ForegroundColor Cyan
Write-Host "  Parar com : Ctrl+C" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "A aguardar que a API responda em $BaseUrl/health ..." -ForegroundColor DarkGray
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    $h = Invoke-Api -Method "GET" -Path "/health"
    if ($h.Ok) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Host "ERRO: a API nao respondeu em $BaseUrl. Esta a correr? (docker compose up -d)" -ForegroundColor Red
    exit 1
}
Write-Host "API disponivel. A iniciar simulacao..." -ForegroundColor Green
Write-Host ""

# Bootstrap: garantir pelo menos 1 utilizador e alguns tickets
Action-RegisterUser
for ($i = 0; $i -lt 3; $i++) { Action-CreateTicket }

# ---------------------------------------------------------------------------
# Loop principal (até Ctrl+C)
# ---------------------------------------------------------------------------
try {
    while ($true) {
        $script:Iter++
        $fn = Get-RandomItem $ActionPool
        try {
            & $fn
        }
        catch {
            # Nunca deixar uma falha pontual parar o simulador
            Write-Host ("[ACAO FALHOU] {0}: {1}" -f $fn, $_.Exception.Message) -ForegroundColor DarkRed
            Update-Stats 0
        }

        if (($script:Iter % $SummaryEvery) -eq 0) { Show-Summary }

        Start-Sleep -Milliseconds (Get-Random -Minimum $MinDelayMs -Maximum ($MaxDelayMs + 1))
    }
}
finally {
    Show-Summary -Title "RESUMO FINAL (simulacao terminada)"
    Write-Host "Abre o Grafana em http://localhost:3001 para ver os dados." -ForegroundColor Cyan
}
