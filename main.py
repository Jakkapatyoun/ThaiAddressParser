#!/usr/bin/env python3
"""
main.py — Thai Address Parser CLI
ใช้งาน offline ได้ 100% | self-learning knowledge base

การใช้งาน:
  python main.py                   — เมนูหลัก (interactive)
  python main.py parse             — แยกที่อยู่แบบพิมพ์ทีละบรรทัด
  python main.py csv <file.csv>    — แยกที่อยู่จากไฟล์ CSV
  python main.py stats             — ดูสถิติ knowledge base
  python main.py export            — export knowledge base
  python main.py import <file>     — import knowledge base
"""
import sys
import os
import csv
import json
import argparse
from datetime import datetime
from typing import Optional

# ── ensure package is importable ──
sys.path.insert(0, os.path.dirname(__file__))

from address_parser import ParsedAddress, KnowledgeBase, AddressParser

# ─────────────────── สีสำหรับ terminal ───────────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    C_GREEN  = Fore.GREEN
    C_CYAN   = Fore.CYAN
    C_YELLOW = Fore.YELLOW
    C_RED    = Fore.RED
    C_BOLD   = Style.BRIGHT
    C_RESET  = Style.RESET_ALL
except ImportError:
    C_GREEN = C_CYAN = C_YELLOW = C_RED = C_BOLD = C_RESET = ""


# ─────────────────── Helpers ──────────────────────────────

def hr(char: str = "─", width: int = 60) -> str:
    return char * width


def banner():
    print(f"\n{C_BOLD}{C_CYAN}{'═'*60}")
    print("   🏠  Thai Address Parser  v1.0")
    print(f"   Knowledge Base: self-learning | Offline 100%")
    print(f"{'═'*60}{C_RESET}\n")


def print_parsed(addr: ParsedAddress, show_raw: bool = True):
    """แสดงผลการแยกที่อยู่"""
    if show_raw:
        print(f"\n{C_BOLD}📍 ที่อยู่ต้นฉบับ:{C_RESET}")
        print(f"   {addr.raw}")
    print(f"\n{C_GREEN}{hr()}{C_RESET}")
    for eng, thai in ParsedAddress.THAI_COLUMNS.items():
        val = getattr(addr, eng)
        if val:
            print(f"  {C_YELLOW}{thai:<20}{C_RESET}: {val}")
    bar   = "█" * int(addr.confidence * 10) + "░" * (10 - int(addr.confidence * 10))
    color = C_GREEN if addr.confidence >= 0.75 else (C_YELLOW if addr.confidence >= 0.4 else C_RED)
    print(f"  {C_YELLOW}{'ความมั่นใจ':<20}{C_RESET}: {color}[{bar}] {addr.confidence*100:.0f}%{C_RESET}")
    print(f"{C_GREEN}{hr()}{C_RESET}")


def ask_correction(addr: ParsedAddress, parser: AddressParser) -> Optional[ParsedAddress]:
    """
    ถามผู้ใช้ว่าต้องการแก้ไขผลลัพธ์ไหม
    ถ้าแก้ไข จะบันทึกลง knowledge base เพื่อเรียนรู้
    """
    print(f"\n{C_CYAN}ต้องการแก้ไขผลลัพธ์ไหม? (y/n) [{C_RESET}n{C_CYAN}]{C_RESET} ", end="")
    ans = input().strip().lower()
    if ans not in ("y", "yes", "ใช่", "แก้"):
        return None

    print(f"\n{C_BOLD}แก้ไขค่า (Enter = ไม่เปลี่ยน, '-' = ลบค่า):{C_RESET}")
    corrected_data = addr.to_dict()
    corrected_data.pop("confidence", None)

    field_map = {
        "1": ("house_number", "บ้านเลขที่"),
        "2": ("village",      "หมู่บ้าน/โครงการ"),
        "3": ("moo",          "หมู่ที่"),
        "4": ("soi",          "ซอย"),
        "5": ("road",         "ถนน"),
        "6": ("sub_district", "ตำบล/แขวง"),
        "7": ("district",     "อำเภอ/เขต"),
        "8": ("province",     "จังหวัด"),
        "9": ("postal_code",  "รหัสไปรษณีย์"),
        "0": ("country",      "ประเทศ"),
    }

    for num, (field, thai) in field_map.items():
        current = corrected_data.get(field) or ""
        display = f"{C_CYAN}[{current}]{C_RESET}" if current else f"{C_RED}[ว่าง]{C_RESET}"
        print(f"  {num}. {thai:<20} {display}: ", end="")
        new_val = input().strip()
        if new_val == "-":
            corrected_data[field] = None
        elif new_val:
            corrected_data[field] = new_val

    corrected = ParsedAddress.from_dict({**corrected_data, "raw": addr.raw})
    corrected.confidence = 1.0   # user-verified = confidence 100%

    # เรียนรู้จากการแก้ไข
    parser.learn(addr.raw, addr, corrected)
    print(f"\n{C_GREEN}✅ บันทึกการแก้ไขลง Knowledge Base แล้ว — ระบบจะเรียนรู้สำหรับครั้งต่อไป{C_RESET}")
    return corrected


