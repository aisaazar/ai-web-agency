$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  throw "Ollama is required. Install it before running this setup."
}
ollama create agency-qwen3-4k -f "$repoRoot\config\agency-qwen3-4k.Modelfile"
Write-Output "Created local model: agency-qwen3-4k"
Write-Output "Set AGENCY_LOCAL_LLM_MODEL=agency-qwen3-4k for the agency API."
