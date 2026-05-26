@echo off
chcp 65001 >nul
:: ─────────────────────────────────────────────────────────────
::  run_windows.bat — รัน Thai Address Parser โดยตรง (ไม่ต้อง build exe)
::  ต้องมี Python 3.9+ ติดตั้งอยู่บน Windows
:: ─────────────────────────────────────────────────────────────
title Thai Address Parser

echo.
echo  ===============================================
echo   Thai Address Parser - Windows
echo  ===============================================
echo.

:: ── ตรวจว่ามี Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] ไม่พบ Python กรุณาติดตั้งจาก https://python.org
    echo      เลือก "Add Python to PATH" ตอนติดตั้ง
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo  Python: %%i

:: ── ติดตั้ง dependencies ──
echo.
echo  [*] ติดตั้ง dependencies...
pip install openpyxl colorama --quiet

:: ── รัน GUI ──
echo  [*] เปิดโปรแกรม...
echo.
cd /d "%~dp0"
python gui_app.py

pause