# ─────────────────── Mode: parse (interactive) ────────────

def mode_parse(parser: AddressParser):
    """แยกที่อยู่แบบ interactive ทีละบรรทัด"""
    print(f"\n{C_BOLD}📝 โหมดแยกที่อยู่ (พิมพ์ 'q' เพื่อออก){C_RESET}")
    print(f"   Tips: รองรับทั้งภาษาไทยและอังกฤษ\n")

    while True:
        print(f"{C_CYAN}➤ ที่อยู่:{C_RESET} ", end="")
        raw = input().strip()

        if not raw:
            continue
        if raw.lower() in ("q", "quit", "exit", "ออก"):
            print(f"\n{C_YELLOW}ออกจากโหมดแยกที่อยู่{C_RESET}")
            break

        addr = parser.parse(raw)
        print_parsed(addr)

        corrected = ask_correction(addr, parser)
        if corrected:
            print(f"\n{C_BOLD}📋 ผลลัพธ์หลังแก้ไข:{C_RESET}")
            print_parsed(corrected, show_raw=False)

        print()


# ─────────────────── Mode: CSV ────────────────────────────

def mode_csv(parser: AddressParser, input_path: str):
    """แยกที่อยู่จากไฟล์ CSV"""
    if not os.path.exists(input_path):
        print(f"{C_RED}❌ ไม่พบไฟล์: {input_path}{C_RESET}")
        return

    # ─── อ่าน CSV ───
    rows = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        print(f"{C_RED}❌ ไฟล์ว่างเปล่า{C_RESET}")
        return

    # ─── เลือกคอลัมภ์ที่อยู่ ───
    print(f"\n{C_BOLD}คอลัมภ์ที่มีในไฟล์:{C_RESET}")
    for i, col in enumerate(fieldnames):
        print(f"  {i+1}. {col}")

    print(f"\n{C_CYAN}เลือกหมายเลขคอลัมภ์ที่อยู่เต็ม:{C_RESET} ", end="")
    try:
        col_idx = int(input().strip()) - 1
        addr_col = fieldnames[col_idx]
    except (ValueError, IndexError):
        print(f"{C_RED}❌ เลือกคอลัมภ์ไม่ถูกต้อง{C_RESET}")
        return

    # ─── แยกที่อยู่ ───
    # remember=False: ไม่บันทึกลง KB ทีละแถว (เร็วกว่า ~12×)
    # ถ้าต้องการ train KB ให้ใช้โหมด parse (interactive) แล้วแก้ไขผลลัพธ์แต่ละรายการ
    print(f"\n{C_BOLD}กำลังแยกที่อยู่ {len(rows)} รายการ...{C_RESET}")
    results = []
    for i, row in enumerate(rows, 1):
        raw  = row.get(addr_col, "").strip()
        addr = parser.parse(raw, remember=False) if raw else ParsedAddress(raw="")
        out  = dict(row)     # คงคอลัมภ์เดิมไว้
        out.update(addr.to_output_row())
        results.append(out)
        # progress
        if i % 10 == 0 or i == len(rows):
            pct = i / len(rows) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"\r  [{bar}] {i}/{len(rows)} ({pct:.0f}%)", end="", flush=True)

    print()

    # ─── เลือก output path ───
    base     = os.path.splitext(input_path)[0]
    out_path = f"{base}_parsed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    print(f"\n{C_CYAN}บันทึกไปที่ [{out_path}] (Enter = ใช้ default, พิมพ์ path ใหม่เพื่อเปลี่ยน):{C_RESET} ", end="")
    custom = input().strip()
    if custom:
        out_path = custom

    # ─── เขียน CSV ───
    all_keys = list(results[0].keys()) if results else []
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(results)

    # ─── summary ───
    ok_count = sum(1 for r in results if r.get("จังหวัด") or r.get("ตำบล/แขวง"))
    print(f"\n{C_GREEN}✅ บันทึกแล้ว: {out_path}")
    print(f"   รายการทั้งหมด : {len(results)}")
    print(f"   แยกสำเร็จ    : {ok_count} ({ok_count/len(results)*100:.0f}%){C_RESET}")

    # แสดงตัวอย่าง 3 รายการแรก
    print(f"\n{C_BOLD}ตัวอย่างผลลัพธ์ (3 รายการแรก):{C_RESET}")
    for i, r in enumerate(results[:3], 1):
        print(f"\n  [{i}] {r.get('ที่อยู่เต็ม', '')}")
        for thai in ParsedAddress.THAI_COLUMNS.values():
            val = r.get(thai)
            if val:
                print(f"       {thai:<18}: {val}")


