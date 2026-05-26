"""
parser.py — Engine สำหรับแยกส่วนที่อยู่ไทย/อังกฤษ
ใช้ keyword-based tokenization + fuzzy matching จาก knowledge base
ไม่ต้องพึ่ง AI API ทำงาน offline ได้ทั้งหมด
"""
import re
from typing import List, Tuple, Dict, Optional

from .models import ParsedAddress
from .knowledge_base import KnowledgeBase


class AddressParser:
    """
    Parser หลักสำหรับแยกส่วนที่อยู่
    Algorithm:
        1. ตรวจสอบ knowledge base (fuzzy match) — ถ้าเจอ ≥ threshold ใช้เลย
        2. แยกรหัสไปรษณีย์ด้วย regex
        3. ค้นหา keyword positions ในข้อความ (longest match first)
        4. สกัดค่าระหว่าง keyword แต่ละคู่
        5. คำนวณ confidence score
        6. บันทึกผลลงใน knowledge base
    """

    # รหัสไปรษณีย์ไทย = 5 หลัก
    POSTAL_RE = re.compile(r"(?<!\d)(\d{5})(?!\d)")

    # ตัวเลขที่ดูเหมือนบ้านเลขที่
    HOUSE_RE  = re.compile(r"^(\d[\d/\-–ก-ฮA-Za-z]*)")

    # ตัวอักษรพิเศษที่ตัดออกจากต้น/ท้ายค่าได้
    TRIM_CHARS = " \t\n\r.,;:ๆ"

    # Keywords ที่ตัวมันเองคือค่า — เช่น "กรุงเทพมหานคร" → province = "กรุงเทพมหานคร"
    SELF_VALUE_KEYWORDS: Dict[str, str] = {
        "กรุงเทพมหานคร": "กรุงเทพมหานคร",
        "กรุงเทพฯ":      "กรุงเทพมหานคร",
        "กทม.":          "กรุงเทพมหานคร",
        "กทม":           "กรุงเทพมหานคร",
        "Bangkok":       "Bangkok",
        "Thailand":      "Thailand",
    }

    # Pattern สำหรับตรวจจับชื่อหมู่บ้าน/โครงการหลังบ้านเลขที่
    # เช่น "456 บ้านพฤกษา" → house="456", village="บ้านพฤกษา"
    VILLAGE_AFTER_HOUSE_RE = re.compile(
        r"^(\d[\d/\-–]*)[\s]+((?:บ้าน|หมู่บ้าน|โครงการ|คอนโด|อาคาร|ตึก)\S{1,25})"
    )

    def __init__(self, kb: KnowledgeBase, cache_threshold: float = 0.88):
        self.kb = kb
        self.cache_threshold = cache_threshold

    # ──────────────────────────── Public API ──────────────────────────────

    def parse(self, raw: str, remember: bool = True) -> ParsedAddress:
        """แยกส่วนที่อยู่ — entry point หลัก"""
        if not raw or not raw.strip():
            return ParsedAddress(raw=raw or "")

        raw = raw.strip()

        # 1. A correction contains address-specific values; reuse it only
        # for the exact input. Fuzzy reuse can silently copy house numbers.
        cached = self.kb.find_exact(raw)
        if cached:
            addr = ParsedAddress.from_dict(cached)
            addr.raw        = raw
            addr.confidence = 1.0
            return addr

        # 2. แยกด้วย rule-based
        addr = self._rule_based_parse(raw, track_usage=remember)

        # 3. บันทึกลง knowledge base (unverified)
        if remember:
            self.kb.save_example(raw, addr.to_dict(), verified=False)

        return addr

    def parse_batch(self, addresses: List[str], remember: bool = True) -> List[ParsedAddress]:
        """แยกที่อยู่หลายรายการพร้อมกัน"""
        return [self.parse(a, remember=remember) for a in addresses]

    def learn(self, raw: str, parsed: ParsedAddress, corrected: ParsedAddress):
        """บันทึกการแก้ไขจากผู้ใช้ เพื่อปรับปรุง knowledge base"""
        self.kb.save_correction(raw, parsed.to_dict(), corrected.to_dict())

    # ──────────────────────────── Core Logic ──────────────────────────────

    def _rule_based_parse(self, text: str, track_usage: bool = True) -> ParsedAddress:
        addr = ParsedAddress(raw=text)

        # ── Step 1: แยกรหัสไปรษณีย์ก่อน ──
        postal_match = self.POSTAL_RE.search(text)
        if postal_match:
            addr.postal_code = postal_match.group(1)

        # ── Step 2: ดึง keywords จาก KB ──
        keywords = self.kb.get_keywords()   # เรียงยาวก่อน

        # ── Step 3: ค้นหาตำแหน่ง keywords (ไม่ overlap) ──
        matches = self._find_matches(text, keywords, track_usage=track_usage)

        # ── Step 4: สกัดค่าระหว่าง keywords ──
        components = self._extract_values(text, matches)

        # ── Step 5: Assign ค่าลงใน ParsedAddress ──
        for component, value in components.items():
            # ตัดรหัสไปรษณีย์ออกจาก field อื่น
            if component != "postal_code":
                value = self.POSTAL_RE.sub("", value)
            value = value.strip(self.TRIM_CHARS)
            if value and hasattr(addr, component):
                setattr(addr, component, value)

        # ── Step 5b: Post-process house_number ──
        # ถ้า house_number มีชื่อหมู่บ้าน/โครงการติดมา → แยกออก
        if addr.house_number and not addr.village:
            m = self.VILLAGE_AFTER_HOUSE_RE.match(addr.house_number)
            if m:
                addr.house_number = m.group(1)
                addr.village      = m.group(2)
        if addr.house_number:
            # A location-only suffix may be the first detected keyword; do
            # not retain arbitrary free text in the leading house-number field.
            m = self.HOUSE_RE.match(addr.house_number)
            if m:
                addr.house_number = m.group(1)

        # ── Step 5c: Post-process self-value keywords (เช่น กรุงเทพมหานคร) ──
        # ถ้า province ยังว่าง ให้ค้นหา self-value keywords ในข้อความ
        if not addr.province:
            for kw, canonical_val in self.SELF_VALUE_KEYWORDS.items():
                if kw in text:
                    addr.province = canonical_val
                    break
        if not addr.country and "Thailand" in text:
            addr.country = "Thailand"

        # ── Step 5d: Canonical administrative-area master data ──
        master = self.kb.match_admin_area(text, addr.postal_code)
        if master:
            master_score = master.get("score", 0)
            for component in ("sub_district", "district", "province"):
                val = master.get(component)
                if not val:
                    continue
                # ── Guard สำหรับ sub_district ──
                # match_admin_area ใช้ substring check ใน searchable text
                # ซึ่งอาจ false positive ได้: เช่น "กรุงเทพมหานคร" → "รุง" (score=5)
                # เพราะ "รุง" เป็น substring ของ "กรุงเทพมหานคร"
                # Fix: ต้องเป็น high-score (labelled context, ≥25) หรือ whole-word match
                if component == "sub_district" and master_score < 25:
                    # ตรวจว่า val ปรากฏเป็น token แยกด้วย whitespace/punctuation
                    if not re.search(
                        r"(?:^|[\s.,/])" + re.escape(val) + r"(?:[\s.,/]|$)",
                        text,
                    ):
                        continue   # substring เท่านั้น — ข้ามไป
                setattr(addr, component, val)

        # ── Step 6: Confidence ──
        key_fields = ["house_number", "sub_district", "district", "province"]
        filled     = sum(1 for f in key_fields if getattr(addr, f))
        addr.confidence = filled / len(key_fields)

        return addr

    # ──────────────────────────── Helpers ─────────────────────────────────

    def _find_matches(
        self,
        text: str,
        keywords: List[Tuple[str, str]],
        track_usage: bool = True,
    ) -> List[Tuple[int, int, str, str]]:
        """
        ค้นหา keyword ทั้งหมดในข้อความโดยไม่ให้ overlap กัน
        Returns list of (start_pos, length, component, keyword)

        Performance: รวม keyword usage ไว้ก่อน แล้ว bulk-update ครั้งเดียว
        แทนที่จะเรียก DB write ทุก keyword match (ลด DB round-trips จาก N → 1)
        """
        used: set = set()
        matches: List[Tuple[int, int, str, str]] = []
        used_keywords: List[str] = []       # เก็บไว้ bulk-update ทีเดียว

        for keyword, component in keywords:
            start = 0
            while True:
                idx = text.find(keyword, start)
                if idx == -1:
                    break

                span = set(range(idx, idx + len(keyword)))
                if not span & used:
                    matches.append((idx, len(keyword), component, keyword))
                    used.update(span)
                    if track_usage:
                        used_keywords.append(keyword)

                start = idx + len(keyword)

        # Bulk-update usage ใน transaction เดียว (ไม่ใช่ N × single UPDATE)
        if track_usage and used_keywords:
            self.kb.batch_increment_keyword_usage(used_keywords)

        matches.sort(key=lambda x: x[0])
        return matches

    def _extract_values(
        self,
        text: str,
        matches: List[Tuple[int, int, str, str]],
    ) -> Dict[str, str]:
        """
        สกัดค่าระหว่าง keyword แต่ละคู่
        - ค่าของ keyword[i] = text[end_of_kw_i : start_of_kw_{i+1}]
        - ข้อความก่อน keyword แรก → house_number (ถ้ายังไม่มี)
        """
        components: Dict[str, str] = {}

        for i, (start, klen, component, keyword) in enumerate(matches):
            val_start = start + klen
            val_end   = matches[i + 1][0] if i + 1 < len(matches) else len(text)
            value     = text[val_start:val_end].strip(self.TRIM_CHARS)

            if value and component not in components:
                components[component] = value

        # ข้อความหน้า keyword แรก → บ้านเลขที่ (ถ้ายังไม่มี)
        if matches and "house_number" not in components:
            prefix = text[: matches[0][0]].strip(self.TRIM_CHARS)
            # ตัด prefix เช่น "บ้านเลขที่", "เลขที่" ออก
            prefix = re.sub(r"^(บ้านเลขที่|เลขที่)\s*", "", prefix).strip()
            if prefix:
                components["house_number"] = prefix
        elif not matches:
            # ไม่เจอ keyword เลย — ลองดึง house number จาก regex
            m = self.HOUSE_RE.match(text)
            if m:
                components["house_number"] = m.group(1)

        return components

    # ──────────────────────────── Display ─────────────────────────────────

    @staticmethod
    def format_result(addr: ParsedAddress, show_confidence: bool = True) -> str:
        """แปลง ParsedAddress เป็น string สวยงามสำหรับแสดงบน console"""
        lines = [f"📍 ที่อยู่ต้นฉบับ: {addr.raw}"]
        lines.append("─" * 55)
        for eng, thai in ParsedAddress.THAI_COLUMNS.items():
            val = getattr(addr, eng)
            if val:
                lines.append(f"  {thai:<18}: {val}")
        if show_confidence:
            bar = "█" * int(addr.confidence * 10) + "░" * (10 - int(addr.confidence * 10))
            lines.append(f"  {'ความมั่นใจ':<18}: [{bar}] {addr.confidence*100:.0f}%")
        return "\n".join(lines)
