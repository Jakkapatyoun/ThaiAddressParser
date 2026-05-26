"""
test_parser.py — Unit tests สำหรับ Thai Address Parser
รัน: python3 -m unittest tests/test_parser.py -v
"""
import os
import time
import tempfile
import unittest
from pathlib import Path

from address_parser import AddressParser, KnowledgeBase, ParsedAddress


# ──────────────── Master data สำหรับ test (isolated) ──────────────────────────
MASTER_ROWS = [
    {
        "subdistrict_code": "500107",
        "postal_code": "50300",
        "sub_district_th": "ช้างเผือก",
        "district_th": "เมืองเชียงใหม่",
        "province_th": "เชียงใหม่",
        "sub_district_en": "Chang Phueak",
        "district_en": "Mueang Chiang Mai",
        "province_en": "Chiang Mai",
    },
    {
        "subdistrict_code": "101101",
        "postal_code": "10110",
        "sub_district_th": "คลองเตยเหนือ",
        "district_th": "วัฒนา",
        "province_th": "กรุงเทพมหานคร",
        "sub_district_en": "Khlong Toei Nuea",
        "district_en": "Watthana",
        "province_en": "Bangkok",
    },
    {
        "subdistrict_code": "401701",
        "postal_code": "40000",
        "sub_district_th": "ในเมือง",
        "district_th": "เมืองขอนแก่น",
        "province_th": "ขอนแก่น",
        "sub_district_en": "Nai Mueang",
        "district_en": "Mueang Khon Kaen",
        "province_en": "Khon Kaen",
    },
    {
        # ตำบลจริงที่ชื่อ 'รุง' — ใช้ทดสอบ false positive sub_district จาก substring
        "subdistrict_code": "331601",
        "postal_code": "33110",
        "sub_district_th": "รุง",
        "district_th": "กันทรลักษ์",
        "province_th": "ศรีสะเกษ",
        "sub_district_en": "Rung",
        "district_en": "Kantharalak",
        "province_en": "Si Sa Ket",
    },
    {
        "subdistrict_code": "640501",
        "postal_code": "64110",
        "sub_district_th": "ในเมือง",
        "district_th": "สวรรคโลก",
        "province_th": "สุโขทัย",
        "sub_district_en": "Nai Mueang",
        "district_en": "Sawankhalok",
        "province_en": "Sukhothai",
    },
    {
        "subdistrict_code": "180102",
        "postal_code": "17000",
        "sub_district_th": "นางลือ",
        "district_th": "เมืองชัยนาท",
        "province_th": "ชัยนาท",
        "sub_district_en": "Nang Lue",
        "district_en": "Mueang Chai Nat",
        "province_en": "Chai Nat",
    },
]


# ──────────────── Base Test Class ──────────────────────────────────────────────
class ParserTestBase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.kb = KnowledgeBase(str(Path(self.tempdir.name) / "knowledge.db"))
        self.kb.import_admin_rows(MASTER_ROWS, source="test")
        self.parser = AddressParser(self.kb)

    def tearDown(self):
        self.kb.close()
        self.tempdir.cleanup()