# ─────────────────── Mode: stats ──────────────────────────

def mode_stats(kb: KnowledgeBase):
    """แสดงสถิติ knowledge base"""
    stats = kb.get_stats()
    print(f"\n{C_BOLD}📊 Knowledge Base Statistics{C_RESET}")
    print(f"{hr()}")
    print(f"  ตัวอย่างที่อยู่ทั้งหมด    : {stats['total_examples']:>6,}")
    print(f"  ตัวอย่างที่ verified แล้ว  : {C_GREEN}{stats['verified_examples']:>6,}{C_RESET}")
    print(f"  จำนวนการแก้ไข            : {stats['corrections']:>6,}")
    print(f"  Keyword patterns          : {stats['keyword_patterns']:>6,}")
    print(f"  Custom keywords           : {stats['custom_keywords']:>6,}")
    print(f"  Administrative areas      : {stats['administrative_areas']:>6,}")
    print(f"{hr()}")

    top_kw = kb.get_top_keywords(10)
    if top_kw:
        print(f"\n{C_BOLD}🔑 Keywords ที่ใช้บ่อย:{C_RESET}")
        for kw in top_kw:
            bar = "▪" * min(20, kw["usage_count"])
            print(f"  {kw['keyword']:<20} ({kw['component']:<15}) — ใช้ {kw['usage_count']:,} ครั้ง")


# ─────────────────── Mode: export / import ────────────────

def mode_export(kb: KnowledgeBase):
    path = f"exports/knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("exports", exist_ok=True)
    kb.export_json(path)
    print(f"{C_GREEN}✅ Export แล้ว: {path}{C_RESET}")


def mode_import(kb: KnowledgeBase, path: str):
    if not os.path.exists(path):
        print(f"{C_RED}❌ ไม่พบไฟล์: {path}{C_RESET}")
        return
    result = kb.import_json(path)
    print(f"{C_GREEN}✅ Import สำเร็จ")
    print(f"   ตัวอย่าง: {result['examples']} รายการ")
    print(f"   Keywords: {result['keywords']} คำ{C_RESET}")


# ─────────────────── Mode: master data / benchmark ─────────

def mode_load_master(kb: KnowledgeBase, path: str):
    """นำเข้าทำเนียบตำบล/อำเภอ/จังหวัด/รหัสไปรษณีย์สำหรับ parse แบบ local"""
    if not os.path.exists(path):
        print(f"{C_RED}❌ ไม่พบไฟล์ master data: {path}{C_RESET}")
        print("   สร้างไฟล์ด้วย: python scripts/download_master_data.py")
        return
    count = kb.import_admin_csv(path, source="thailand-geography-data/thailand-geography-json")
    print(f"{C_GREEN}✅ โหลด Administrative Master Data แล้ว: {count:,} ตำบล{C_RESET}")


