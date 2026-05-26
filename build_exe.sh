#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  build_exe.sh — Build Thai Address Parser
#  ได้: dist/ThaiAddressParser.app  (ย้ายได้ทันที ไม่ต้องพึ่งไฟล์อื่น)
# ─────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════╗"
echo "║    Thai Address Parser — Build macOS .app            ║"
echo "╚══════════════════════════════════════════════════════╝"

echo ""
echo "📦  ตรวจสอบ dependencies..."
pip3 install pyinstaller openpyxl colorama --quiet

echo "🧹  ลบ build เก่า..."
rm -rf build dist ThaiAddressParser.spec

echo ""
echo "🔨  กำลัง build... (ใช้เวลา ~30 วินาที)"
pyinstaller \
  --name "ThaiAddressParser" \
  --onedir \
  --windowed \
  --add-data "data/thai_administrative_areas.csv:data" \
  --add-data "data/MASTER_DATA_SOURCE.md:data" \
  --add-data "address_parser:address_parser" \
  --hidden-import "address_parser" \
  --hidden-import "address_parser.models" \
  --hidden-import "address_parser.knowledge_base" \
  --hidden-import "address_parser.parser" \
  --hidden-import "openpyxl" \
  --hidden-import "openpyxl.styles" \
  --hidden-import "openpyxl.utils" \
  --hidden-import "colorama" \
  --hidden-import "difflib" \
  --hidden-import "sqlite3" \
  --hidden-import "tkinter" \
  --hidden-import "tkinter.ttk" \
  --hidden-import "tkinter.filedialog" \
  --hidden-import "tkinter.messagebox" \
  --noconfirm \
  gui_app.py

echo ""
echo "✅  Build เสร็จแล้ว!"
echo ""
echo "📍  ไฟล์: dist/ThaiAddressParser.app  (ขนาด ~33MB)"
echo ""
echo "วิธีแจกจ่าย:"
echo "   1. copy  dist/ThaiAddressParser.app  ไปเครื่องอื่นได้เลย"
echo "   2. ไม่ต้องติดตั้ง Python หรือไฟล์อื่นใดๆ"
echo "   3. Knowledge DB จะสร้างที่: ~/Documents/ThaiAddressParser/data/"
echo ""
echo "วิธีใช้ GUI:  ดับเบิลคลิก dist/ThaiAddressParser.app"
echo "วิธีใช้ CLI:  dist/ThaiAddressParser.app/Contents/MacOS/ThaiAddressParser input.xlsx --col \"ที่อยู่\""