# ──────────────── Correctness Tests ───────────────────────────────────────────
class CorrectnessTest(ParserTestBase):

    # ── Existing tests (ต้องยังผ่าน) ──────────────────────────────────────────

    def test_unlabelled_province_uses_master_data(self):
        addr = self.parser.parse(
            "88/2 ถนนเชียงใหม่-ลำปาง ต.ช้างเผือก อ.เมืองเชียงใหม่ เชียงใหม่ 50300"
        )
        self.assertEqual(addr.sub_district, "ช้างเผือก")
        self.assertEqual(addr.district, "เมืองเชียงใหม่")
        self.assertEqual(addr.province, "เชียงใหม่")

    def test_verified_address_is_not_fuzzy_copied_to_new_house(self):
        """Exact-match cache ไม่ copy บ้านเลขที่ไปยังที่อยู่ใหม่"""
        original = "123 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110"
        corrected = ParsedAddress(
            raw=original,
            house_number="123",
            road="สุขุมวิท",
            sub_district="คลองเตยเหนือ",
            district="วัฒนา",
            province="กรุงเทพมหานคร",
            postal_code="10110",
        )
        self.parser.learn(original, self.parser.parse(original), corrected)
        new_address = self.parser.parse(
            "124 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110"
        )
        self.assertEqual(new_address.house_number, "124")

    def test_unlabelled_repeated_area_names_follow_address_order(self):
        """ที่อยู่ไม่มี label — ใช้ลำดับ sub/district/province"""
        cases = [
            (
                "5396/1 ประชาร่วมใจ ในเมือง สวรรคโลก สุโขทัย 64110",
                ("ในเมือง", "สวรรคโลก", "สุโขทัย"),
            ),
            (
                "800/1 ประชาร่วมใจ นางลือ เมืองชัยนาท ชัยนาท 17000",
                ("นางลือ", "เมืองชัยนาท", "ชัยนาท"),
            ),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                addr = self.parser.parse(raw, remember=False)
                self.assertEqual(
                    (addr.sub_district, addr.district, addr.province),
                    expected,
                )

    def test_plain_database_filename_is_valid(self):
        """KnowledgeBase ทำงานได้เมื่อ db_path ไม่มี directory component"""
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                kb = KnowledgeBase("local.db")
                self.assertGreater(kb.get_admin_area_count(), 4)
                kb.close()
                self.assertTrue(Path("local.db").exists())
            finally:
                os.chdir(previous)

    # ── New: Bug fixes ─────────────────────────────────────────────────────────

    def test_province_name_only_does_not_produce_false_sub_district(self):
        """
        Bug fix: "กรุงเทพมหานคร" เป็น input → ไม่ควร set sub_district เป็น "รุง"
        เพราะ "รุง" เป็นแค่ substring ของ "กรุงเทพมหานคร" ไม่ใช่ standalone word
        """
        addr = self.parser.parse("กรุงเทพมหานคร", remember=False)
        self.assertEqual(addr.province, "กรุงเทพมหานคร")
        self.assertIsNone(
            addr.sub_district,
            f"sub_district ควรเป็น None แต่ได้ {addr.sub_district!r}",
        )

    def test_substring_sub_district_from_other_province_is_blocked(self):
        """
        'รุง' (ศรีสะเกษ) ต้องไม่ปรากฏเป็น sub_district ของ 'กรุงเทพมหานคร'
        แม้ 'รุง' จะเป็น substring ของ 'กรุงเทพมหานคร'
        """
        addr = self.parser.parse(
            "99 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110",
            remember=False,
        )
        self.assertNotEqual(
            addr.sub_district,
            "รุง",
            "sub_district 'รุง' ไม่ควรปรากฏในที่อยู่กรุงเทพ",
        )
        self.assertEqual(addr.province, "กรุงเทพมหานคร")

    def test_labelled_sub_district_is_set_even_with_low_base_score(self):
        """
        ต.ช้างเผือก (labelled) ต้องได้ sub_district ถูกต้อง
        แม้ base score จะต่ำ — เพราะมี label bonus (score≥25)
        """
        addr = self.parser.parse(
            "88/2 ถ.เชียงใหม่-ลำปาง ต.ช้างเผือก อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50300",
            remember=False,
        )
        self.assertEqual(addr.sub_district, "ช้างเผือก")
        self.assertEqual(addr.province, "เชียงใหม่")

    def test_unlabelled_whole_word_sub_district_is_set(self):
        """
        ช้างเผือก เชียงใหม่ (ไม่มี label แต่เป็น standalone word) → sub_district ถูกต้อง
        """
        addr = self.parser.parse(
            "1/1 ช้างเผือก เชียงใหม่ 50300", remember=False
        )
        self.assertEqual(addr.sub_district, "ช้างเผือก")
        self.assertEqual(addr.province, "เชียงใหม่")

    def test_house_number_formats(self):
        """รองรับบ้านเลขที่หลายรูปแบบ"""
        cases = [
            ("123/4 ต.ช้างเผือก เชียงใหม่ 50300", "123/4"),
            ("99-1 ต.ช้างเผือก เชียงใหม่ 50300", "99-1"),
            ("10ก ต.ช้างเผือก เชียงใหม่ 50300", "10ก"),
        ]
        for raw, expected_house in cases:
            with self.subTest(raw=raw):
                addr = self.parser.parse(raw, remember=False)
                self.assertEqual(addr.house_number, expected_house)

    def test_bangkok_short_forms(self):
        """กทม / กทม. / กรุงเทพฯ → province = กรุงเทพมหานคร"""
        for prov_text in ("กทม", "กทม.", "กรุงเทพฯ"):
            raw = f"99 ม.3 ถ.สุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา {prov_text} 10110"
            with self.subTest(prov_text=prov_text):
                addr = self.parser.parse(raw, remember=False)
                self.assertEqual(addr.province, "กรุงเทพมหานคร")

    def test_empty_input_returns_empty_address(self):
        """Input ว่าง → ParsedAddress ว่าง ไม่ error"""
        for raw in ("", "   ", None):
            with self.subTest(raw=raw):
                addr = self.parser.parse(raw or "", remember=False)
                self.assertEqual(addr.confidence, 0.0)
                self.assertIsNone(addr.province)

    def test_postal_code_only_does_not_set_sub_district(self):
        """รหัสไปรษณีย์อย่างเดียว → postal_code ถูก, sub_district=None"""
        addr = self.parser.parse("10110", remember=False)
        self.assertEqual(addr.postal_code, "10110")
        self.assertIsNone(addr.sub_district)

    def test_english_address(self):
        """ที่อยู่ภาษาอังกฤษ → แยกได้ถูกต้อง"""
        addr = self.parser.parse(
            "No. 55 Moo 2 Soi Sukhumvit 71 Road Sukhumvit "
            "Khwaeng Khlong Toei Nuea Khet Watthana Bangkok 10110",
            remember=False,
        )
        self.assertEqual(addr.province, "Bangkok")
        self.assertEqual(addr.district, "Watthana")
        self.assertIsNotNone(addr.house_number)


# ──────────────── Self-Learning Tests ─────────────────────────────────────────
class SelfLearningTest(ParserTestBase):

    def test_correction_is_recalled_for_exact_same_address(self):
        """หลัง correction → parse ที่อยู่เดิมต้องได้ผลที่ corrected แล้ว"""
        raw = "99 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110"
        auto = self.parser.parse(raw)
        corrected = ParsedAddress(
            raw=raw,
            house_number="99",
            road="สุขุมวิท",
            sub_district="คลองเตยเหนือ",
            district="วัฒนา",
            province="กรุงเทพมหานคร",
            postal_code="10110",
            confidence=1.0,
        )
        self.parser.learn(raw, auto, corrected)
        recalled = self.parser.parse(raw)
        self.assertEqual(recalled.confidence, 1.0)
        self.assertEqual(recalled.sub_district, "คลองเตยเหนือ")

    def test_correction_does_not_affect_different_house_number(self):
        """Correction ของ 123 ไม่ควรเปลี่ยนบ้านเลขที่ของ 124"""
        raw_123 = "123 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110"
        raw_124 = "124 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร 10110"
        corrected = ParsedAddress(
            raw=raw_123,
            house_number="123",
            province="กรุงเทพมหานคร",
        )
        self.parser.learn(raw_123, self.parser.parse(raw_123), corrected)
        result_124 = self.parser.parse(raw_124)
        self.assertEqual(result_124.house_number, "124",
                         "บ้านเลขที่ 124 ไม่ควรถูก override โดย correction ของ 123")

    def test_stats_counts_corrections(self):
        """stats() ต้องนับ correction ถูกต้อง"""
        raw = "1/1 ต.ในเมือง อ.เมืองขอนแก่น จ.ขอนแก่น 40000"
        auto = self.parser.parse(raw)
        corrected = ParsedAddress(raw=raw, province="ขอนแก่น", sub_district="ในเมือง")
        self.parser.learn(raw, auto, corrected)
        stats = self.kb.get_stats()
        self.assertGreater(stats["corrections"], 0)
        self.assertGreater(stats["verified_examples"], 0)


# ──────────────── Performance Tests ───────────────────────────────────────────
class PerformanceTest(ParserTestBase):

    def test_batch_remember_false_under_500ms_for_200_addresses(self):
        """
        parse_batch 200 addresses (remember=False) ต้องเสร็จใน < 500ms
        เพื่อให้ CSV ขนาดใหญ่ใช้งานได้จริง
        """
        addrs = [
            f"{i}/1 ถนนสุขุมวิท ต.ในเมือง อ.เมืองขอนแก่น จ.ขอนแก่น 40000"
            for i in range(200)
        ]
        t0 = time.time()
        results = self.parser.parse_batch(addrs, remember=False)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.5, f"200 addresses ใช้เวลา {elapsed*1000:.0f}ms (> 500ms)")
        correct = sum(1 for r in results if r.province == "ขอนแก่น")
        self.assertEqual(correct, 200, "ทุก address ต้องได้ province = ขอนแก่น")

    def test_no_postal_code_parse_under_50ms(self):
        """
        ที่อยู่ไม่มีรหัสไปรษณีย์ — province pre-filter ทำให้ไม่ช้าเกิน 50ms
        """
        raw = "99 ถนนสุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กรุงเทพมหานคร"
        t0 = time.time()
        for _ in range(20):
            self.parser.parse(raw, remember=False)
        elapsed = (time.time() - t0) / 20 * 1000
        self.assertLess(elapsed, 50, f"No-postal parse ใช้ {elapsed:.1f}ms (> 50ms)")

    def test_batch_keyword_usage_reduces_db_writes(self):
        """
        parse ด้วย remember=True ต้อง increment keyword usage ถูกต้อง
        (batch update ไม่ใช่ N × individual write)
        """
        raw = "99 ม.3 ถ.สุขุมวิท แขวงคลองเตยเหนือ เขตวัฒนา กทม 10110"
        # Get initial sum of usage counts
        before = self.kb.conn.execute(
            "SELECT SUM(usage_count) FROM keyword_patterns"
        ).fetchone()[0] or 0
        self.parser.parse(raw, remember=True)
        after = self.kb.conn.execute(
            "SELECT SUM(usage_count) FROM keyword_patterns"
        ).fetchone()[0] or 0
        increments = after - before
        # ควรมี increment (keywords ถูก found)
        self.assertGreater(increments, 0, "ต้องมี keyword usage increment")
        # ต้องไม่เกิน 15 (ป้องกัน loop ที่ increment ซ้ำ)
        self.assertLessEqual(increments, 15, f"increment {increments} ดูเยอะเกินไป")


