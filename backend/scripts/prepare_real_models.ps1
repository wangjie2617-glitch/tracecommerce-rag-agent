param(
    [ValidateSet("cpu", "cuda")]
    [string]$Device = "cpu",
    [switch]$StartApi,
    [switch]$SkipEvaluation
)

$ErrorActionPreference = "Stop"

$backendDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$uvicorn = Join-Path $backendDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "backend\.venv was not found. Create the interpreter and install dependencies first."
}

# Process-local overrides preserve the existing offline Fake/Mock profile.
$env:EMBEDDING_PROVIDER = "sentence_transformers"
$env:EMBEDDING_MODEL = "BAAI/bge-m3"
$env:EMBEDDING_DEVICE = $Device
$env:RERANKER_PROVIDER = "cross_encoder"
$env:RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
$env:RERANKER_DEVICE = $Device
$env:MILVUS_COLLECTION = "tracecommerce_chunks_bge_m3_v1"
$env:MIN_RETRIEVAL_SCORE = "0.35"
$env:MIN_EVIDENCE_SCORE = "0.45"

Write-Host "Preparing real retrieval profile:"
Write-Host "  Embedding:  BAAI/bge-m3 ($Device)"
Write-Host "  Reranker:   BAAI/bge-reranker-v2-m3 ($Device)"
Write-Host "  Collection: tracecommerce_chunks_bge_m3_v1"
Write-Host "The first run downloads model files and can take a long time on CPU."

Push-Location $backendDir
try {
    & $python scripts\init_milvus.py
    if ($LASTEXITCODE -ne 0) { throw "Milvus collection initialization failed." }

    & $python scripts\ingest_bootstrap.py
    if ($LASTEXITCODE -ne 0) { throw "Bootstrap ingestion failed." }

    if (-not $SkipEvaluation) {
        & $python scripts\evaluate_rag.py `
            --output reports\rag_evaluation_bge_m3.json `
            --minimum-precision 0.95
        if ($LASTEXITCODE -ne 0) { throw "RAG evaluation failed." }
    }

    if ($StartApi) {
        & $uvicorn app.main:app --host 127.0.0.1 --port 8000
    }
}
finally {
    Pop-Location
}
