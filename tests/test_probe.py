import tempfile
import unittest
from pathlib import Path
import fostex_probe as p

class DescriptorTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(p.descriptors(b''), [])
    def test_truncated_header(self):
        with self.assertRaises(ValueError): p.descriptors(b'\x02')
    def test_zero_length(self):
        with self.assertRaises(ValueError): p.descriptors(b'\x00\x01')
    def test_short_length(self):
        with self.assertRaises(ValueError): p.descriptors(b'\x01\x01')
    def test_overrun(self):
        with self.assertRaises(ValueError): p.descriptors(b'\x12\x01')
    def test_device(self):
        r = p.descriptors(bytes.fromhex('120100020000004019101300100101020301'))[0]
        self.assertEqual((r['vid'], r['pid'], r['bcd_device']), ('1019','0013','0110'))
    def test_uac2(self):
        blob = bytes.fromhex('090401010101022000 10240101000101000080020000000000 062402010418 07050105400201')
        r=p.descriptors(blob)
        self.assertTrue(r[1]['uac2_streaming']['raw_data_advertised'])
        self.assertTrue(r[1]['uac2_streaming']['pcm_advertised'])
        self.assertEqual(r[1]['uac2_streaming']['channels'], 2)
        self.assertEqual(r[2]['uac2_type_i'], {'subslot_bytes':4,'resolution_bits':24})
        self.assertEqual(r[3]['endpoint']['address'],1)
    def test_not_uac2(self):
        r=p.descriptors(bytes.fromhex('090401010101020000 062402010418'))
        self.assertNotIn('uac2_type_i',r[1])
    def test_unknown(self):
        self.assertEqual(p.descriptors(bytes.fromhex('03ffaa'))[0]['hex'],'03ffaa')
    def test_short_known(self):
        self.assertNotIn('vid',p.descriptors(bytes.fromhex('0201'))[0])
    def test_class_guard(self):
        r=p.descriptors(bytes.fromhex('0904010101ff022000 062402010418'))
        self.assertNotIn('uac2_type_i',r[1])

class ProbeTests(unittest.TestCase):
    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(p.collect(Path(d))['devices'],[])
    def test_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); dev=root/'sys/bus/usb/devices/1-2'; dev.mkdir(parents=True)
            for k,v in {'idVendor':'1019','idProduct':'0013','product':'FOSTEX USB AUDIO HP-A4','manufacturer':'FOSTEX'}.items(): (dev/k).write_text(v)
            (dev/'descriptors').write_bytes(bytes.fromhex('120100020000004019101300100101020301'))
            intf=root/'sys/bus/usb/devices/1-2:1.0'; intf.mkdir()
            (intf/'driver').symlink_to('/sys/bus/usb/drivers/snd-usb-audio')
            actual=dev/'1-2:1.0'; actual.mkdir()
            card=root/'sys/class/sound/card2'; card.mkdir(parents=True)
            (card/'device').symlink_to(actual)
            proc=root/'proc/asound/card2'; proc.mkdir(parents=True)
            (proc/'id').write_text('HPA4')
            (proc/'stream0').write_text('Playback:\n  Format: S16_LE\n  Rates: 48000\n')
            result=p.collect(root)
            self.assertEqual(len(result['devices']),1)
            found=result['devices'][0]
            self.assertEqual(found['interfaces'][0]['driver'],'snd-usb-audio')
            self.assertEqual(found['alsa'][0]['card_id'],'HPA4')
            self.assertFalse(result['hardware_verified'])
    def test_unrelated_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            dev=Path(d)/'sys/bus/usb/devices/1-2'; dev.mkdir(parents=True)
            for k,v in {'idVendor':'1234','idProduct':'5678','product':'Other'}.items(): (dev/k).write_text(v)
            self.assertEqual(p.collect(Path(d))['devices'],[])
    def test_config(self):
        self.assertIn('hw:CARD=HPA4,DEV=0',p.pcm_config('HPA4'))
        self.assertNotIn('!default',p.pcm_config('HPA4'))
    def test_pcm_container(self):
        self.assertIn("format S32_LE",p.pcm_config("HPA4"))
        self.assertNotIn("format S16_LE",p.pcm_config("HPA4"))
    def test_config_injection(self):
        for value in ['','a";','../../foo','a\nb']:
            with self.assertRaises(ValueError): p.pcm_config(value)

if __name__=='__main__': unittest.main()
