#!/usr/bin/env python3
"""
seed_knowledge_base.py — เพิ่มตัวอย่างที่อยู่สุ่มลง Knowledge Base

วิธีรัน:
    python scripts/seed_knowledge_base.py                  # ครบ 1,000,000 รายการ
    python scripts/seed_knowledge_base.py --count 5000     # ระบุจำนวนเอง
    python scripts/seed_knowledge_base.py --dry-run        # ดูตัวอย่างโดยไม่บันทึก
    python scripts/seed_knowledge_base.py --dry-run --n 40 # ดูตัวอย่าง 40 รายการ

ที่อยู่จะถูกสร้างโดยการผสมผสาน:
  - บ้านเลขที่รูปแบบต่าง ๆ (123, 45/6, 789-1, 10ก, ...)
  - 7,436 ตำบล/แขวงจากข้อมูลมาตรฐาน
  - ชื่อถนน ซอย หมู่บ้าน อาคาร ห้องเลขที่ แบบสุ่ม
  - รูปแบบผสม: หมู่บ้าน+อาคาร, โครงการ+ตึก+ห้อง, คอนโด+ห้อง ฯลฯ
  - ที่อยู่ที่ parser แยกได้ครบ 4 fields จะถูก mark verified=True
    เพื่อให้ find_similar() ใช้งานได้ทันที
"""

import sys
import os
import csv
import json
import hashlib
import random
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# ── Project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from address_parser import KnowledgeBase, AddressParser

RANDOM_SEED = 42

# =============================================================================
#  ชุดข้อมูลสำหรับสุ่มสร้างที่อยู่
# =============================================================================

THAI_ROADS = [
    "สุขุมวิท", "พระราม 2", "พระราม 4", "พระราม 9", "รัชดาภิเษก",
    "ลาดพร้าว", "เพชรบุรี", "สีลม", "สาทร", "พหลโยธิน",
    "วิภาวดีรังสิต", "งามวงศ์วาน", "แจ้งวัฒนะ", "บางนา-ตราด",
    "ประชาชื่น", "รามคำแหง", "อโศก", "ทองหล่อ", "เอกมัย",
    "ประชาอุทิศ", "สุทธิสาร", "เจริญกรุง", "เยาวราช", "วรจักร",
    "ดินแดง", "บรมราชชนนี", "ปิ่นเกล้า", "จรัญสนิทวงศ์",
    "นวมินทร์", "มิตรภาพ", "อุดรดุษฎี", "ท่าแพ", "นิมมานเหมินท์",
    "ห้วยแก้ว", "โชตนา", "สนามบินน้ำ", "บางพลัด", "ราษฎร์บูรณะ",
    "เพชรเกษม", "กาญจนาภิเษก", "ติวานนท์", "รังสิต-นครนายก",
    "บางขุนเทียน", "สุขาภิบาล 1", "สุขาภิบาล 3", "นิมิตใหม่",
]

ENGLISH_ROADS = [
    "Sukhumvit", "Silom", "Sathorn", "Ratchadaphisek", "Phahon Yothin",
    "Ladprao", "Vibhavadi Rangsit", "Bangna-Trat", "Charoenkrung",
    "Yaowarat", "Phra Ram 4", "Wireless", "Ploenchit", "Asok",
    "Thonglor", "Ekkamai", "Ratchapruek", "Petchkasem",
]

SOI_NAMES_TH = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "สุขใจ", "ร่วมพัฒนา", "สามัคคี", "เจริญสุข", "ประชาสงเคราะห์",
    "สวนหลวง", "มิตรภาพ", "นิรันดร์", "สุขสวัสดิ์", "ศรีนครินทร์",
    "เจริญราษฎร์", "พัฒนาการ", "ลาดกระบัง", "สาธุประดิษฐ์",
]

SOI_NAMES_EN = [
    "1", "3", "5", "7", "9", "11", "13", "15", "17", "19", "21", "23",
    "Ruamrudee", "Nana", "Asok", "Thonglor", "Ekkamai", "Phrom Phong",
]

