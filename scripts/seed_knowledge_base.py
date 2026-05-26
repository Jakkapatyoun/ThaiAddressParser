#!/usr/bin/env python3
"""
seed_knowledge_base.py — เพิ่มตัวอย่างที่อยู่สุ่ม 100,000 รายการลง Knowledge Base

วิธีรัน:
    python scripts/seed_knowledge_base.py              # ครบ 100,000 รายการ
    python scripts/seed_knowledge_base.py --count 5000 # ระบุจำนวนเอง
    python scripts/seed_knowledge_base.py --dry-run    # ดูตัวอย่างโดยไม่บันทึก

ที่อยู่จะถูกสร้างโดยการผสมผสาน:
  - บ้านเลขที่รูปแบบต่าง ๆ (123, 45/6, 789-1, 10ก, ...)
  - 7,436 ตำบล/แขวงจากข้อมูลมาตรฐาน
  - ชื่อถนน ซอย หมู่บ้าน แบบสุ่ม
  - รูปแบบที่อยู่ที่หลากหลาย (มี label / ไม่มี, ไทย / อังกฤษ, ย่อ / เต็ม)
"""

import sys
import os
import csv
import random
import time
import argparse
from pathlib import Path
from typing import List, Dict

# ── Project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from address_parser import KnowledgeBase, AddressParser

# ── Seed สำหรับ reproducibility (เปลี่ยนได้) ──────────────────────────────────
RANDOM_SEED = 42

# =============================================================================
#  ชุดข้อมูลสำหรับสุ่มสร้างที่อยู่
# =============================================================================

# ชื่อถนนทั่วไปในไทย
THAI_ROADS = [
    "สุขุมวิท", "พระราม 2", "พระราม 4", "พระราม 9", "รัชดาภิเษก",
    "ลาดพร้าว", "เพชรบุรี", "สีลม", "สาทร", "พหลโยธิน",
    "วิภาวดีรังสิต", "งามวงศ์วาน", "แจ้งวัฒนะ", "บางนา-ตราด",
    "ประชาชื่น", "รามคำแหง", "อโศก", "ทองหล่อ", "เอกมัย",
    "ประชาอุทิศ", "สุทธิสาร", "เจริญกรุง", "เยาวราช", "วรจักร",
    "ดินแดง", "บรมราชชนนี", "ปิ่นเกล้า", "จรัญสนิทวงศ์",
    "นวมินทร์", "มิตรภาพ", "อุดรดุษฎี", "ท่าแพ", "นิมมานเหมินท์",
    "ห้วยแก้ว", "โชตนา", "สนามบินน้ำ", "บางพลัด", "ราษฎร์บูรณะ",
]

ENGLISH_ROADS = [
    "Sukhumvit", "Silom", "Sathorn", "Ratchadaphisek", "Phahon Yothin",
    "Ladprao", "Vibhavadi Rangsit", "Bangna-Trat", "Charoenkrung",
    "Yaowarat", "Phra Ram 4", "Wireless", "Ploenchit",
]

# ชื่อซอยสุ่ม
SOI_NAMES_TH = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11", "13", "15", "17", "19", "21", "23", "25",
    "สุขใจ", "ร่วมพัฒนา", "สามัคคี", "เจริญสุข", "ประชาสงเคราะห์",
    "สวนหลวง", "มิตรภาพ", "นิรันดร์", "สุขสวัสดิ์", "ศรีนครินทร์",
]

SOI_NAMES_EN = [
    "1", "3", "5", "7", "9", "11", "13", "15", "17", "19", "21",
    "Ruamrudee", "Nana", "Asok", "Thonglor", "Ekkamai",
]

# ชื่อหมู่บ้าน/โครงการสุ่ม
VILLAGE_NAMES_TH = [
    "ลดาวัลย์", "บุษบา", "เมืองใหม่", "กรีนวิลล์", "ธนาวิลล่า",
    "พฤกษา", "พฤกษาวิลล์", "เดอะพาร์ค", "ชัยพฤกษ์", "สัมมากร",
    "ศุภาลัย", "แลนด์แอนด์เฮ้าส์", "นันทวัน", "เขาทอง", "ทองหล่อ",
    "มัณฑนา", "บางกอกบูเลอวาร์ด", "คาซ่า", "บ้านกลางเมือง",
    "ชลดา", "ประสานสุข", "ศิวารัตน์", "เดอะบลูมส์", "นิรันดร์วิลล์",
    "สุขสมบูรณ์", "ร่มเกล้า", "เขียวขจี", "วนาสิริ", "อรุณรุ่ง",
]

