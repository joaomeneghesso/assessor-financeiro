$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PythonAssessor = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonAssessor)) {
    throw "Ambiente Python nao encontrado. Execute instalar.ps1 primeiro."
}
& $PythonAssessor (Join-Path $PSScriptRoot "app.py")
exit $LASTEXITCODE
