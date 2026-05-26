"""
models.py — โครงสร้างข้อมูลที่อยู่
"""
from dataclasses import dataclass, asdict, field
from typing import Optional, ClassVar, Dict


@dataclass
class ParsedAddress:
    """โครงสร้างที่อยู่ที่ผ่านการแยกส่วนแล้ว"""

    raw: str = ""                         # ที่อยู่ต้นฉบับ
    house_number: Optional[str] = None    # บ้านเลขที่
    village: Optional[str] = None         # ชื่อหมู่บ้าน/โครงการ
    moo: Optional[str] = None             # หมู่ที่
    soi: Optional[str] = None             # ซอย
    road: Optional[str] = None            # ถนน
    sub_district: Optional[str] = None    # ตำบล / แขวง
    district: Optional[str] = None        # อำเภอ / เขต
    province: Optional[str] = None        # จังหวัด
    postal_code: Optional[str] = None     # รหัสไปรษณีย์
    country: Optional[str] = None         # ประเทศ
    confidence: float = 0.0               # ความมั่นใจในการแยก (0–1)

    # ชื่อคอลัมภ์ภาษาไทย สำหรับแสดงผล / export
    THAI_COLUMNS: ClassVar[Dict[str, str]] = {
        "house_number": "บ้านเลขที่",
        "village":      "หมู่บ้าน/โครงการ",
        "moo":          "หมู่ที่",
        "soi":          "ซอย",
        "road":         "ถนน",
        "sub_district": "ตำบล/แขวง",
        "district":     "อำเภอ/เขต",
        "province":     "จังหวัด",
        "postal_code":  "รหัสไปรษณีย์",
        "country":      "ประเทศ",
    }

    # ---- conversion helpers ----

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("confidence", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedAddress":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def to_display_dict(self) -> dict:
        """Dict พร้อมชื่อคอลัมภ์ภาษาไทย สำหรับพิมพ์บนหน้าจอ"""
        return {
            thai: getattr(self, eng) or ""
            for eng, thai in self.THAI_COLUMNS.items()
        }

    def to_output_row(self) -> dict:
        """Dict สำหรับ export CSV — มีคอลัมภ์ที่อยู่เต็มด้วย"""
        row = {"ที่อยู่เต็ม": self.raw, "ความมั่นใจ (%)": f"{self.confidence*100:.0f}"}
        for eng, thai in self.THAI_COLUMNS.items():
            row[thai] = getattr(self, eng) or ""
        return row

    def filled_fields(self) -> int:
        """จำนวน field ที่มีค่า (ไม่นับ raw, confidence)"""
        return sum(
            1 for f in self.THAI_COLUMNS
            if getattr(self, f) not in (None, "")
        )

    def __str__(self) -> str:
        parts = []
        for eng, thai in self.THAI_COLUMNS.items():
            val = getattr(self, eng)
            if val:
                parts.append(f"{thai}: {val}")
        return " | ".join(parts) if parts else "(ไม่สามารถแยกได้)"
