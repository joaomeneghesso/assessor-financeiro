# Publica a versão desta pasta (branch nuvem) no servidor do assessor (Google Cloud).
#
#   .\deploy\publicar.ps1              # gate -> backup no servidor -> envia -> reinicia -> confere
#   .\deploy\publicar.ps1 -SemGate     # só se o gate acabou de passar
#   .\deploy\publicar.ps1 -Desfazer    # volta o servidor para a versão anterior à última publicação
#
# Se o bot não subir depois de publicar, volta sozinho para a versão anterior.
# Nunca envia banco, .env ou backups: só código (git bundle).
param(
    [switch]$SemGate,
    [switch]$Desfazer,
    [string]$Servidor = "assessor@SEU_SERVIDOR",
    [string]$Chave = "$HOME\.ssh\assessor_nuvem"
)
$ErrorActionPreference = "Stop"
$Projeto = Split-Path $PSScriptRoot -Parent
Set-Location $Projeto
$Python = "C:\Projetos\assessor-financeiro\.venv\Scripts\python.exe"
$Remoto = "assessor-financeiro"

function Remoto([string]$comando) {
    $saida = & ssh -i $Chave -o ConnectTimeout=20 $Servidor $comando
    if ($LASTEXITCODE -ne 0) { throw "Falhou no servidor: $comando`n$saida" }
    return $saida
}

function Conferir-Bot {
    Start-Sleep -Seconds 20
    $estado = (Remoto "systemctl is-active assessor; systemctl show assessor -p NRestarts --value") -join " "
    return $estado -match '^active 0$'
}

if ($Desfazer) {
    $anterior = (Remoto "cat ~/.assessor_publicacao_anterior 2>/dev/null || true").Trim()
    if (-not $anterior) { throw "Não há publicação anterior registrada no servidor." }
    Write-Host "Voltando o servidor para $anterior ..."
    Remoto "cd $Remoto && git reset -q --hard $anterior && sudo systemctl restart assessor" | Out-Null
    if (Conferir-Bot) { Write-Host "OK: bot rodando na versão $anterior." } else { throw "O bot não subiu após desfazer. Veja: journalctl -u assessor -n 50" }
    exit 0
}

Write-Host "== 1/5 Conferindo o código local"
if (git status --porcelain) { throw "Há alterações não commitadas em $Projeto. Faça o commit antes de publicar." }
if ((git branch --show-current) -ne "nuvem") { throw "Publique a partir da branch nuvem." }
$versao = (git log --oneline -1)
Write-Host "   $versao"

if (-not $SemGate) {
    Write-Host "== 2/5 Gate oficial (Windows)"
    $saida = Join-Path $env:TEMP "assessor-gate-publicar"
    & $Python .\validacao\validar_versao_oficial.py --projeto $Projeto --workers 4 --timeout 1500 --saida $saida | Out-Null
    $r = Get-Content (Join-Path $saida "resultado.json") -Raw | ConvertFrom-Json
    if (-not $r.approved) { throw "Gate reprovado ($($r.failures) falhas, $($r.errors) erros, $($r.skipped) pulados). Nada foi publicado." }
    Write-Host "   Gate aprovado: $($r.tests)/$($r.tests)"
} else { Write-Host "== 2/5 Gate pulado (-SemGate)" }

Write-Host "== 3/5 Backup do banco no servidor"
# Sem aspas duplas no comando remoto (o PowerShell 5.1 as remove ao chamar o ssh): o prefixo vai como argumento.
$backup = Remoto "cd $Remoto && .venv/bin/python -c 'import sys, services; print(services.criar_backup_db(sys.argv[1])[0])' pre_publicacao 2>/dev/null | tail -1"
Write-Host "   $backup"
$anterior = (Remoto "cd $Remoto && git rev-parse HEAD").Trim()

Write-Host "== 4/5 Enviando e reiniciando"
$bundle = Join-Path $env:TEMP "assessor-nuvem.bundle"
git bundle create $bundle nuvem 2>$null | Out-Null
& scp -q -i $Chave $bundle "${Servidor}:assessor-nuvem.bundle"
if ($LASTEXITCODE -ne 0) { throw "Falha ao enviar o código. Nada foi alterado no servidor." }
Remoto "cd $Remoto && git pull -q --ff-only ../assessor-nuvem.bundle nuvem && echo $anterior > ~/.assessor_publicacao_anterior && ~/.local/bin/uv pip install -q --python .venv/bin/python -r requirements.txt -r requirements-audio.txt && sudo systemctl restart assessor" | Out-Null

Write-Host "== 5/5 Conferindo o bot"
if (Conferir-Bot) {
    Write-Host "OK: publicado e rodando. Versão: $versao"
    Write-Host "   Para desfazer: .\deploy\publicar.ps1 -Desfazer"
} else {
    Write-Host "O bot não subiu. Voltando sozinho para a versão anterior ($anterior)..."
    Remoto "cd $Remoto && git reset -q --hard $anterior && sudo systemctl restart assessor" | Out-Null
    if (Conferir-Bot) { throw "Publicação desfeita: o bot voltou à versão anterior. Veja o erro: journalctl -u assessor -n 50" }
    throw "ATENÇÃO: o bot não subiu nem na versão anterior. Veja: journalctl -u assessor -n 50"
}