def mode_benchmark(parser: AddressParser, kb: KnowledgeBase, limit: Optional[int] = None):
    """
    ทดสอบ variants ที่สร้างจาก master data โดยไม่บันทึก synthetic address
    เป็นตัวอย่าง learned เพื่อไม่ให้ผลวัด accuracy ปนกับข้อมูลฝึก
    """
    areas = kb.get_admin_areas(limit=limit)
    if not areas:
        print(f"{C_RED}❌ ยังไม่มี Administrative Master Data กรุณารัน load-master ก่อน{C_RESET}")
        return

    total_addresses = 0
    total_fields = 0
    correct_fields = 0
    perfect = 0
    failures = []

    for idx, area in enumerate(areas, 1):
        house = f"{idx}/1"
        sub = area["sub_district_th"]
        district = area["district_th"]
        province = area["province_th"]
        postal = area["postal_code"]
        if province == "กรุงเทพมหานคร":
            locality_labelled = f"แขวง{sub} เขต{district} {province}"
            locality_short = f"แขวง{sub} เขต{district} กทม"
        else:
            locality_labelled = f"ตำบล{sub} อำเภอ{district} จังหวัด{province}"
            locality_short = f"ต.{sub} อ.{district} {province}"
        addresses = [
            f"{house} ถนนประชาร่วมใจ {locality_labelled} {postal}",
            f"{house} ถ.ประชาร่วมใจ {locality_short} {postal}",
            f"{house} ประชาร่วมใจ {sub} {district} {province} {postal}",
        ]
        expected = {
            "house_number": house,
            "sub_district": sub,
            "district": district,
            "province": province,
            "postal_code": postal,
        }
        for raw in addresses:
            result = parser.parse(raw, remember=False)
            wrong = []
            for field, value in expected.items():
                total_fields += 1
                if getattr(result, field) == value:
                    correct_fields += 1
                else:
                    wrong.append(f"{field}={getattr(result, field)!r} expected {value!r}")
            total_addresses += 1
            if not wrong:
                perfect += 1
            elif len(failures) < 5:
                failures.append((raw, wrong))

    field_accuracy = correct_fields / total_fields * 100
    full_accuracy = perfect / total_addresses * 100
    print(f"\n{C_BOLD}Benchmark จาก Administrative Master Data{C_RESET}")
    print(f"  พื้นที่ต้นทาง       : {len(areas):>8,} ตำบล")
    print(f"  Full address variants: {total_addresses:>8,} รายการ")
    print(f"  Field accuracy       : {field_accuracy:>7.2f}%")
    print(f"  Full-row accuracy    : {full_accuracy:>7.2f}%")
    print("  หมายเหตุ             : variants ชุดนี้ไม่ถูกบันทึกเป็น learned examples")
    if failures:
        print(f"\n{C_YELLOW}ตัวอย่างที่ยังไม่ผ่าน (สูงสุด 5 รายการ):{C_RESET}")
        for raw, wrong in failures:
            print(f"  - {raw}")
            print(f"    {'; '.join(wrong)}")


# ─────────────────── Mode: keyword management ─────────────

def mode_keywords(kb: KnowledgeBase):
    """จัดการ keyword patterns"""
    while True:
        print(f"\n{C_BOLD}🔑 จัดการ Keyword Patterns{C_RESET}")
        print("  1. ดู keywords ทั้งหมด")
        print("  2. เพิ่ม keyword ใหม่")
        print("  3. ลบ keyword (เฉพาะ custom)")
        print("  0. กลับ")
        print(f"\n{C_CYAN}เลือก:{C_RESET} ", end="")
        choice = input().strip()

        if choice == "0":
            break
        elif choice == "1":
            keywords = kb.get_keywords()
            print(f"\n{C_BOLD}Keyword ทั้งหมด ({len(keywords)} คำ):{C_RESET}")
            # group by component
            groups: dict = {}
            for kw, comp in keywords:
                groups.setdefault(comp, []).append(kw)
            for comp, kws in sorted(groups.items()):
                print(f"\n  {C_YELLOW}{comp}:{C_RESET}")
                print("    " + " | ".join(kws))
        elif choice == "2":
            print(f"{C_CYAN}Keyword ใหม่:{C_RESET} ", end="")
            kw = input().strip()
            print(f"{C_CYAN}Component (house_number/village/moo/soi/road/sub_district/district/province/postal_code/country):{C_RESET} ", end="")
            comp = input().strip()
            print(f"{C_CYAN}ภาษา (th/en):{C_RESET} ", end="")
            lang = input().strip() or "th"
            if kw and comp:
                kb.add_keyword(kw, comp, lang)
                print(f"{C_GREEN}✅ เพิ่มแล้ว: '{kw}' → {comp}{C_RESET}")
        elif choice == "3":
            print(f"{C_CYAN}Keyword ที่ต้องการลบ:{C_RESET} ", end="")
            kw = input().strip()
            if kb.remove_keyword(kw):
                print(f"{C_GREEN}✅ ลบแล้ว: '{kw}'{C_RESET}")
            else:
                print(f"{C_RED}❌ ไม่พบหรือไม่สามารถลบได้ (เฉพาะ custom keyword เท่านั้น){C_RESET}")


