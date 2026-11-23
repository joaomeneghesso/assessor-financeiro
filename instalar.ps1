$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PythonAssessor = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonAssessor)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente Python." }
}
& $PythonAssessor -m pip install -r (Join-Path $PSScriptRoot "requirements-tooling.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar as ferramentas de instalacao." }
& $PythonAssessor -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias." }
if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) {
    Copy-Item (Join-Path $PSScriptRoot ".env.example") (Join-Path $PSScriptRoot ".env")
    Write-Host "Arquivo .env criado. Configure token/usuario e execute preparar_seguranca_v40.py antes de iniciar."
}
Write-Host "Instalacao concluida."
