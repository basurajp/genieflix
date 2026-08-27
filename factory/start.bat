@echo off
rem Windows launcher: starts the factory runner + dashboard.
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo error: node not found — run setup\setup-windows.ps1 first
  exit /b 1
)
node runner.mjs
