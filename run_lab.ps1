# Bitácora: 2026-09-05 - Fase 1: launcher PowerShell para extracción RAW.
param([string]$InputFile, [switch]$Resume)
$ErrorActionPreference = 'Stop'
Write-Host 'LAB PDF TRANSLATOR — Phase 1: Structured RAW Extraction'
$python = if (Test-Path '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'python' }
$env:PYTHONPATH = "$(Join-Path $PSScriptRoot 'src')$([IO.Path]::PathSeparator)$env:PYTHONPATH"
$arguments = @('-m', 'lab_pdf_translator', 'extract')
if ($InputFile) { $arguments += @('--input', $InputFile) }
if ($Resume) { $arguments += '--resume' }
& $python @arguments
exit $LASTEXITCODE
