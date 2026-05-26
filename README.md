# 🏠 Thai Address Parser

ระบบแยกส่วนที่อยู่ไทย/อังกฤษ พร้อม **self-learning knowledge base**  
ทำงาน **offline 100%** — ไม่ต้องพึ่ง AI API ภายนอก

---

## ✨ Features

| Feature | รายละเอียด |
|---------|-----------|
| **แยกส่วนที่อยู่** | บ้านเลขที่, หมู่บ้าน, หมู่ที่, ซอย, ถนน, ตำบล/แขวง, อำเภอ/เขต, จังหวัด, รหัสไปรษณีย์ |
| **รองรับ 2 ภาษา** | ภาษาไทย + ภาษาอังกฤษ |
| **Self-learning** | เรียนรู้จากการแก้ไขของผู้ใช้ — ปรับปรุงตัวเองได้ |
| **Knowledge Base** | เก็บรูปแบบที่อยู่ใน SQLite (local) |
| **Administrative Master Data** | จังหวัด/อำเภอ/ตำบล/รหัสไปรษณีย์ 7,436 รายการใน SQLite |
| **Fuzzy Matching** | ค้นหาตัวอย่างที่คล้ายกันใน KB ได้อัตโนมัติ |
| **CSV Batch** | แยกที่อยู่หลายพันรายการจากไฟล์ CSV |
| **Export/Import** | แชร์ knowledge base ระหว่างเครื่องได้ |
| **Offline** | ไม่ต้องเชื่อมต่ออินเทอร์เน็ต |

---

## 🚀 ติดตั้ง

```bash
cd /Users/jp/Desktop/Address

# ติดตั้ง dependency (แค่ colorama สำหรับสี)
pip install -r requirements.txt

# หรือถ้าไม่ต้องการสี ใช้งานได้เลยโดยไม่ต้องติดตั้งอะไร
python main.py
```

---

## 📖 การใช้งาน

### เมนูหลัก (interactive)
```bash
python main.py
```

### แยกที่อยู่ทีละบรรทัด
```bash
python main.py parse
```

### แยกที่อยู่จากไฟล์ CSV
```bash
python main.py csv sample_addresses.csv
```

### ดูสถิติ Knowledge Base
```bash
python main.py stats
```

### จัดการ Keywords
```bash
python main.py keywords
```

### Export / Import Knowledge Base
```bash
python main.py export
python main.py import exports/knowledge_20240101_120000.json
```

### โหลดหรือ Refresh ข้อมูลพื้นที่ประเทศไทย
ไฟล์ `data/thai_administrative_areas.csv` ถูกจัดเก็บไว้กับโปรเจกต์ และจะถูก
โหลดเข้าฐานข้อมูลใหม่โดยอัตโนมัติ ถ้าต้องการดาวน์โหลดข้อมูลต้นทางใหม่แล้ว
นำเข้า DB เดิม:

```bash
python scripts/download_master_data.py
python main.py load-master
```

แหล่งข้อมูล: [`thailand-geography-data/thailand-geography-json`](https://github.com/thailand-geography-data/thailand-geography-json)
(MIT License) รายละเอียดอยู่ใน `data/MASTER_DATA_SOURCE.md`

### ทดสอบ Coverage จำนวนมาก
```bash
python main.py benchmark
```

คำสั่งนี้สร้าง full-address variants 3 รูปแบบต่อทุกตำบลจาก master data
รวม 22,308 รายการ แล้ววัด field/full-row accuracy โดย **ไม่** บันทึก
address จำลองเข้า learned examples

---

## 📂 โครงสร้างโปรเจกต์

```
Address/
├── address_parser/
│   ├── __init__.py         — package init
│   ├── models.py           — ParsedAddress dataclass
│   ├── knowledge_base.py   — SQLite self-learning KB
│   └── parser.py           — parsing engine
├── data/
│   ├── address_knowledge.db   — SQLite database (สร้างอัตโนมัติ)
│   └── thai_administrative_areas.csv — master data สำหรับ bootstrap offline
├── exports/                   — สร้างอัตโนมัติเมื่อ export knowledge
├── main.py                    — CLI หลัก
├── requirements.txt
├── sample_addresses.csv        — ตัวอย่าง CSV
└── README.md
```

---

## 🧠 Self-Learning คืออะไร?

ระบบเรียนรู้ผ่าน 3 ทาง:

1. **Keyword matching** — รู้จัก keywords เช่น "ซอย", "ถนน", "อำเภอ" จาก knowledge base  
2. **Administrative master matching** — ใช้ตำบล/อำเภอ/จังหวัด/รหัสไปรษณีย์
   เพื่อแยกชื่อพื้นที่ทั้งแบบมี label และแบบละ label
3. **User corrections** — เมื่อผู้ใช้แก้ไขผลลัพธ์ ระบบบันทึกผล verified และ
   นำกลับมาใช้เฉพาะที่อยู่ต้นฉบับเดียวกัน เพื่อไม่คัดลอกบ้านเลขที่ผิดไปยังรายการใหม่

---

## 📋 รูปแบบที่อยู่ที่รองรับ

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

## 💡 Tips

- ยิ่งใช้งานมาก ยิ่งแม่นยำขึ้น (self-learning)
- ใช้ `python main.py stats` เพื่อดูว่า KB เรียนรู้ไปมากแค่ไหน
- Export KB แล้ว Import ใน PC เครื่องอื่นได้
- เพิ่ม custom keywords ผ่านเมนู "จัดการ Keywords"

## ข้อจำกัดด้านความแม่นยำ

ผล `benchmark` เป็นการตรวจ coverage ของรูปแบบที่สร้างจาก master data เดียวกัน
จึงใช้ยืนยัน regression ของ parser ได้ แต่ไม่ใช่ค่าความแม่นยำบนที่อยู่จริงของ
ลูกค้าที่ยังไม่เคยเห็น ก่อนนำไปใช้ผลิตจริงควรสุ่มที่อยู่จริงที่ผ่านการตรวจโดย
คนแยกเป็นชุด validation และวัดผลซ้ำ โดยไม่ import ชุด validation เป็น knowledge
ก่อนวัด
