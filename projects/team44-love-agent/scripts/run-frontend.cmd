@echo off
REM Wrapper that bypasses PowerShell execution policy and runs run-frontend.ps1.
REM Usage: scripts\run-frontend.cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-frontend.ps1" %*