# ──────────────── Knowledge Base Tests ────────────────────────────────────────
class KnowledgeBaseTest(ParserTestBase):

    def test_export_and_import_verified_examples(self):
        """export → import → verified examples ยังอยู่"""
        raw = "1/1 ต.ช้างเผือก อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50300"
        parsed = self.parser.parse(raw)
        corrected = ParsedAddress(raw=raw, province="เชียงใหม่", sub_district="ช้างเผือก")
        self.parser.learn(raw, parsed, corrected)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name
        try:
            self.kb.export_json(export_path)
            result = self.kb.import_json(export_path)
            self.assertGreater(result["examples"], 0)
        finally:
            os.unlink(export_path)

    def test_add_and_remove_custom_keyword(self):
        """เพิ่ม/ลบ custom keyword ได้"""
        self.kb.add_keyword("นิคม", "village", "th")
        keywords = dict(self.kb.get_keywords())
        self.assertIn("นิคม", keywords)
        self.assertEqual(keywords["นิคม"], "village")

        removed = self.kb.remove_keyword("นิคม")
        self.assertTrue(removed)
        keywords_after = dict(self.kb.get_keywords())
        self.assertNotIn("นิคม", keywords_after)

    def test_cannot_remove_builtin_keyword(self):
        """ลบ built-in keyword ไม่ได้"""
        removed = self.kb.remove_keyword("ถนน")   # built-in (is_custom=0)
        self.assertFalse(removed)

    def test_province_names_cache_is_populated(self):
        """_province_names() ต้อง return list ที่มี province"""
        names = self.kb._province_names()
        self.assertIn("เชียงใหม่", names)
        self.assertIn("กรุงเทพมหานคร", names)
        # ครั้งที่ 2 ต้องใช้ cache (ไม่ error)
        names2 = self.kb._province_names()
        self.assertEqual(names, names2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
