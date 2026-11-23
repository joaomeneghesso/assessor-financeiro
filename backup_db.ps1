$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PythonAssessor = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonAssessor)) {
    throw "Ambiente Python nao encontrado. Execute instalar.ps1 primeiro."
}
# A API SQLite copia tambem as transacoes confirmadas presentes no WAL.
& $PythonAssessor -c "from services import criar_backup_db; p,_ = criar_backup_db(); print(p if p else 'Banco nao encontrado.'); raise SystemExit(0 if p else 1)"
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar e validar o backup." }
