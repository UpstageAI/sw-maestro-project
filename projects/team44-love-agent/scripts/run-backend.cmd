@echo off
REM Wrapper that bypasses PowerShell execution policy and runs run-backend.ps1.
REM Usage: scripts\run-backend.cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-backend.ps1" %*