# ชื่อหมู่บ้าน/โครงการ (ไทย)
VILLAGE_NAMES_TH = [
    "ลดาวัลย์", "บุษบา", "เมืองใหม่", "กรีนวิลล์", "ธนาวิลล่า",
    "พฤกษา", "พฤกษาวิลล์", "เดอะพาร์ค", "ชัยพฤกษ์", "สัมมากร",
    "ศุภาลัย", "แลนด์แอนด์เฮ้าส์", "นันทวัน", "เขาทอง", "ทองหล่อ",
    "มัณฑนา", "บางกอกบูเลอวาร์ด", "คาซ่า", "บ้านกลางเมือง",
    "ชลดา", "ประสานสุข", "ศิวารัตน์", "เดอะบลูมส์", "นิรันดร์วิลล์",
    "สุขสมบูรณ์", "ร่มเกล้า", "เขียวขจี", "วนาสิริ", "อรุณรุ่ง",
    "สราญรมย์", "เพ็ญนภา", "วังทอง", "ไพรวัลย์", "สิรินทร์",
    "ปัญจทรัพย์", "ธารา", "แสงทอง", "ริเวอร์ไซด์", "เดอะแกรนด์",
    "พาร์ควิว", "กรีนเลค", "บลูสกาย", "โกลเด้นเกต", "ซิลเวอร์วิลล์",
]

# ชื่ออาคาร/ตึก (ไทย — ใช้ต่างจาก village prefix)
BUILDING_NAMES_TH = [
    "จตุรัส", "สยามทาวเวอร์", "เพลินจิต", "เซ็นทรัล", "เมโทรโพลิส",
    "แกรนด์ไดมอนด์", "อมรินทร์", "บางกอกซิตี้", "สุขุมวิทพาร์ค",
    "เอ็มไพร์", "แพลทินัม", "ไดมอนด์", "เพชร", "ทองคำ",
    "รีเจนท์", "อัมบาสซาเดอร์", "อินเตอร์คอนติเนนตัล", "โนโวเทล",
    "เมอร์เคียว", "แอสตัน", "ริซซ่า", "เอสซี",
]

BUILDING_NAMES_EN = [
    "Green Park", "The City", "Lake View", "Golden Gate", "Silver Creek",
    "Orchid Garden", "Palm Spring", "Blue Diamond", "Sun Valley", "Mountain View",
    "Sky Tower", "Crystal", "Emerald", "Sapphire", "Grand Residence",
    "The Loft", "Riverside", "Parkview", "Metro", "Urbana",
    "The Address", "Noble", "Rhythm", "Life", "Ideo",
]

VILLAGE_PREFIXES_TH = ["หมู่บ้าน", "โครงการ", "คอนโดมิเนียม", "อาคาร", "ตึก"]
VILLAGE_PREFIXES_EN = ["Village", "Project", "Building", "Tower", "Condominium"]

# ตัวอักษร/หมายเลขอาคารย่อย
BUILDING_LETTERS = ["A", "B", "C", "D", "E", "1", "2", "3", "4", "5"]
TOWER_LABELS_TH  = ["ทาวเวอร์ A", "ทาวเวอร์ B", "ทาวเวอร์ C",
                     "ตึก A", "ตึก B", "ตึก C", "ตึก 1", "ตึก 2", "ตึก 3"]
TOWER_LABELS_EN  = ["Tower A", "Tower B", "Tower C",
                     "Wing A", "Wing B", "Block 1", "Block 2"]


# =============================================================================
#  Helper: สุ่มบ้านเลขที่ / ห้อง / ชั้น
# =============================================================================

def random_house_number(rng: random.Random) -> str:
    style = rng.randint(0, 6)
    n = rng.randint(1, 999)
    if style == 0:
        return str(n)
    elif style == 1:
        return f"{n}/{rng.randint(1, 20)}"
    elif style == 2:
        return f"{n}-{rng.randint(1, 5)}"
    elif style == 3:
        suffix = rng.choice(["ก", "ข", "ค", "ง", "A", "B"])
        return f"{n}{suffix}"
    elif style == 4:
        return f"{n}/{rng.randint(1, 99)}-{rng.randint(1, 5)}"
    elif style == 5:
        return f"เลขที่ {n}"
    else:
        return f"บ้านเลขที่ {n}"


def random_room_th(rng: random.Random) -> str:
    """สุ่มเลขห้องพร้อม label ภาษาไทย"""
    floor = rng.randint(1, 50)
    unit  = rng.randint(1, 24)
    num   = f"{floor}{unit:02d}"
    style = rng.randint(0, 4)
    if style == 0:
        return f"ห้อง {num}"
    elif style == 1:
        return f"ห้องเลขที่ {num}"
    elif style == 2:
        return f"เลขที่ห้อง {num}"
    elif style == 3:
        return f"ห้องที่ {num}"
    else:
        return f"ชั้น {floor} ห้อง {unit:02d}"