# ─────────────────── Main Menu ────────────────────────────

def main_menu(parser: AddressParser, kb: KnowledgeBase):
    banner()
    while True:
        print(f"{C_BOLD}เมนูหลัก:{C_RESET}")
        print(f"  {C_GREEN}1{C_RESET}. แยกที่อยู่ (พิมพ์ทีละบรรทัด)")
        print(f"  {C_GREEN}2{C_RESET}. แยกที่อยู่จากไฟล์ CSV")
        print(f"  {C_GREEN}3{C_RESET}. ดูสถิติ Knowledge Base")
        print(f"  {C_GREEN}4{C_RESET}. จัดการ Keyword Patterns")
        print(f"  {C_GREEN}5{C_RESET}. Export Knowledge Base")
        print(f"  {C_GREEN}6{C_RESET}. Import Knowledge Base")
        print(f"  {C_GREEN}7{C_RESET}. Load Administrative Master Data")
        print(f"  {C_GREEN}8{C_RESET}. Run Accuracy Benchmark")
        print(f"  {C_GREEN}0{C_RESET}. ออก")
        print(f"\n{C_CYAN}เลือก:{C_RESET} ", end="")
        choice = input().strip()

        if choice == "0":
            print(f"\n{C_YELLOW}ลาก่อน! 👋{C_RESET}\n")
            break
        elif choice == "1":
            mode_parse(parser)
        elif choice == "2":
            print(f"\n{C_CYAN}Path ของไฟล์ CSV:{C_RESET} ", end="")
            path = input().strip().strip('"')
            mode_csv(parser, path)
        elif choice == "3":
            mode_stats(kb)
        elif choice == "4":
            mode_keywords(kb)
        elif choice == "5":
            mode_export(kb)
        elif choice == "6":
            print(f"\n{C_CYAN}Path ของไฟล์ JSON:{C_RESET} ", end="")
            path = input().strip().strip('"')
            mode_import(kb, path)
        elif choice == "7":
            mode_load_master(kb, "data/thai_administrative_areas.csv")
        elif choice == "8":
            mode_benchmark(parser, kb)
        else:
            print(f"{C_RED}❌ ไม่มีตัวเลือกนี้{C_RESET}")
        print()


# ─────────────────── Entry Point ──────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Thai Address Parser — offline, self-learning",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument("mode", nargs="?", default="menu",
                    choices=["menu", "parse", "csv", "stats", "export", "import", "keywords",
                             "load-master", "benchmark"],
                    help="โหมดการทำงาน")
    ap.add_argument("file", nargs="?", default=None,
                    help="Path ของไฟล์ (สำหรับ csv / import)")
    ap.add_argument("--db", default="data/address_knowledge.db",
                    help="Path ของ SQLite database (default: data/address_knowledge.db)")
    ap.add_argument("--limit", type=int, default=None,
                    help="จำกัดจำนวนตำบลสำหรับ benchmark แบบเร็ว")
    args = ap.parse_args()

    # เปลี่ยน working directory ไปที่โฟลเดอร์ของ script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    kb     = KnowledgeBase(db_path=args.db)
    parser = AddressParser(kb)

    try:
        if args.mode == "menu":
            main_menu(parser, kb)
        elif args.mode == "parse":
            banner()
            mode_parse(parser)
        elif args.mode == "csv":
            if not args.file:
                print(f"{C_RED}❌ กรุณาระบุ path ของไฟล์ CSV{C_RESET}")
                sys.exit(1)
            banner()
            mode_csv(parser, args.file)
        elif args.mode == "stats":
            banner()
            mode_stats(kb)
        elif args.mode == "keywords":
            banner()
            mode_keywords(kb)
        elif args.mode == "export":
            mode_export(kb)
        elif args.mode == "import":
            if not args.file:
                print(f"{C_RED}❌ กรุณาระบุ path ของไฟล์ JSON{C_RESET}")
                sys.exit(1)
            mode_import(kb, args.file)
        elif args.mode == "load-master":
            mode_load_master(kb, args.file or "data/thai_administrative_areas.csv")
        elif args.mode == "benchmark":
            mode_benchmark(parser, kb, limit=args.limit)
    finally:
        kb.close()


if __name__ == "__main__":
    main()
