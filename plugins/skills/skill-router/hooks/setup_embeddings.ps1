# setup_embeddings.ps1 — enable skill-router tier-2 (multilingual semantic match)
# Installs onnxruntime + tokenizers and downloads the MiniLM ONNX model.
# Run once:  py -3 ... no — just:  powershell -ExecutionPolicy Bypass -File setup_embeddings.ps1
# Safe to re-run (skips existing model files).

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$models = Join-Path $here "models"

Write-Host "[1/3] Installing Python deps (onnxruntime, tokenizers)..." -ForegroundColor Cyan
py -m pip install --quiet --upgrade onnxruntime tokenizers numpy
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $models)) { New-Item -ItemType Directory -Path $models | Out-Null }

$base = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main"
$files = @(
    @{ url = "$base/onnx/model_quantized.onnx"; out = "model_quantized.onnx" },
    @{ url = "$base/tokenizer.json";            out = "tokenizer.json" }
)

$i = 2
foreach ($f in $files) {
    $dest = Join-Path $models $f.out
    if (Test-Path $dest) {
        Write-Host "[$i/3] $($f.out) already present, skipping." -ForegroundColor DarkGray
    } else {
        Write-Host "[$i/3] Downloading $($f.out)..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $f.url -OutFile $dest
    }
    $i++
}

Write-Host "[3/3] Warming corpus vectors (first embed builds the cache)..." -ForegroundColor Cyan
py -c "import sys; sys.path.insert(0, r'$here'); import embed; print('matches:', len(embed.search('ทดสอบโค้ดแบบ test-first')))"
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDone. Tier-2 multilingual routing enabled." -ForegroundColor Green
} else {
    Write-Host "`nSetup ran but warm-up failed — check error above." -ForegroundColor Yellow
}
