<#
.SYNOPSIS
    Runs Rust coverage with cargo-llvm-cov, excluding entry points and auto-generated files.
.DESCRIPTION
    Requires cargo-llvm-cov: cargo install cargo-llvm-cov
    Excludes main.rs (ASGI/WSGI equivalent entry point) from coverage.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineRoot = Resolve-Path "$ScriptDir\..\engine"

Write-Host "===== Running Rust engine coverage (cargo llvm-cov) =====" -ForegroundColor Cyan

cargo llvm-cov `
    --workspace `
    --lcov `
    --output-path "$ScriptDir\..\coverage\engine.lcov" `
    --ignore-filename-regex "main\.rs$" `
    --ignore-filename-regex "mod\.rs$"

Write-Host "Engine coverage report written to coverage/engine.lcov" -ForegroundColor Green
