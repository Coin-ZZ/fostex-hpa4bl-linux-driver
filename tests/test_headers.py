import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_headers

class HeadersTests(unittest.TestCase):
    def make(self, d):
        p=Path(d); (p/'include/generated').mkdir(parents=True)
        (p/'include/generated/utsrelease.h').write_text('#define UTS_RELEASE "7.0.0-34-generic"\n')
        (p/'.config').write_bytes(b'config'); (p/'Module.symvers').write_bytes(b'symbols')
        return p
    def test_exact_and_changed(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(d)
            expected={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in check_headers.NOBLE}
            with patch.dict(check_headers.NOBLE,expected,clear=True):
                self.assertEqual(check_headers.validate(p), ('noble', 'x86_64-linux-gnu-gcc-13'))
                (p/'Module.symvers').write_bytes(b'changed')
                with self.assertRaises(ValueError): check_headers.validate(p)
    def test_wrong_abi(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(d);(p/'include/generated/utsrelease.h').write_text('#define UTS_RELEASE "7.0.0-35-generic"\n')
            with self.assertRaises(ValueError):check_headers.validate(p)
    def test_missing_headers(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):check_headers.validate(d)

class ProfileTests(HeadersTests):
    def test_resolute_and_mixed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(d)
            expected={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in check_headers.RESOLUTE}
            with patch.dict(check_headers.RESOLUTE,expected,clear=True):
                self.assertEqual(check_headers.validate(p), ('resolute','x86_64-linux-gnu-gcc-15'))
                (p/'.config').write_bytes(b'different config')
                with self.assertRaises(ValueError):check_headers.validate(p)
