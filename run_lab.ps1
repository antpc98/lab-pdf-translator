# Bitácora: 2026-09-05 - Fase 1: launcher PowerShell para extracción RAW.
param([string]$InputFile, [switch]$Resume, [ValidateSet(1,2)][int]$Phase = 2)
$ErrorActionPreference = 'Stop'
Write-Host 'LAB PDF TRANSLATOR — governed pipeline'
$python = if (Test-Path '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'python' }
$env:PYTHONPATH = "$(Join-Path $PSScriptRoot 'src')$([IO.Path]::PathSeparator)$env:PYTHONPATH"
if ($Phase -eq 1 -or -not (Test-Path 'data\\raw\\document.json')) {
  $arguments = @('-m', 'lab_pdf_translator', 'extract')
  if ($InputFile) { $arguments += @('--input', $InputFile) }
  if ($Resume) { $arguments += '--resume' }
  & $python @arguments
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if ($Phase -eq 2) { & $python -m lab_pdf_translator normalize }
exit $LASTEXITCODE
