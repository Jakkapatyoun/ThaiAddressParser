@echo off
chcp 65001 >nul
:: ─────────────────────────────────────────────────────────────
::  build_exe_windows.bat — Build ThaiAddressParser.exe
::  ต้องรันบน Windows ที่มี Python 3.9+ ติดตั้งแล้ว
::  ผลลัพธ์: dist\ThaiAddressParser.exe (ย้ายไปใช้ที่ไหนก็ได้)
:: ─────────────────────────────────────────────────────────────
title Build Thai Address Parser .exe

echo.
echo  ========================================================
echo   Thai Address Parser - Build Windows .exe
echo  ========================================================
echo.

cd /d "%~dp0"

:: ── ตรวจ Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] ไม่พบ Python!
    echo.
    echo  วิธีติดตั้ง Python บน Windows:
    echo   1. ไปที่ https://python.org/downloads
    echo   2. กด "Download Python 3.x.x"
    echo   3. เปิด installer → ติ๊ก "Add Python to PATH"
    echo   4. กด Install Now
    echo   5. รัน build_exe_windows.bat อีกครั้ง
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo  [OK] %%i

:: ── ติดตั้ง dependencies ──
echo.
echo  [1/3] ติดตั้ง dependencies...
pip install pyinstaller openpyxl colorama --quiet
if errorlevel 1 (
    echo  [!] ติดตั้ง dependency ล้มเหลว กรุณาตรวจ internet connection
    pause
    exit /b 1
)
echo  [OK] dependencies พร้อมแล้ว

:: ── ลบ build เก่า ──
echo.
echo  [2/3] ลบ build เก่า...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist ThaiAddressParser.spec del /q ThaiAddressParser.spec

:: ── Build .exe ──
echo.
echo  [3/3] กำลัง build .exe ... (ใช้เวลา 1-3 นาที)
echo.

pyinstaller ^
  --name "ThaiAddressParser" ^
  --onefile ^
  --windowed ^
  --add-data "data\thai_administrative_areas.csv;data" ^
  --add-data "data\MASTER_DATA_SOURCE.md;data" ^
  --add-data "address_parser;address_parser" ^
  --hidden-import "address_parser" ^
  --hidden-import "address_parser.models" ^
  --hidden-import "address_parser.knowledge_base" ^
  --hidden-import "address_parser.parser" ^
  --hidden-import "openpyxl" ^
  --hidden-import "openpyxl.styles" ^
  --hidden-import "openpyxl.utils" ^
  --hidden-import "colorama" ^
  --hidden-import "difflib" ^
  --hidden-import "sqlite3" ^
  --hidden-import "tkinter" ^
  --hidden-import "tkinter.ttk" ^
  --hidden-import "tkinter.filedialog" ^
  --hidden-import "tkinter.messagebox" ^
  --noconfirm ^
  gui_app.py

if errorlevel 1 (
    echo.
    echo  [!] Build ล้มเหลว — ดู error ด้านบน
    pause
    exit /b 1
)

echo.
echo  ========================================================
echo   Build สำเร็จ!
echo  ========================================================
echo.
echo  ไฟล์ที่ได้: dist\ThaiAddressParser.exe
echo.
echo  วิธีใช้:
echo   GUI  : ดับเบิลคลิก dist\ThaiAddressParser.exe
echo   CLI  : dist\ThaiAddressParser.exe input.xlsx --col "ที่อยู่"
echo.
echo  Knowledge DB จะเก็บที่:
echo   %%USERPROFILE%%\Documents\ThaiAddressParser\data\address_knowledge.db
echo.

:: เปิดโฟลเดอร์ dist อัตโนมัติ
explorer dist

pause
