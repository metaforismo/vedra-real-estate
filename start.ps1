$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 'Vedra richiede Python 3.11+')"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ richiesto" }
if (-not (Test-Path ".venv/Scripts/python.exe")) { python -m venv .venv }
if ($LASTEXITCODE -ne 0) { throw "Creazione virtualenv fallita" }
& .venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Installazione dipendenze fallita" }
& .venv/Scripts/python.exe scripts/setup.py
if ($LASTEXITCODE -ne 0) { throw "Setup fallito" }
& .venv/Scripts/python.exe scripts/run.py @args