def random_room_en(rng: random.Random) -> str:
    """สุ่มเลขห้องพร้อม label ภาษาอังกฤษ"""
    floor = rng.randint(1, 50)
    unit  = rng.randint(1, 24)
    num   = f"{floor}{unit:02d}"
    style = rng.randint(0, 3)
    if style == 0:
        return f"Room {num}"
    elif style == 1:
        return f"Room No. {num}"
    elif style == 2:
        return f"Unit {num}"
    else:
        return f"Apt. {num}"


def bkk_or_standard(row: Dict, sub_label: str = "ต.", dist_label: str = "อ.") -> List[str]:
    """คืน [sub_district, district] label ให้เหมาะกับจังหวัด"""
    if row['province_th'] == 'กรุงเทพมหานคร':
        return [f"แขวง{row['sub_district_th']}", f"เขต{row['district_th']}"]
    return [f"{sub_label}{row['sub_district_th']}", f"{dist_label}{row['district_th']}"]


def bkk_province(rng: random.Random, row: Dict) -> str:
    if row['province_th'] == 'กรุงเทพมหานคร':
        return rng.choice(["กรุงเทพมหานคร", "กรุงเทพฯ", "กทม.", "กทม"])
    return row['province_th']


# =============================================================================
#  Templates เดิม
# =============================================================================

