import unittest
from c55_boot import parse_boot, parse_cinit, word_bytes

class BootTests(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(ValueError):parse_boot(b'')
    def test_magic(self):
        with self.assertRaises(ValueError):parse_boot(bytes(10))
    def test_no_sections(self):
        r=parse_boot(bytes.fromhex('09aa0001234500000000'))
        self.assertEqual(r['entry_byte_address'],0x12345)
        self.assertEqual(r['sections'],[])
    def test_one_section(self):
        r=parse_boot(bytes.fromhex('09aa000123450000000100002000abcd00000000'))
        self.assertEqual(r['sections'][0]['words'],1)
        self.assertEqual(r['sections'][0]['word_address'],0x2000)
    def test_trailing(self):
        with self.assertRaises(ValueError):parse_boot(bytes.fromhex('09aa00012345000000000000'))
    def test_truncated(self):
        with self.assertRaises(ValueError):parse_boot(bytes.fromhex('09aa000123450000000100002000abcd'))
    def test_register(self):
        r=parse_boot(bytes.fromhex('09aa000123450001123456780000'))
        self.assertEqual(r['register_configuration'],[{'address':0x1234,'value':0x5678}])
    def test_chars(self):
        self.assertEqual(word_bytes(bytes.fromhex('001200010019')),bytes.fromhex('120119'))
    def test_nonchars(self):
        with self.assertRaises(ValueError):word_bytes(bytes.fromhex('0112'))
    def test_unaligned(self):
        with self.assertRaises(ValueError):word_bytes(bytes.fromhex('00'))
    def test_cinit(self):
        r=parse_cinit(bytes.fromhex('000100123400abcd0000'))
        self.assertEqual(r[0]['word_address'],0x1234)
    def test_cinit_flags(self):
        with self.assertRaises(ValueError):parse_cinit(bytes.fromhex('000100123480abcd0000'))
    def test_cinit_missing_end(self):
        with self.assertRaises(ValueError):parse_cinit(bytes.fromhex('000100123400abcd'))

if __name__=='__main__':unittest.main()
