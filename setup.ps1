# One-time setup for Windows PowerShell. Run from inside the project folder:  .\setup.ps1
$ErrorActionPreference = "Stop"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python not found. Install Python 3.11+ from python.org and tick 'Add python.exe to PATH'." -ForegroundColor Red; exit 1
}
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# An old .env (with ANTHROPIC lines) is backed up and replaced, so the new free-LLM settings always apply.
$needNew = (-not (Test-Path .env))
if (-not $needNew) {
  if (Select-String -Path .env -Pattern "ANTHROPIC|CLAUDE_MODEL" -Quiet) {
    Copy-Item .env .env.old -Force; $needNew = $true
    Write-Host "Old .env found. Backed up as .env.old and replaced." -ForegroundColor Yellow
  }
}
if ($needNew) {
  $groq = (Read-Host "Paste your Groq key (starts with gsk_), or press Enter to add it later").Trim()
  $dg = (Read-Host "Paste your data.gov.in key, or press Enter to add it later").Trim()
  if (-not $groq) { $groq = "your_groq_key" }
  if (-not $dg) { $dg = "none" }
  @"
LLM_API_KEY=$groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
DATA_GOV_IN_API_KEY=$dg
TRANSPORT_RS_PER_QTL_KM=0.25
"@ | Set-Content -Path .env -Encoding ascii
  Write-Host ".env written." -ForegroundColor Green
}
& .\.venv\Scripts\python.exe -m pytest -q
Write-Host "`nSetup finished. Next:  .\.venv\Scripts\Activate.ps1  then  python check_llm.py  then  python check_data.py  then  streamlit run app.py" -ForegroundColor Green