VILLAGE_PREFIXES_TH  = ["หมู่บ้าน", "โครงการ", "คอนโดมิเนียม", "อาคาร", "ตึก"]
VILLAGE_PREFIXES_EN  = ["Village", "Project", "Building", "Tower", "Condominium"]

VILLAGE_NAMES_EN = [
    "Green Park", "The City", "Lake View", "Golden Gate", "Silver Creek",
    "Orchid Garden", "Palm Spring", "Blue Diamond", "Sun Valley", "Mountain View",
]

# รูปแบบบ้านเลขที่
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


# =============================================================================
#  Template สำหรับสร้างที่อยู่
# =============================================================================

def fmt_thai_full(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยเต็มรูปแบบ — ทุก field มี label"""
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
    """ที่อยู่ไทยเต็มรูปแบบ — label แบบยาว"""
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
    """ที่อยู่กรุงเทพ — ใช้ แขวง/เขต"""
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
    ]
    # สลับระหว่างรูปแบบจังหวัดกรุงเทพ
    bkk_province = rng.choice(["กรุงเทพมหานคร", "กรุงเทพฯ", "กทม.", "กทม"])
    parts += [bkk_province, row['postal_code']]
    return " ".join(parts)


def fmt_thai_unlabelled(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทย — ไม่มี label (ใช้ลำดับแทน)"""
    parts = [random_house_number(rng)]
    if rng.random() < 0.3:
        parts.append(str(rng.randint(1, 15)))  # หมู่ที่ (ไม่มี label)
    parts += [
        row['sub_district_th'],
        row['district_th'],
        row['province_th'],
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_with_village(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยพร้อมชื่อหมู่บ้าน/โครงการ"""
    prefix = rng.choice(VILLAGE_PREFIXES_TH)
    village_name = rng.choice(VILLAGE_NAMES_TH)
    parts = [
        random_house_number(rng),
        f"{prefix}{village_name}",
    ]
    if rng.random() < 0.4:
        parts.append(f"ม.{rng.randint(1, 10)}")
    if rng.random() < 0.4:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    parts += [
        f"ต.{row['sub_district_th']}",
        f"อ.{row['district_th']}",
        f"จ.{row['province_th']}",
        row['postal_code'],
    ]
    return " ".join(parts)


def fmt_thai_room(rng: random.Random, row: Dict) -> str:
    """ที่อยู่ไทยพร้อมเลขห้อง (คอนโด/อาคาร)"""
    building = f"อาคาร{rng.choice(VILLAGE_NAMES_TH)}"
    floor = rng.randint(1, 40)
    room = f"{floor}{rng.randint(1, 20):02d}"
    parts = [
        random_house_number(rng),
        building,
        f"ห้อง {room}",
    ]
    if rng.random() < 0.5:
        parts.append(f"ถ.{rng.choice(THAI_ROADS)}")
    # ใช้ แขวง/เขต เฉพาะกรุงเทพ — พื้นที่อื่นใช้ ต./อ.
    if row['province_th'] == 'กรุงเทพมหานคร':
        parts += [
            f"แขวง{row['sub_district_th']}",
            f"เขต{row['district_th']}",
        ]
    else:
        parts += [
            f"ต.{row['sub_district_th']}",
            f"อ.{row['district_th']}",
        ]
    parts += [row['province_th'], row['postal_code']]
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
    """ที่อยู่ภาษาอังกฤษสำหรับกรุงเทพ"""
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
    """ที่อยู่ภาษาอังกฤษพร้อม building/village"""
    prefix = rng.choice(VILLAGE_PREFIXES_EN)
    name   = rng.choice(VILLAGE_NAMES_EN)
    parts  = [
        f"No. {rng.randint(1, 999)}",
        f"{prefix} {name}",
    ]
    if rng.random() < 0.4:
        parts.append(f"Moo {rng.randint(1, 10)}")
    if rng.random() < 0.5:
        parts.append(f"{rng.choice(ENGLISH_ROADS)} Road")
    parts += [
        f"Tambon {row['sub_district_en']}",
        f"Amphoe {row['district_en']}",
        f"{row['province_en']}",
        row['postal_code'],
        "Thailand",
    ]
    return " ".join(parts)


def fmt_postal_only(rng: random.Random, row: Dict) -> str:
    """รหัสไปรษณีย์อย่างเดียว + จังหวัด"""
    return f"{row['postal_code']} {row['province_th']}"


def fmt_minimal_thai(rng: random.Random, row: Dict) -> str:
    """ที่อยู่สั้น — บ้านเลขที่ + จังหวัด + รหัสไปรษณีย์"""
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
    parts += [
        f"ต.{row['sub_district_th']}",
        f"อ.{row['district_th']}",
        row['province_th'],
        row['postal_code'],
    ]
    return " ".join(parts)


# Pool ของ template functions พร้อม weight
TEMPLATES = [
    (fmt_thai_full,           20),   # ที่อยู่ไทยเต็ม (ย่อ)
    (fmt_thai_full_long,      15),   # ที่อยู่ไทยเต็ม (ยาว)
    (fmt_thai_bangkok,        10),   # กรุงเทพ แขวง/เขต
    (fmt_thai_unlabelled,     12),   # ไม่มี label
    (fmt_thai_with_village,   12),   # มีชื่อหมู่บ้าน
    (fmt_thai_room,            8),   # มีเลขห้อง
    (fmt_english_full,         8),   # อังกฤษเต็ม
    (fmt_english_bangkok,      5),   # อังกฤษกรุงเทพ
    (fmt_english_with_village, 5),   # อังกฤษ + building
    (fmt_mixed_thai_english,   3),   # ผสม
    (fmt_postal_only,          1),   # รหัส + จังหวัด
    (fmt_minimal_thai,         1),   # minimal
]

# สร้าง weighted list
_template_pool: List = []
for fn, weight in TEMPLATES:
    _template_pool.extend([fn] * weight)


def generate_address(rng: random.Random, row: Dict) -> str:
    """สุ่มสร้างที่อยู่จาก row ของตาราง administrative_areas"""
    is_bkk = row['province_th'] == 'กรุงเทพมหานคร'

    template = rng.choice(_template_pool)

    # template แขวง/เขต ใช้ได้เฉพาะกรุงเทพ — ถ้าสุ่มได้แล้วไม่ใช่ BKK ให้สลับ
    if template in (fmt_thai_bangkok, fmt_english_bangkok) and not is_bkk:
        template = rng.choice([fmt_thai_full, fmt_thai_full_long,
                                fmt_thai_unlabelled, fmt_english_full])

    # กรุงเทพฯ — template ทั่วไปสลับเป็น Bangkok variant
    if is_bkk:
        if template == fmt_thai_full:
            template = fmt_thai_bangkok
        elif template == fmt_english_full:
            template = fmt_english_bangkok

    return template(rng, row)


# =============================================================================
#  Progress Bar แบบ lightweight
# =============================================================================

def progress_bar(current: int, total: int, elapsed: float, bar_width: int = 40) -> str:
    pct  = current / total
    done = int(pct * bar_width)
    bar  = "█" * done + "░" * (bar_width - done)
    rate = current / elapsed if elapsed > 0 else 0
    eta  = (total - current) / rate if rate > 0 else 0
    eta_str = f"{int(eta//60):02d}:{int(eta%60):02d}"
    return (
        f"\r[{bar}] {current:>7,}/{total:,} "
        f"({pct*100:5.1f}%) "
        f"{rate:6.0f}/s  ETA {eta_str}"
    )


# =============================================================================
#  Main
# =============================================================================

def bulk_save_examples(kb: KnowledgeBase, pairs: List[tuple]):
    """
    Bulk-insert parsed examples ใน transaction เดียว — เร็วกว่า N × save_example()
    pairs = list of (raw_str, parsed_dict)
    """
    import hashlib, json
    from datetime import datetime

    now = datetime.now().isoformat()
    values = [
        (
            raw,
            hashlib.md5(raw.encode("utf-8")).hexdigest(),
            json.dumps(parsed, ensure_ascii=False),
            0,          # verified = False (auto-parsed)
            "seed",
            now,
            now,
        )
        for raw, parsed in pairs
    ]
    kb.conn.executemany("""
        INSERT INTO address_examples
            (raw_address, address_hash, parsed_json, verified, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(raw_address) DO NOTHING
    """, values)
    kb.conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="เพิ่มตัวอย่างที่อยู่สุ่มลง Knowledge Base"
    )
    parser.add_argument(
        "--count", type=int, default=100_000,
        help="จำนวนที่อยู่ที่จะสร้าง (default: 100000)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=2000,
        help="ขนาด batch สำหรับ parse+insert (default: 2000)",
    )
    parser.add_argument(
        "--db", type=str, default=str(ROOT / "data" / "address_knowledge.db"),
        help="path ของ knowledge base DB",
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED,
        help="random seed (default: 42)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="แสดงตัวอย่างที่อยู่ 20 รายการโดยไม่บันทึก",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # ── โหลด admin areas จาก CSV ────────────────────────────────────────────
    csv_path = ROOT / "data" / "thai_administrative_areas.csv"
    print(f"📂 โหลดข้อมูลจาก {csv_path.name} ...", flush=True)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))
    print(f"   พบ {len(all_rows):,} ตำบล/แขวง", flush=True)

    # ── Dry-run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n── ตัวอย่างที่อยู่สุ่ม (dry-run, ไม่บันทึก) ──────────────────")
        for i in range(20):
            row = rng.choice(all_rows)
            addr = generate_address(rng, row)
            print(f"  {i+1:2d}. {addr}")
        return

    # ── เปิด KB ──────────────────────────────────────────────────────────────
    print(f"🗄  เปิด Knowledge Base: {args.db}", flush=True)
    kb     = KnowledgeBase(args.db)
    ap     = AddressParser(kb)
    before = kb.get_stats()
    print(f"   ตัวอย่างปัจจุบัน: {before['total_examples']:,} รายการ", flush=True)

    # ── ตั้งค่า SQLite WAL mode เพื่อเพิ่มความเร็ว write ──────────────────
    kb.conn.execute("PRAGMA journal_mode=WAL")
    kb.conn.execute("PRAGMA synchronous=NORMAL")

    # ── สร้างที่อยู่ทั้งหมด ──────────────────────────────────────────────────
    TARGET = args.count
    BATCH  = args.batch_size
    print(f"\n🚀 เริ่มสร้าง {TARGET:,} ที่อยู่ (batch={BATCH}) ...\n", flush=True)

    total_parsed = 0
    t_start      = time.time()
    batch_addrs  = []

    for i in range(TARGET):
        row  = rng.choice(all_rows)
        addr = generate_address(rng, row)
        batch_addrs.append(addr)

        # parse + insert เมื่อ batch เต็ม หรือถึง address สุดท้าย
        if len(batch_addrs) >= BATCH or i == TARGET - 1:
            # parse โดยไม่ track usage (เร็วกว่า) แล้ว bulk-insert เอง
            results = ap.parse_batch(batch_addrs, remember=False)
            pairs = [
                (raw, result.to_dict())
                for raw, result in zip(batch_addrs, results)
            ]
            bulk_save_examples(kb, pairs)

            total_parsed += len(batch_addrs)
            batch_addrs   = []

            elapsed = time.time() - t_start
            bar = progress_bar(total_parsed, TARGET, elapsed)
            print(bar, end="", flush=True)

    elapsed_total = time.time() - t_start
    print()  # newline after progress bar

    # ── สรุปผล ────────────────────────────────────────────────────────────────
    after = kb.get_stats()
    new_examples = after['total_examples'] - before['total_examples']

    print(f"\n{'='*60}")
    print(f"✅ เสร็จสิ้น! ใช้เวลา {elapsed_total:.1f} วินาที")
    print(f"   ความเร็วเฉลี่ย : {total_parsed / elapsed_total:,.0f} ที่อยู่/วินาที")
    print(f"   ที่อยู่ที่ parse  : {total_parsed:,} รายการ")
    print(f"   ตัวอย่างใหม่ใน KB: {new_examples:,} รายการ  (ซ้ำ skip: {total_parsed - new_examples:,})")
    print(f"   รวมใน KB ทั้งหมด : {after['total_examples']:,} รายการ")
    print(f"   Keyword patterns : {after['keyword_patterns']:,} คำ")
    print(f"{'='*60}")

    kb.close()


if __name__ == "__main__":
    main()