def fmt_thai_full(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยเต็มรูปแบบ — label ย่อ"""
    parts = [random_house_number(rng)]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 15)}")
    if rng.random() < 0.35:
        parts.append(f"ซ.{rng.choice(SOI_NAMES_TH)}")
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += [
        f"ต.{row['sub_district_th']}",
        f"อ.{row['district_th']}",
        f"จ.{row['province_th']}",
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_full_long(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยเต็มรูปแบบ — label ยาว"""
    parts = [random_house_number(rng)]
    if rng.random() < 0.4:
        parts.append(f"หมู่ที่ {rng.randint(1, 15)}")
    if rng.random() < 0.35:
        parts.append(f"ซอย{rng.choice(SOI_NAMES_TH)}")
    if rng.random() < 0.5:
        parts.append(f"ถนน{rng.choice(THAI_ROADS)}")
    parts += [
        f"ตำบล{row['sub_district_th']}",
        f"อำเภอ{row['district_th']}",
        f"จังหวัด{row['province_th']}",
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_bangkok(rng: random.Random, row: Dict) -> str:
    """ที่อยู่กรุงเทพ — แขวง/เขต (BKK only)"""
    parts = [random_house_number(rng)]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ซ.{rng.choice(SOI_NAMES_TH)}")
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += [
        f"แขวง{row['sub_district_th']}",
        f"เขต{row['district_th']}",
        rng.choice(["กรุงเทพมหานคร", "กรุงเทพฯ", "กทม.", "กทม"]),
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_unlabelled(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทย — ไม่มี label"""
    parts = [random_house_number(rng)]
    if rng.random() < 0.3:
        parts.append(str(rng.randint(1, 15)))
    parts += [
        row['sub_district_th'],
        row['district_th'],
        row['province_th'],
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_with_village(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทย + หมู่บ้าน/โครงการ"""
    prefix = rng.choice(VILLAGE_PREFIXES_TH)
    name   = rng.choice(VILLAGE_NAMES_TH)
    parts  = [random_house_number(rng), f"{prefix}{name}"]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_thai_room(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทย + อาคาร + ห้องเลขที่"""
    building = f"อาคาร{rng.choice(BUILDING_NAMES_TH)}"
    parts = [random_house_number(rng), building, random_room_th(rng)]
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_english_full(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ภาษาอังกฤษเต็มรูปแบบ"""
    parts = [f"No. {rng.randint(1, 999)}"]
    if rng.random() < 0.4:
        parts.append(f"Moo {rng.randint(1, 15)}")
    if rng.random() < 0.35:
        parts.append(f"Soi {rng.choice(SOI_NAMES_EN)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    parts += [
        f"Tambon {row['sub_district_en']}",
        f"Amphoe {row['district_en']}",
        f"Province {row['province_en']}",
        row['postal_code'],
        "Thailand",
    ]
    return " ".join(parts)


def fmt_english_bangkok(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ภาษาอังกฤษ กรุงเทพ (BKK only)"""
    parts = [f"No. {rng.randint(1, 999)}"]
    if rng.random() < 0.35:
        parts.append(f"Soi {rng.choice(SOI_NAMES_EN)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    parts += [
        f"Khwaeng {row['sub_district_en']}",
        f"Khet {row['district_en']}",
        "Bangkok",
        row['postal_code'],
        "Thailand",
    ]
    return " ".join(parts)


def fmt_english_with_village(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ภาษาอังกฤษ + building/village"""
    prefix = rng.choice(VILLAGE_PREFIXES_EN)
    name   = rng.choice(BUILDING_NAMES_EN)
    parts  = [f"No. {rng.randint(1, 999)}", f"{prefix} {name}"]
    if rng.random() < 0.4:
        parts.append(f"Moo {rng.randint(1, 10)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    parts += [
        f"Tambon {row['sub_district_en']}",
        f"Amphoe {row['district_en']}",
        row['province_en'],
        row['postal_code'],
        "Thailand",
    ]
    return " ".join(parts)


def fmt_postal_only(rng: random.Random, row: Dict) -> str:
    return f"{row['postal_code']} {row['province_th']}"


def fmt_minimal_thai(rng: random.Random, row: Dict) -> str:
    return f"{random_house_number(rng)} {row['province_th']} {row['postal_code']}"


def fmt_mixed_thai_english(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ผสมไทย-อังกฤษ"""
    parts = [f"No. {rng.randint(1, 999)}"]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"Soi {rng.choice(SOI_NAMES_EN)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


# =============================================================================
#  Templates ใหม่ — ผสม ห้องเลขที่ + หมู่บ้าน + อาคาร
# =============================================================================

def fmt_thai_village_room(rng: random.Random, row: Dict) -> str:
    """หมู่บ้าน + อาคาร (ตัวอักษร) + ห้องเลขที่"""
    village = f"หมู่บ้าน{rng.choice(VILLAGE_NAMES_TH)}"
    building = f"อาคาร {rng.choice(BUILDING_LETTERS)}"
    parts = [
        random_house_number(rng),
        village,
        building,
        random_room_th(rng),
    ]
    if rng.random() < 0.35:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_thai_project_tower_room(rng: random.Random, row: Dict) -> str:
    """โครงการ + ทาวเวอร์/ตึก + ห้องเลขที่"""
    project = f"โครงการ{rng.choice(VILLAGE_NAMES_TH)}"
    tower   = rng.choice(TOWER_LABELS_TH)
    parts   = [
        random_house_number(rng),
        project,
        tower,
        random_room_th(rng),
    ]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_thai_condo_floor_room(rng: random.Random, row: Dict) -> str:
    """คอนโดมิเนียม + ชั้น + ห้อง (รูปแบบสมบูรณ์)"""
    condo = f"คอนโดมิเนียม{rng.choice(BUILDING_NAMES_TH)}"
    floor = rng.randint(1, 50)
    unit  = rng.randint(1, 24)
    # ห้องในรูปแบบต่าง ๆ
    room_str = rng.choice([
        f"ชั้น {floor} ห้อง {unit:02d}",
        f"ห้องเลขที่ {floor}{unit:02d}",
        f"ห้อง {floor}{unit:02d}",
        f"เลขที่ห้อง {floor}{unit:02d}",
    ])
    parts = [random_house_number(rng), condo, room_str]
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_thai_bkk_condo_room(rng: random.Random, row: Dict) -> str:
    """กรุงเทพ: คอนโด + ห้อง + แขวง/เขต (BKK only)"""
    condo = f"คอนโด{rng.choice(BUILDING_NAMES_TH)}"
    parts = [
        random_house_number(rng),
        condo,
        random_room_th(rng),
    ]
    if rng.random() < 0.5:
        parts.append(f"ซ.{rng.choice(SOI_NAMES_TH)}")
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += [
        f"แขวง{row['sub_district_th']}",
        f"เขต{row['district_th']}",
        rng.choice(["กรุงเทพมหานคร", "กรุงเทพฯ", "กทม."]),
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_village_building_no_room(rng: random.Random, row: Dict) -> str:
    """หมู่บ้าน + อาคาร (ไม่มีห้อง — บ้านแถว/ทาวน์เฮ้าส์)"""
    village_prefix = rng.choice(["หมู่บ้าน", "โครงการ"])
    village = f"{village_prefix}{rng.choice(VILLAGE_NAMES_TH)}"
    building = f"อาคาร {rng.choice(BUILDING_LETTERS)}"
    parts = [random_house_number(rng), village, building]
    if rng.random() < 0.3:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row, "ต.", "อ.")
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_english_building_room(rng: random.Random, row: Dict) -> str:
    """อังกฤษ: Building + Tower/Wing + Room"""
    building = rng.choice(BUILDING_NAMES_EN)
    tower    = rng.choice(TOWER_LABELS_EN)
    parts    = [
        f"No. {rng.randint(1, 999)}",
        f"Building {building}",
        tower,
        random_room_en(rng),
    ]
    if rng.random() < 0.4:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    if row['province_th'] == 'กรุงเทพมหานคร':
        parts += [
            f"Khwaeng {row['sub_district_en']}",
            f"Khet {row['district_en']}",
            "Bangkok",
        ]
    else:
        parts += [
            f"Tambon {row['sub_district_en']}",
            f"Amphoe {row['district_en']}",
            row['province_en'],
        ]
    parts += [row['postal_code'], "Thailand"]
    return " ".join(parts)


def fmt_english_village_unit(rng: random.Random, row: Dict) -> str:
    """อังกฤษ: Village/Project + Unit/Apt"""
    village = rng.choice(BUILDING_NAMES_EN)
    prefix  = rng.choice(["Village", "Project", "Condominium"])
    parts   = [
        f"No. {rng.randint(1, 999)}",
        f"{prefix} {village}",
        random_room_en(rng),
    ]
    if rng.random() < 0.35:
        parts.append(f"Moo {rng.randint(1, 10)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    if row['province_th'] == 'กรุงเทพมหานคร':
        parts += [
            f"Khwaeng {row['sub_district_en']}",
            f"Khet {row['district_en']}",
            "Bangkok",
        ]
    else:
        parts += [
            f"Tambon {row['sub_district_en']}",
            f"Amphoe {row['district_en']}",
            row['province_en'],
        ]
    parts += [row['postal_code'], "Thailand"]
    return " ".join(parts)


def fmt_thai_full_room(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยเต็ม + ห้องเลขที่ (ไม่มีชื่ออาคาร)"""
    parts = [random_house_number(rng), random_room_th(rng)]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 15)}")
    if rng.random() < 0.35:
        parts.append(f"ซ.{rng.choice(SOI_NAMES_TH)}")
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row, "ตำบล", "อำเภอ")
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


def fmt_thai_project_room_full_label(rng: random.Random, row: Dict) -> str:
    """โครงการ + ห้องเลขที่ — label ยาวทั้งหมด"""
    project = f"โครงการ{rng.choice(VILLAGE_NAMES_TH)}"
    parts   = [random_house_number(rng), project, random_room_th(rng)]
    if rng.random() < 0.4:
        parts.append(f"หมู่ที่ {rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ถนน{rng.choice(THAI_ROADS)}")
    parts += [
        f"ตำบล{row['sub_district_th']}",
        f"อำเภอ{row['district_th']}",
        f"จังหวัด{row['province_th']}",
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_mixed_village_room(rng: random.Random, row: Dict) -> str:
    """ผสมไทย-อังกฤษ: Village/Project EN + ห้อง TH"""
    village = rng.choice(BUILDING_NAMES_EN)
    prefix  = rng.choice(["Village", "Project", "Condominium"])
    parts   = [
        random_house_number(rng),
        f"{prefix} {village}",
        random_room_th(rng),
    ]
    if rng.random() < 0.4:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += bkk_or_standard(row)
    parts += [bkk_province(rng, row), row['postal_code']]
    return " ".join(parts)


# =============================================================================
#  Template pool พร้อม weight
# =============================================================================

TEMPLATES = [
    # ── เดิม ──────────────────────────────────────────────────
    (fmt_thai_full,                    18),
    (fmt_thai_full_long,               14),
    (fmt_thai_bangkok,                  8),   # BKK only (guard ใน generate_address)
    (fmt_thai_unlabelled,              10),
    (fmt_thai_with_village,            10),
    (fmt_thai_room,                     6),
    (fmt_english_full,                  7),
    (fmt_english_bangkok,               4),   # BKK only
    (fmt_english_with_village,          4),
    (fmt_mixed_thai_english,            3),
    (fmt_postal_only,                   1),
    (fmt_minimal_thai,                  1),
    # ── ใหม่: ผสม ห้องเลขที่ + หมู่บ้าน + อาคาร ───────────────
    (fmt_thai_village_room,             8),   # หมู่บ้าน + อาคาร A + ห้อง
    (fmt_thai_project_tower_room,       8),   # โครงการ + ทาวเวอร์ + ห้อง
    (fmt_thai_condo_floor_room,         7),   # คอนโด + ชั้น + ห้อง
    (fmt_thai_bkk_condo_room,           5),   # BKK only: คอนโด + ห้อง
    (fmt_thai_village_building_no_room, 6),   # หมู่บ้าน + อาคาร (ไม่มีห้อง)
    (fmt_english_building_room,         5),   # EN: Building + Tower + Room
    (fmt_english_village_unit,          5),   # EN: Village + Unit/Apt
    (fmt_thai_full_room,                5),   # ไทยเต็ม + ห้อง (ไม่มีอาคาร)
    (fmt_thai_project_room_full_label,  5),   # โครงการ + ห้อง label ยาว
    (fmt_mixed_village_room,            4),   # ผสม EN village + TH ห้อง
]

_template_pool: List = []
for fn, weight in TEMPLATES:
    _template_pool.extend([fn] * weight)

# BKK-only templates ที่ห้ามใช้กับพื้นที่อื่น
_BKK_ONLY = {fmt_thai_bangkok, fmt_english_bangkok, fmt_thai_bkk_condo_room}
# Templates ทั่วไปที่จะสลับเป็น BKK variant สำหรับกรุงเทพ
_BKK_SWAP = {fmt_thai_full: fmt_thai_bangkok, fmt_english_full: fmt_english_bangkok}


def generate_address(rng: random.Random, row: Dict) -> str:
    is_bkk   = row['province_th'] == 'กรุงเทพมหานคร'
    template = rng.choice(_template_pool)

    # template เฉพาะ BKK → ถ้าไม่ใช่กรุงเทพ สลับเป็น template ทั่วไป
    if template in _BKK_ONLY and not is_bkk:
        template = rng.choice([fmt_thai_full, fmt_thai_full_long,
                                fmt_thai_unlabelled, fmt_english_full])

    # กรุงเทพ → สลับ template ทั่วไปเป็น BKK variant
    if is_bkk and template in _BKK_SWAP:
        template = _BKK_SWAP[template]

    return template(rng, row)


# =============================================================================
#  Progress Bar
# =============================================================================

def progress_bar(current: int, total: int, elapsed: float, bar_width: int = 40) -> str:
    pct     = current / total
    done    = int(pct * bar_width)
    bar     = "█" * done + "░" * (bar_width - done)
    rate    = current / elapsed if elapsed > 0 else 0
    eta     = (total - current) / rate if rate > 0 else 0
    eta_str = f"{int(eta//60):02d}:{int(eta%60):02d}"
    return (
        f"\r[{bar}] {current:>9,}/{total:,} "
        f"({pct*100:5.1f}%) "
        f"{rate:6.0f}/s  ETA {eta_str}"
    )


# =============================================================================
#  Bulk save — single transaction, verified ถ้า 4/4 key fields
# =============================================================================

_KEY_FIELDS = ("house_number", "sub_district", "district", "province")


def bulk_save_examples(kb: KnowledgeBase, pairs: List[Tuple[str, dict]]):
    """
    Bulk-insert parsed examples ใน transaction เดียว
    - pairs = [(raw_str, parsed_dict), ...]
    - ที่อยู่ที่ parser แยกได้ครบ 4 key fields → verified = 1
      (house_number, sub_district, district, province)
    """
    now    = datetime.now().isoformat()
    values = []
    for raw, parsed in pairs:
        verified = int(all(parsed.get(f) for f in _KEY_FIELDS))
        values.append((
            raw,
            hashlib.md5(raw.encode("utf-8")).hexdigest(),
            json.dumps(parsed, ensure_ascii=False),
            verified,
            "seed",
            now,
            now,
        ))
    kb.conn.executemany("""
        INSERT INTO address_examples
            (raw_address, address_hash, parsed_json, verified, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(raw_address) DO NOTHING
    """, values)
    kb.conn.commit()


# =============================================================================
#  Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="เพิ่มตัวอย่างที่อยู่สุ่มลง Knowledge Base"
    )
    parser.add_argument(
        "--count", type=int, default=1_000_000,
        help="จำนวนที่อยู่ที่จะสร้าง (default: 1,000,000)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=2000,
        help="ขนาด batch (default: 2000)",
    )
    parser.add_argument(
        "--db", type=str,
        default=str(ROOT / "data" / "address_knowledge.db"),
        help="path ของ knowledge base DB",
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED,
        help="random seed (default: 42)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="แสดงตัวอย่างโดยไม่บันทึก",
    )
    parser.add_argument(
        "--n", type=int, default=30,
        help="จำนวนตัวอย่างใน dry-run (default: 30)",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # โหลด admin areas
    csv_path = ROOT / "data" / "thai_administrative_areas.csv"
    print(f"📂 โหลดข้อมูลจาก {csv_path.name} ...", flush=True)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))
    print(f"   พบ {len(all_rows):,} ตำบล/แขวง", flush=True)

    # Dry-run
    if args.dry_run:
        print(f"\n── ตัวอย่างที่อยู่สุ่ม (dry-run, ไม่บันทึก, n={args.n}) ──")
        for i in range(args.n):
            row  = rng.choice(all_rows)
            addr = generate_address(rng, row)
            print(f"  {i+1:3d}. {addr}")
        return

    # เปิด KB
    print(f"🗄  เปิด Knowledge Base: {args.db}", flush=True)
    kb     = KnowledgeBase(args.db)
    ap     = AddressParser(kb)
    before = kb.get_stats()
    print(f"   ตัวอย่างปัจจุบัน  : {before['total_examples']:>10,} รายการ", flush=True)
    print(f"   verified ปัจจุบัน : {before['verified_examples']:>10,} รายการ", flush=True)

    # ตั้งค่า SQLite เพื่อความเร็ว
    kb.conn.execute("PRAGMA journal_mode=WAL")
    kb.conn.execute("PRAGMA synchronous=NORMAL")
    kb.conn.execute("PRAGMA cache_size=-64000")   # 64 MB page cache

    TARGET = args.count
    BATCH  = args.batch_size
    print(f"\n🚀 เริ่มสร้าง {TARGET:,} ที่อยู่ (batch={BATCH:,}) ...\n", flush=True)

    total_parsed  = 0
    total_verified = 0
    t_start        = time.time()
    batch_addrs    = []

    for i in range(TARGET):
        row  = rng.choice(all_rows)
        addr = generate_address(rng, row)
        batch_addrs.append(addr)

        if len(batch_addrs) >= BATCH or i == TARGET - 1:
            results = ap.parse_batch(batch_addrs, remember=False)
            pairs   = [(raw, res.to_dict())
                       for raw, res in zip(batch_addrs, results)]

            # นับ verified ใน batch นี้ก่อน insert
            batch_verified = sum(
                1 for _, d in pairs if all(d.get(f) for f in _KEY_FIELDS)
            )
            bulk_save_examples(kb, pairs)

            total_parsed   += len(batch_addrs)
            total_verified += batch_verified
            batch_addrs     = []

            elapsed = time.time() - t_start
            print(progress_bar(total_parsed, TARGET, elapsed), end="", flush=True)

    elapsed_total = time.time() - t_start
    print()

    after        = kb.get_stats()
    new_total    = after['total_examples'] - before['total_examples']
    new_verified = after['verified_examples'] - before['verified_examples']

    print(f"\n{'='*65}")
    print(f"✅ เสร็จสิ้น! ใช้เวลา {elapsed_total:.1f} วินาที  "
          f"({elapsed_total/60:.1f} นาที)")
    print(f"   ความเร็วเฉลี่ย    : {total_parsed / elapsed_total:>10,.0f} ที่อยู่/วินาที")
    print(f"   ที่อยู่ที่ generate : {total_parsed:>10,} รายการ")
    print(f"   ใหม่ใน KB         : {new_total:>10,} รายการ  "
          f"(ซ้ำ skip: {total_parsed - new_total:,})")
    print(f"   verified ใหม่     : {new_verified:>10,} รายการ  "
          f"({new_verified/max(new_total,1)*100:.1f}%)")
    print(f"   รวมทั้งหมด        : {after['total_examples']:>10,} รายการ")
    print(f"   verified รวม      : {after['verified_examples']:>10,} รายการ")
    print(f"{'='*65}")

    kb.close()


if __name__ == "__main__":
    main()
