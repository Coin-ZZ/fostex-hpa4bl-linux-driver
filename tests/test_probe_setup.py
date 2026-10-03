"""Actual stream.c probe block + real prepare helpers, without device access."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_kernel_logic import function
from test_lifecycle import HEAD, MID

ROOT = Path(__file__).resolve().parents[1]

def probe_block(text):
    start = text.index('\t\tset_iface_first = false;')
    end = text.index('\n\t}\n\treturn 0;\n}', start)
    return text[start:end]

def compile_run(source):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
        src.write_text(source)
        subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-fsanitize=address,undefined',
                        str(src), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

class ProbeSetupTests(unittest.TestCase):
    def branch(self, folder):
        p = ROOT / folder / 'sound/usb'
        stream = (p / 'stream.c').read_text()
        quirk = (p / 'quirks.c').read_text()
        clock = (p / 'clock.c').read_text()
        endpoint = (p / 'endpoint.c').read_text()
        functions = '\n'.join(function(clock, n) for n in (
            'get_sample_rate_v2v3', 'snd_usb_set_sample_rate_v2v3',
            'set_sample_rate_v2v3', 'snd_usb_fostex_set_rate'))
        functions += '\n' + MID + '\n' + '\n'.join(function(quirk, n) for n in (
            'is_fostex_dsd', 'snd_usb_fostex_dsd_enabled', 'snd_usb_select_mode_quirk'))
        functions += '\n' + '\n'.join(function(endpoint, n) for n in (
            'update_clock_ref_rate', 'init_sample_rate', 'snd_usb_endpoint_prepare'))
        block = probe_block(stream)
        # The old behavior is the exact old condition, not a model of its USB calls.
        old = block.replace(' ||\n\t\t    snd_usb_fostex_dsd_enabled(chip)', '')
        old = old.replace('\t\tif (snd_usb_fostex_dsd_enabled(chip))\n\t\t\tcontinue;\n\n', '')
        assert old != block
        wrapper = '''
static void NAME(struct snd_usb_audio *chip, struct audioformat *fp) {
 int iface_no=fp->iface, protocol=fp->protocol;
 for(int altno=1;altno<=3;altno++) { bool set_iface_first;
 BLOCK
 }
}
'''
        probes = wrapper.replace('NAME', 'current_probe').replace('BLOCK', block)
        probes += wrapper.replace('NAME', 'baseline_probe').replace('BLOCK', old)
        main = r'''
static void clear(void){event_count=write_count=active_count=0;events[0]=0;}
int main(void) {
 struct usb_device dev={0};
 struct snd_usb_audio chip={USB_ID(0x1019,0x0013),0,&dev,0};
 struct audioformat fmt={1,3,UAC_VERSION_2,16,352800,SNDRV_PCM_FMTBIT_DSD_U32_BE|1024};
 hardware_rate=48000;mode=0;fostex_dsd=true;
 clear();baseline_probe(&chip,&fmt);assert(write_count==1&&active_count==3&&hardware_rate==352800);
 /* Actual new block performs no rate/alt/pitch hardware setup, irrespective of old device mode. */
 for(int old_mode=0;old_mode<2;old_mode++) {
  hardware_rate=48000;mode=old_mode;clear();current_probe(&chip,&fmt);
  assert(event_count==0&&write_count==0&&active_count==0&&hardware_rate==48000&&mode==old_mode);
 }
 /* Opt-out, same-vendor other product, and different vendor preserve baseline behavior. */
 unsigned ids[]={USB_ID(0x1019,0x0013),USB_ID(0x1019,0x0012),USB_ID(0x1234,0x0013)};
 for(int i=0;i<3;i++) {
  chip.usb_id=ids[i];fostex_dsd=(i!=0);hardware_rate=48000;clear();
  current_probe(&chip,&fmt);assert(write_count==1&&active_count==3&&hardware_rate==352800);
 }
#ifdef HAS_GENERIC_SKIP
 chip.quirk_flags=QUIRK_FLAG_SKIP_IFACE_SETUP;clear();current_probe(&chip,&fmt);assert(event_count==0);
 chip.quirk_flags=0;
#endif
 /* Deferred probe leaves no poisoned clock cache; selected PCM/DSD still uses actual strict prepare. */
 chip.usb_id=USB_ID(0x1019,0x0013);fostex_dsd=true;
 int rates[]={44100,48000,88200,96000,176400,192000,88200,176400,352800};
 for(int i=0;i<9;i++) {
  struct snd_usb_clock_ref cr={0,0,true};struct snd_usb_iface_ref ir={true};
  struct snd_usb_endpoint sync={&cr,&ir,&fmt,rates[i],i<6?10:52,129,false,true};
  hardware_rate=48000;mode=0;clear();current_probe(&chip,&fmt);assert(event_count==0);
  assert(snd_usb_endpoint_prepare(&chip,&sync)==1);
  assert(hardware_rate==rates[i]&&write_count==1&&active_count==1&&applied_mode==(i>=6));
  assert(strstr(events,"MRGVA"));
  struct snd_usb_endpoint data=sync;data.need_prepare=true;clear();
  assert(snd_usb_endpoint_prepare(&chip,&data)==1&&event_count==0);
 }
 return 0;
}
'''
        flags = '\n#define QUIRK_FLAG_SKIP_IFACE_SETUP (1ULL<<26)\n#define mutex_lock(p) ((void)(p))\n#define mutex_unlock(p) ((void)(p))\n'
        if folder == 'kernel-source': flags += '#define HAS_GENERIC_SKIP\n'
        compile_run(HEAD + flags + functions + probes + main)
        # Discovery and endpoint creation remain ahead of the only new skip gate.
        guard = stream.index('snd_usb_fostex_dsd_enabled(chip)')
        for operation in ('fp = snd_usb_get_audioformat_uac12(',
                          'snd_usb_audioformat_set_sync_ep(chip, fp);',
                          'err = snd_usb_add_audio_stream(',
                          'err = snd_usb_add_endpoint('):
            self.assertLess(stream.index(operation), guard)
        self.assertEqual(stream.count('snd_usb_fostex_dsd_enabled(chip)'), 1)
        self.assertIn('bool snd_usb_fostex_dsd_enabled(struct snd_usb_audio *chip);', (p/'quirks.h').read_text())

    def test_ubuntu_actual_probe_and_prepare(self): self.branch('kernel-source')
    def test_debian_actual_probe_and_prepare(self): self.branch('kernel-source-debian-6.12')

if __name__ == '__main__': unittest.main()
