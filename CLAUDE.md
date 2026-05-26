# CLAUDE.md

## โปรเจกต์นี้คืออะไร

**Thai Address Parser** คือระบบแยกส่วนที่อยู่ภาษาไทย/อังกฤษ พร้อม self-learning knowledge base  
ทำงาน **offline 100%** — ไม่ต้องพึ่ง AI API ภายนอก

ภาษา: **Python 3**  
Database: **SQLite** (ผ่าน standard library `sqlite3`)  
UI: **CLI** (`main.py`) + **GUI** (`gui_app.py` — Tkinter)

---

## โครงสร้างโปรเจกต์

```
ThaiAddressParser/
├── address_parser/
│   ├── __init__.py          — package init, export public API
│   ├── models.py            — ParsedAddress dataclass
│   ├── knowledge_base.py    — SQLite self-learning KB (29 KB)
│   └── parser.py            — parsing engine หลัก (15 KB)
├── data/
│   ├── thai_administrative_areas.csv  — master data จังหวัด/อำเภอ/ตำบล/ไปรษณีย์ (7,436 รายการ)
│   ├── MASTER_DATA_SOURCE.md          — แหล่งที่มาของ master data
│   └── LICENSE.thailand-geography-json.txt
├── scripts/
│   └── download_master_data.py  — script ดาวน์โหลด master data ใหม่
├── tests/
│   └── test_parser.py           — unit tests (20 KB)
├── main.py                  — CLI หลัก (23 KB)
├── gui_app.py               — GUI application Tkinter (37 KB)
├── requirements.txt         — dependencies
├── sample_addresses.csv     — ตัวอย่างข้อมูลสำหรับทดสอบ
├── build_exe.sh             — สร้าง executable สำหรับ Linux/macOS
└── run_windows.bat          — รัน app บน Windows
```

---

## Dependencies

```bash
pip install -r requirements.txt
```

| Package | ใช้ทำอะไร | จำเป็น |
|---------|-----------|--------|
| `openpyxl>=3.1.0` | อ่าน/เขียน Excel (.xlsx) | ✅ ต้องติดตั้ง |
| `colorama>=0.4.6` | สีใน terminal | ❌ optional |
| `pyinstaller>=6.0.0` | build .exe | เฉพาะตอน build |

ไม่มี third-party ML/AI dependency — ใช้ `sqlite3`, `re`, `difflib` จาก standard library ล้วนๆ

---

## คำสั่งที่ใช้บ่อย

```bash
# รัน interactive menu
python main.py

# แยกที่อยู่ทีละบรรทัด
python main.py parse

# แยกที่อยู่จากไฟล์ CSV
python main.py csv sample_addresses.csv

# ดูสถิติ knowledge base
python main.py stats

# รัน benchmark (22,308 รายการจาก master data)
python main.py benchmark

# Export/Import knowledge base
python main.py export
python main.py import exports/knowledge_<timestamp>.json

# โหลด master data ใหม่เข้า DB
python main.py load-master

# รัน tests
python -m pytest tests/
```

---

## Architecture

### Parsing Engine (`address_parser/parser.py`)

แยกที่อยู่ด้วย 3 กลไกหลักตามลำดับ:

1. **Keyword matching** — regex จาก keywords เช่น `ซอย`, `ถนน`, `หมู่`, `อำเภอ` ใน knowledge base
2. **Administrative master matching** — ค้นหา fuzzy match กับ ตำบล/อำเภอ/จังหวัด/รหัสไปรษณีย์ จาก SQLite
3. **User correction recall** — ดึง verified result จากที่อยู่ต้นฉบับเดียวกันที่เคยแก้ไขแล้ว

### Knowledge Base (`address_parser/knowledge_base.py`)

- ใช้ **SQLite** เก็บ 2 ส่วน:
  - `learned_examples` — ที่อยู่ที่ผู้ใช้ verified แล้ว
  - `keywords` — คำสำคัญสำหรับ regex matching
- รองรับ **Export/Import JSON** เพื่อแชร์ระหว่างเครื่อง
- DB ถูกสร้างอัตโนมัติที่ `data/address_knowledge.db` (ไม่ commit ใน git)

### Data Model (`address_parser/models.py`)

`ParsedAddress` dataclass มี fields:
- `house_no`, `village`, `moo`, `soi`, `road`
- `subdistrict` (ตำบล/แขวง), `district` (อำเภอ/เขต), `province` (จังหวัด)
- `postal_code`, `raw_input`, `confidence`, `source`

---

## รูปแบบที่อยู่ที่รองรับ

```
# แบบเต็ม
123/4 หมู่ 5 ซอยพหลโยธิน 12 ถนนพหลโยธิน ตำบลคลองหนึ่ง อำเภอคลองหลวง จังหวัดปทุมธานี 12120

# แบบย่อ
99 ม.3 ถ.สุขุมวิท แขวงพระโขนง เขตวัฒนา กทม 10110

# กรุงเทพฯ
456 ซ.อ่อนนุช 46 ถ.อ่อนนุช แขวงสวนหลวง เขตสวนหลวง กรุงเทพมหานคร 10250

# ภาษาอังกฤษ
No. 55 Moo 2 Soi Sukhumvit 71 Road Sukhumvit Bangkok 10110
```

---

## Build Executable

```bash
# Linux / macOS
bash build_exe.sh

# Windows
build_exe_windows.bat
```

ใช้ **PyInstaller** สร้าง standalone binary ที่รันได้โดยไม่ต้องติดตั้ง Python

---

## Master Data

- ที่มา: [`thailand-geography-data/thailand-geography-json`](https://github.com/thailand-geography-data/thailand-geography-json) (MIT License)
- มีข้อมูล 7,436 รายการ (จังหวัด/อำเภอ/ตำบล/รหัสไปรษณีย์)
- ไฟล์: `data/thai_administrative_areas.csv`
- อัปเดต master data: `python scripts/download_master_data.py` แล้ว `python main.py load-master`

---

## ข้อควรระวัง

- `data/address_knowledge.db` ไม่ควร commit เข้า git (อยู่ใน `.gitignore`)
- `exports/` folder สร้างอัตโนมัติเมื่อ export — ไม่ต้องสร้างเอง
- benchmark ไม่ได้วัดความแม่นยำบนที่อยู่จริง — ใช้เพื่อ regression testing เท่านั้น
