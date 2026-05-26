# Create the s2-ake Ollama model on the host where Ollama runs (e.g. r730).
# Usage: .\scripts\create-s2-ake-model.ps1 [-OllamaHost http://192.168.1.78:11434]

param(
  [string]$OllamaHost = $env:OLLAMA_HOST
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$modelfile = Join-Path $root "ollama\Modelfile.s2-ake"

if (-not (Test-Path $modelfile)) {
  Write-Error "Modelfile not found: $modelfile"
}

Write-Host "Pulling base llama3.2 if missing..."
ollama pull llama3.2

Write-Host "Creating s2-ake from $modelfile ..."
ollama create s2-ake -f $modelfile

Write-Host "Tags:"
ollama list | Select-String "s2-ake"

Write-Host "Done. Set OLLAMA_MODEL=s2-ake on the public-api service."
