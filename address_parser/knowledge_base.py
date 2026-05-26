"""
knowledge_base.py — ฐานความรู้แบบ self-learning บน SQLite
ไม่ต้องพึ่ง external API — ทำงาน offline ได้ 100%
"""
import sqlite3
import json
import hashlib
import os
import csv
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, List, Tuple, Dict, Any


class KnowledgeBase:
    """
    SQLite-backed knowledge base สำหรับเรียนรู้รูปแบบที่อยู่
    - เก็บตัวอย่างที่อยู่ที่ผ่านการตรวจสอบแล้ว
    - เรียนรู้จากการแก้ไขของผู้ใช้
    - ใช้ fuzzy matching เพื่อดึงตัวอย่างที่คล้ายกัน
    - เก็บ keyword patterns สำหรับระบุส่วนประกอบของที่อยู่
    """

    def __init__(self, db_path: str = "data/address_knowledge.db"):
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._seed_keywords()
        bundled_master = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "data", "thai_administrative_areas.csv"
        ))
        if self.get_admin_area_count() == 0 and os.path.exists(bundled_master):
            self.import_admin_csv(
                bundled_master,
                source="thailand-geography-data/thailand-geography-json",
            )

    # ─────────────────────────── Schema ────────────────────────────

    def _init_schema(self):
        cur = self.conn.cursor()

        # ตัวอย่างที่อยู่ที่บันทึกไว้
        cur.execute("""
            CREATE TABLE IF NOT EXISTS address_examples (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_address  TEXT    UNIQUE,
                address_hash TEXT,
                parsed_json  TEXT,
                verified     INTEGER DEFAULT 0,
                source       TEXT    DEFAULT 'auto',
                created_at   TEXT,
                updated_at   TEXT
            )
        """)

        # การแก้ไขจากผู้ใช้
        cur.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_address  TEXT,
                wrong_json   TEXT,
                correct_json TEXT,
                created_at   TEXT
            )
        """)

        # Keyword patterns สำหรับระบุส่วนประกอบ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keyword_patterns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT    UNIQUE,
                component   TEXT,
                language    TEXT    DEFAULT 'th',
                confidence  REAL    DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0,
                is_custom   INTEGER DEFAULT 0,
                created_at  TEXT
            )
        """)

        # สถิติการใช้งาน
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                detail     TEXT,
                created_at TEXT
            )
        """)

        # Master data for deterministic Thai administrative area resolution.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS administrative_areas (
                subdistrict_code TEXT PRIMARY KEY,
                postal_code      TEXT,
                sub_district_th  TEXT,
                district_th      TEXT,
                province_th      TEXT,
                sub_district_en  TEXT,
                district_en      TEXT,
                province_en      TEXT,
                source           TEXT,
                imported_at      TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_admin_postal
            ON administrative_areas(postal_code)
        """)

        self.conn.commit()

    # ─────────────────────────── Seeding ───────────────────────────

    def _seed_keywords(self):
        """เพิ่ม keywords เริ่มต้น (ถ้ายังไม่มี)"""
        keywords = [
            # ─── Thai (ยาว → สั้น เพื่อป้องกัน substring match ผิด) ───
            ("บ้านเลขที่",      "house_number", "th"),
            ("เลขที่",          "house_number", "th"),
            ("หมู่บ้าน",        "village",      "th"),
            ("หมู่ที่",         "moo",          "th"),
            ("หมู่",            "moo",          "th"),
            ("ม.",              "moo",          "th"),
            ("ซอย",             "soi",          "th"),
            ("ซ.",              "soi",          "th"),
            ("ถนน",             "road",         "th"),
            ("ถ.",              "road",         "th"),
            ("ตำบล",            "sub_district", "th"),
            ("ต.",              "sub_district", "th"),
            ("แขวง",            "sub_district", "th"),
            ("อำเภอ",           "district",     "th"),
            ("อ.",              "district",     "th"),
            ("เขต",             "district",     "th"),
            ("กรุงเทพมหานคร",   "province",     "th"),
            ("กรุงเทพฯ",        "province",     "th"),
            ("กทม.",            "province",     "th"),
            ("กทม",             "province",     "th"),
            ("จังหวัด",         "province",     "th"),
            ("จ.",              "province",     "th"),
            ("ประเทศ",          "country",      "th"),
            # ─── English ───
            ("No.",             "house_number", "en"),
            ("Village",         "village",      "en"),
            ("Moo",             "moo",          "en"),
            ("Soi",             "soi",          "en"),
            ("Lane",            "soi",          "en"),
            ("Alley",           "soi",          "en"),
            ("Road",            "road",         "en"),
            ("Rd.",             "road",         "en"),
            ("Street",          "road",         "en"),
            ("St.",             "road",         "en"),
            ("Tambon",          "sub_district", "en"),
            ("Subdistrict",     "sub_district", "en"),
            ("Sub-district",    "sub_district", "en"),
            ("Khwaeng",         "sub_district", "en"),
            ("Amphoe",          "district",     "en"),
            ("District",        "district",     "en"),
            ("Khet",            "district",     "en"),
            ("Bangkok",         "province",     "en"),
            ("Province",        "province",     "en"),
            ("Thailand",        "country",      "en"),
        ]

        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        for kw, comp, lang in keywords:
            cur.execute("""
                INSERT OR IGNORE INTO keyword_patterns
                    (keyword, component, language, created_at)
                VALUES (?, ?, ?, ?)
            """, (kw, comp, lang, now))
        self.conn.commit()

    # ─────────────────────────── Examples ──────────────────────────

    def save_example(self, raw: str, parsed: dict, verified: bool = False, source: str = "auto"):
        """บันทึกตัวอย่างที่อยู่ที่ผ่านการแยกแล้ว"""
        cur = self.conn.cursor()
        addr_hash = hashlib.md5(raw.encode("utf-8")).hexdigest()
        now = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO address_examples
                (raw_address, address_hash, parsed_json, verified, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(raw_address) DO UPDATE SET
                parsed_json = excluded.parsed_json,
                verified    = MAX(verified, excluded.verified),
                source      = excluded.source,
                updated_at  = excluded.updated_at
        """, (raw, addr_hash, json.dumps(parsed, ensure_ascii=False),
              1 if verified else 0, source, now, now))
        self.conn.commit()

    def find_similar(self, raw: str, threshold: float = 0.85) -> Optional[dict]:
        """ค้นหาตัวอย่างที่คล้ายกันใน knowledge base (fuzzy match)"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT raw_address, parsed_json
            FROM address_examples
            WHERE verified = 1
            ORDER BY updated_at DESC
            LIMIT 500
        """)
        rows = cur.fetchall()

        best_parsed = None
        best_ratio  = 0.0

        for row in rows:
            ratio = SequenceMatcher(None, raw.strip(), row["raw_address"].strip()).ratio()
            if ratio > best_ratio:
                best_ratio  = ratio
                best_parsed = row["parsed_json"]

        if best_ratio >= threshold and best_parsed:
            return json.loads(best_parsed)
        return None

    def find_exact(self, raw: str) -> Optional[dict]:
        """Return a user-verified result only for the exact original address."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT parsed_json
            FROM address_examples
            WHERE raw_address = ? AND verified = 1
        """, (raw.strip(),))
        row = cur.fetchone()
        return json.loads(row["parsed_json"]) if row else None

    def get_all_examples(self, verified_only: bool = False) -> List[dict]:
        cur = self.conn.cursor()
        if verified_only:
            cur.execute("SELECT * FROM address_examples WHERE verified=1 ORDER BY updated_at DESC")
        else:
            cur.execute("SELECT * FROM address_examples ORDER BY updated_at DESC")
        return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────── Corrections ───────────────────────

    def save_correction(self, raw: str, wrong: dict, correct: dict):
        """บันทึกการแก้ไข และ mark ตัวอย่างว่าผ่านการตรวจสอบ"""
        cur = self.conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("""
            INSERT INTO corrections (raw_address, wrong_json, correct_json, created_at)
            VALUES (?, ?, ?, ?)
        """, (raw, json.dumps(wrong, ensure_ascii=False),
              json.dumps(correct, ensure_ascii=False), now))
        self.conn.commit()
        # บันทึก correction เป็น verified example
        self.save_example(raw, correct, verified=True, source="correction")
        self._log_event("correction", f"corrected: {raw[:50]}")

    def get_corrections(self) -> List[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM corrections ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────── Keywords ──────────────────────────

    def get_keywords(self) -> List[Tuple[str, str]]:
        """ดึง keyword ทั้งหมด เรียงจากยาวไปสั้น (ป้องกัน substring match ผิด)"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT keyword, component
            FROM keyword_patterns
            ORDER BY LENGTH(keyword) DESC, confidence DESC
        """)
        return [(row["keyword"], row["component"]) for row in cur.fetchall()]

    def add_keyword(self, keyword: str, component: str, language: str = "th") -> bool:
        """เพิ่ม keyword ใหม่ (custom)"""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                INSERT INTO keyword_patterns
                    (keyword, component, language, is_custom, created_at)
                VALUES (?, ?, ?, 1, ?)
            """, (keyword, component, language, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # keyword มีอยู่แล้ว — update component
            cur.execute("""
                UPDATE keyword_patterns
                SET component = ?, language = ?, is_custom = 1
                WHERE keyword = ?
            """, (component, language, keyword))
            self.conn.commit()
            return True

    def remove_keyword(self, keyword: str) -> bool:
        """ลบ keyword (เฉพาะ custom เท่านั้น)"""
        cur = self.conn.cursor()
        cur.execute("""
            DELETE FROM keyword_patterns
            WHERE keyword = ? AND is_custom = 1
        """, (keyword,))
        self.conn.commit()
        return cur.rowcount > 0

    def increment_keyword_usage(self, keyword: str):
        """Single-keyword increment (backward compat). ใช้ batch_increment แทนเพื่อ performance."""
        self.batch_increment_keyword_usage([keyword])

    def batch_increment_keyword_usage(self, keywords: List[str]):
        """
        Bulk-update usage counts ด้วย transaction เดียว — เร็วกว่า N × single UPDATE
        เรียกครั้งเดียวต่อหนึ่ง parse แทนการเรียกซ้ำทุก keyword match
        """
        if not keywords:
            return
        from collections import Counter
        counts = Counter(keywords)
        self.conn.executemany(
            "UPDATE keyword_patterns SET usage_count = usage_count + ? WHERE keyword = ?",
            [(cnt, kw) for kw, cnt in counts.items()],
        )
        self.conn.commit()

    def get_top_keywords(self, n: int = 20) -> List[dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT keyword, component, language, usage_count
            FROM keyword_patterns
            ORDER BY usage_count DESC
            LIMIT ?
        """, (n,))
        return [dict(r) for r in cur.fetchall()]

    # ───────────────────── Administrative Master Data ─────────────────────

    @staticmethod
    def _district_without_prefix(name: str) -> str:
        return re.sub(r"^(เขต|อำเภอ|กิ่งอำเภอ)\s*", "", (name or "").strip())

    def import_admin_csv(self, path: str, source: str = "local CSV") -> int:
        """Import canonical Thai administrative areas from a local CSV file."""
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        return self.import_admin_rows(rows, source=source)

    def import_admin_rows(self, rows: List[dict], source: str = "import") -> int:
        """Upsert administrative rows; intended for public master-data imports."""
        now = datetime.now().isoformat()
        values = []
        for row in rows:
            code = str(row.get("subdistrict_code") or row.get("subdistrictCode") or row.get("id") or "")
            if not code:
                continue
            values.append((
                code,
                str(row.get("postal_code") or row.get("postalCode") or row.get("zip_code") or ""),
                row.get("sub_district_th") or row.get("subdistrictNameTh") or row.get("name_th") or "",
                self._district_without_prefix(
                    row.get("district_th") or row.get("districtNameTh") or ""
                ),
                row.get("province_th") or row.get("provinceNameTh") or "",
                row.get("sub_district_en") or row.get("subdistrictNameEn") or row.get("name_en") or "",
                row.get("district_en") or row.get("districtNameEn") or "",
                row.get("province_en") or row.get("provinceNameEn") or "",
                source,
                now,
            ))
        self.conn.executemany("""
            INSERT INTO administrative_areas (
                subdistrict_code, postal_code, sub_district_th, district_th,
                province_th, sub_district_en, district_en, province_en,
                source, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(subdistrict_code) DO UPDATE SET
                postal_code = excluded.postal_code,
                sub_district_th = excluded.sub_district_th,
                district_th = excluded.district_th,
                province_th = excluded.province_th,
                sub_district_en = excluded.sub_district_en,
                district_en = excluded.district_en,
                province_en = excluded.province_en,
                source = excluded.source,
                imported_at = excluded.imported_at
        """, values)
        self.conn.commit()
        return len(values)

    def get_admin_area_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM administrative_areas").fetchone()
        return row["n"]

    def get_admin_areas(self, limit: Optional[int] = None) -> List[dict]:
        sql = "SELECT * FROM administrative_areas ORDER BY subdistrict_code"
        params: tuple = ()
        if limit:
            sql += " LIMIT ?"
            params = (limit,)
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    @staticmethod
    def _search_text(value: str) -> str:
        return re.sub(r"[\s.,\-–_/]", "", (value or "").casefold())

    def _province_names(self) -> List[str]:
        """
        Cached list of Thai province names (โหลดครั้งแรกแล้วเก็บใน memory)
        ใช้ pre-filter rows ก่อน full scan เมื่อไม่มีรหัสไปรษณีย์
        """
        if not hasattr(self, "_prov_names_cache"):
            rows = self.conn.execute(
                "SELECT DISTINCT province_th FROM administrative_areas WHERE province_th != ''"
            ).fetchall()
            self._prov_names_cache: List[str] = [r["province_th"] for r in rows]
        return self._prov_names_cache

    def match_admin_area(self, text: str, postal_code: Optional[str] = None) -> Optional[dict]:
        """
        Locate named administrative components in an address.

        Postal codes narrow candidates, but never alone cause an unspecified
        subdistrict or district to be invented in the returned result.

        Without a postal code: ใช้ province name pre-filtering ลด scan จาก 7,436
        ลงเหลือ ~100-500 rows ต่อจังหวัด (เร็วขึ้น ~10-15×)
        """
        if postal_code:
            rows = self.conn.execute(
                "SELECT * FROM administrative_areas WHERE postal_code = ?", (postal_code,)
            ).fetchall()
        else:
            # Pre-filter by province name present in the text
            searchable_for_prov = self._search_text(text)
            matching_provinces = [
                prov for prov in self._province_names()
                if self._search_text(prov) in searchable_for_prov
            ]
            if matching_provinces:
                placeholders = ",".join(["?"] * len(matching_provinces))
                rows = self.conn.execute(
                    f"SELECT * FROM administrative_areas WHERE province_th IN ({placeholders})",
                    matching_provinces,
                ).fetchall()
            else:
                # Fallback: scan all (ไม่ควรเกิดบ่อย)
                rows = self.conn.execute("SELECT * FROM administrative_areas").fetchall()
        if not rows:
            return None

        searchable = self._search_text(text)
        labelled = re.sub(r"\s+", "", (text or "").casefold())
        best = None
        best_rank = (0, 0)
        for row in rows:
            th_hits = {
                "sub_district": bool(row["sub_district_th"]) and self._search_text(row["sub_district_th"]) in searchable,
                "district": bool(row["district_th"]) and self._search_text(row["district_th"]) in searchable,
                "province": bool(row["province_th"]) and self._search_text(row["province_th"]) in searchable,
            }
            en_hits = {
                "sub_district": bool(row["sub_district_en"]) and self._search_text(row["sub_district_en"]) in searchable,
                "district": bool(row["district_en"]) and self._search_text(row["district_en"]) in searchable,
                "province": bool(row["province_en"]) and self._search_text(row["province_en"]) in searchable,
            }
            th_score = 5 * th_hits["sub_district"] + 3 * th_hits["district"] + 2 * th_hits["province"]
            en_score = 5 * en_hits["sub_district"] + 3 * en_hits["district"] + 2 * en_hits["province"]
            sub_th = self._search_text(row["sub_district_th"])
            district_th = self._search_text(row["district_th"])
            province_th = self._search_text(row["province_th"])
            # Labels disambiguate repeated names such as แขวงดุสิต/เขตดุสิต.
            if f"ตำบล{sub_th}" in labelled or f"ต.{sub_th}" in labelled or f"แขวง{sub_th}" in labelled:
                th_score += 20
            if f"อำเภอ{district_th}" in labelled or f"อ.{district_th}" in labelled or f"เขต{district_th}" in labelled:
                th_score += 6
            if f"จังหวัด{province_th}" in labelled or f"จ.{province_th}" in labelled:
                th_score += 4
            # Do not reward one occurrence as both levels when an alternative
            # candidate contains distinct subdistrict and district names.
            if sub_th == district_th and th_hits["sub_district"] and th_hits["district"]:
                th_score -= 2

            def ordered_location_bonus(suffix: str, hits: dict) -> int:
                if not all(hits.values()):
                    return 0
                cursor = 0
                for field in ("sub_district", "district", "province"):
                    value = self._search_text(row[f"{field}_{suffix}"])
                    position = searchable.find(value, cursor)
                    if position == -1:
                        return 0
                    cursor = position + len(value)
                return 10

            th_score += ordered_location_bonus("th", th_hits)
            en_score += ordered_location_bonus("en", en_hits)
            score = max(th_score, en_score)
            chosen_hits = th_hits if th_score >= en_score else en_hits
            suffix = "th" if th_score >= en_score else "en"
            specificity = sum(
                len(row[f"{field}_{suffix}"] or "")
                for field, present in chosen_hits.items()
                if present
            )
            if (score, specificity) > best_rank:
                best_rank = (score, specificity)
                best = {
                    "sub_district": row[f"sub_district_{suffix}"] if chosen_hits["sub_district"] else None,
                    "district": row[f"district_{suffix}"] if chosen_hits["district"] else None,
                    "province": row[f"province_{suffix}"] if chosen_hits["province"] else None,
                    "postal_code": row["postal_code"],
                    "score": score,
                }
        return best if best_rank[0] else None

    # ─────────────────────────── Stats ─────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        cur = self.conn.cursor()

        cur.execute("SELECT COUNT(*) as n FROM address_examples")
        total = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM address_examples WHERE verified=1")
        verified = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM corrections")
        corrections = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM keyword_patterns")
        kw_total = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM keyword_patterns WHERE is_custom=1")
        kw_custom = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM administrative_areas")
        admin_areas = cur.fetchone()["n"]

        return {
            "total_examples":    total,
            "verified_examples": verified,
            "corrections":       corrections,
            "keyword_patterns":  kw_total,
            "custom_keywords":   kw_custom,
            "administrative_areas": admin_areas,
        }

    def _log_event(self, event_type: str, detail: str = ""):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO usage_stats (event_type, detail, created_at)
            VALUES (?, ?, ?)
        """, (event_type, detail, datetime.now().isoformat()))
        self.conn.commit()

    # ─────────────────────────── Export / Import ───────────────────

    def export_json(self, path: str):
        """Export knowledge base เป็น JSON"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "verified_examples": [],
            "keyword_patterns": [],
        }

        cur = self.conn.cursor()
        cur.execute("SELECT raw_address, parsed_json FROM address_examples WHERE verified=1")
        for row in cur.fetchall():
            data["verified_examples"].append({
                "raw": row["raw_address"],
                "parsed": json.loads(row["parsed_json"]),
            })

        cur.execute("SELECT keyword, component, language FROM keyword_patterns WHERE is_custom=1")
        for row in cur.fetchall():
            data["keyword_patterns"].append(dict(row))

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, path: str) -> dict:
        """Import knowledge จากไฟล์ JSON"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported_ex  = 0
        imported_kw  = 0

        for ex in data.get("verified_examples", []):
            self.save_example(ex["raw"], ex["parsed"], verified=True, source="import")
            imported_ex += 1

        for kw in data.get("keyword_patterns", []):
            self.add_keyword(kw["keyword"], kw["component"], kw.get("language", "th"))
            imported_kw += 1

        return {"examples": imported_ex, "keywords": imported_kw}

    def close(self):
        self.conn.close()
