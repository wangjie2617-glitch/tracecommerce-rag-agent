$ErrorActionPreference = "Stop"

$backendDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$alembic = Join-Path $backendDir ".venv\Scripts\alembic.exe"
$uvicorn = Join-Path $backendDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "backend\.venv was not found. Create the interpreter and install dependencies first."
}

Push-Location $backendDir
try {
    & $alembic upgrade head
    & $python scripts\seed_admin.py
    & $python scripts\init_milvus.py
    & $python scripts\ingest_bootstrap.py
    & $uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}
finally {
    Pop-Location
}
