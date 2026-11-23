$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Runtime = Join-Path $Root ".runtime\whispercpp"
$BinDir = Join-Path $Runtime "bin"
$ModelDir = Join-Path $Runtime "models"
$WhisperVersion = "1.8.3"
$ArchiveUrl = "https://github.com/ggml-org/whisper.cpp/releases/download/v$WhisperVersion/whisper-bin-x64.zip"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "Ambiente virtual nao encontrado em .venv." -ForegroundColor Red
    Write-Host "Execute primeiro o instalador principal do assessor."
    exit 1
}

$ModelName = "base"
$EnvFile = Join-Path $Root ".env"
if (Test-Path -LiteralPath $EnvFile) {
    $Configured = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match '^ASSESSOR_AUDIO_MODELO=' } | Select-Object -Last 1
    if ($Configured) { $ModelName = (($Configured -split '=', 2)[1]).Trim() }
}
if ([string]::IsNullOrWhiteSpace($ModelName)) { $ModelName = "base" }
if ($ModelName -notmatch '^(tiny|base|small|medium|large-v[123]|large-v3-turbo)$') {
    throw "Modelo de audio nao permitido: $ModelName"
}
$ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$ModelName.bin"
$ModelPath = Join-Path $ModelDir "ggml-$ModelName.bin"
$ExePath = Join-Path $BinDir "whisper-cli.exe"

$TempDir = Join-Path $env:TEMP ("assessor_whispercpp_" + [guid]::NewGuid().ToString("N"))
$ResolvedTemp = [System.IO.Path]::GetFullPath($TempDir)
$TempRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
if (-not $ResolvedTemp.StartsWith($TempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Pasta temporaria fora do TEMP: $ResolvedTemp"
}

try {
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null

    Write-Host "Instalando voz local isolada com whisper.cpp..." -ForegroundColor Cyan
    Write-Host "Etapa 1/4 - Decodificador de audio" -ForegroundColor Cyan
    & $Python -m pip install --upgrade -r (Join-Path $Root "requirements-audio.txt")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Etapa 2/4 - whisper.cpp oficial v$WhisperVersion" -ForegroundColor Cyan
    $Archive = Join-Path $TempDir "whisper-bin-x64.zip"
    Invoke-WebRequest -UseBasicParsing -Uri $ArchiveUrl -OutFile $Archive
    $Extracted = Join-Path $TempDir "whisper"
    Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted -Force
    $DownloadedExe = Get-ChildItem -LiteralPath $Extracted -Recurse -File -Filter "whisper-cli.exe" | Select-Object -First 1
    if (-not $DownloadedExe) { throw "whisper-cli.exe nao encontrado no pacote oficial." }
    Copy-Item -Path (Join-Path $DownloadedExe.Directory.FullName "*") -Destination $BinDir -Recurse -Force

    Write-Host "Etapa 3/4 - Modelo ggml-$ModelName" -ForegroundColor Cyan
    if (-not (Test-Path -LiteralPath $ModelPath) -or (Get-Item -LiteralPath $ModelPath).Length -lt 1000000) {
        Invoke-WebRequest -UseBasicParsing -Uri $ModelUrl -OutFile $ModelPath
    } else {
        Write-Host "Modelo existente preservado: $ModelPath" -ForegroundColor DarkGray
    }

    Write-Host "Etapa 4/4 - Diagnostico local" -ForegroundColor Cyan
    Push-Location $Root
    try {
        & $Python -c "import json; from transcricao_audio import diagnosticar_audio; print(json.dumps(diagnosticar_audio(), ensure_ascii=False))"
        $DiagnosticExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($DiagnosticExit -ne 0 -or -not (Test-Path -LiteralPath $ExePath) -or -not (Test-Path -LiteralPath $ModelPath)) {
        throw "A instalacao terminou sem deixar o motor e o modelo prontos."
    }

    Write-Host ""
    Write-Host "Voz local instalada e validada." -ForegroundColor Green
    Write-Host "Backend: whisper.cpp $WhisperVersion / modelo $ModelName / CPU." -ForegroundColor Yellow
    Write-Host "O audio continua passando por revisao e nunca gera lancamento automatico." -ForegroundColor Yellow
} finally {
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force
    }
}
