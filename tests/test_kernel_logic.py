"""Compile and execute the actual patched helpers against side-effect-recording mocks."""
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(os.environ.get('FOSTEX_QUIRKS_SOURCE', Path(__file__).resolve().parents[1] / 'kernel-source/sound/usb/quirks.c'))

def function(source, name):
    match=re.search(r'(?m)^(?:static\s+)?(?:int|bool|u64)\s+'+re.escape(name)+r'\(',source)
    if match is None: raise ValueError('function definition not found: '+name)
    point=match.start();start=point
    brace=source.index('{',point); depth=1; end=brace+1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[start:end]

class KernelTests(unittest.TestCase):
    def test_actual_functions(self):
        s=SOURCE.read_text()
        functions='\n'.join(function(s,n) for n in ['is_fostex_dsd','fostex_dsd_format_quirk','snd_usb_select_mode_quirk'])
        head=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint64_t u64; typedef uint16_t u16; typedef int snd_pcm_format_t;
#define USB_ID(v,p) (((v)<<16)|(p))
#define USB_DIR_IN 0x80
#define USB_DIR_OUT 0
#define USB_TYPE_VENDOR 0x40
#define USB_RECIP_INTERFACE 1
#define UAC_VERSION_2 0x20
#define SNDRV_PCM_FMTBIT_DSD_U32_BE (1ULL<<52)
#define SNDRV_PCM_FMTBIT_S32_LE (1ULL<<10)
#define SNDRV_PCM_FORMAT_DSD_U32_BE 52
#define QUIRK_FLAG_ITF_USB_DSD_DAC 1
struct usb_interface { int num_altsetting; };
struct usb_device {struct usb_interface *iface;};
struct snd_usb_audio {unsigned usb_id; u64 quirk_flags; struct usb_device *dev;};
struct audioformat {int iface,protocol,endpoint,channels,fmt_bits,altsetting;u64 formats;};
static bool fostex_dsd;
static int clock_rc=16,rate_rc=-9999,validation_rc,rate_count,validation_count;
static int snd_usb_clock_find_source(struct snd_usb_audio*c,const struct audioformat*f,bool v){(void)c;(void)f;assert(!v);return clock_rc;}
static int snd_usb_fostex_set_rate(struct snd_usb_audio*c,const struct audioformat*f,int clock,int rate){(void)c;(void)f;assert(clock==16);rate_count++;validation_count++;return validation_rc?validation_rc:(rate_rc==-9999?rate:rate_rc);}

static int set_rc,ctl_rc,set_count,ctl_count,delay_count,last_index,last_value,last_iface,last_alt;
static struct usb_interface *usb_ifnum_to_if(struct usb_device *d,int i){(void)i;return d->iface;}
static int usb_set_interface(struct usb_device *d,int i,int a){(void)d;set_count++;last_iface=i;last_alt=a;return set_rc;}
static void msleep(int n){assert(n==20);delay_count++;}
static int usb_sndctrlpipe(struct usb_device*d,int i){(void)d;assert(i==0);return 0;}
static int snd_usb_ctl_msg(struct usb_device*d,int p,int request,int type,int value,int index,void*data,int len){
 (void)d;assert(p==0&&request==0&&type==0x41&&data==NULL&&len==0);
 ctl_count++;last_index=index;last_value=value;return ctl_rc;
}
static void reset(void){set_rc=ctl_rc=set_count=ctl_count=delay_count=last_index=last_value=0;clock_rc=16;rate_rc=-9999;validation_rc=rate_count=validation_count=0;}
'''
        tests=r'''
int main(void){
 struct usb_interface iface={3};struct usb_device dev={&iface};
 struct snd_usb_audio chip={USB_ID(0x1019,0x0013),0,&dev};
 struct audioformat fmt={3,UAC_VERSION_2,1,2,32,2,SNDRV_PCM_FMTBIT_DSD_U32_BE|SNDRV_PCM_FMTBIT_S32_LE};
 assert(!is_fostex_dsd(&chip));assert(snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)==0&&ctl_count==0);
 fostex_dsd=true;assert(is_fostex_dsd(&chip));
 chip.usb_id=USB_ID(0x1019,0x0012);assert(!is_fostex_dsd(&chip));
 assert(snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)==0&&ctl_count==0);chip.usb_id=USB_ID(0x1019,0x0013);
 assert(fostex_dsd_format_quirk(&chip,&fmt,4)==(SNDRV_PCM_FMTBIT_S32_LE|SNDRV_PCM_FMTBIT_DSD_U32_BE));
 assert(fostex_dsd_format_quirk(&chip,&fmt,3)==0);
 fmt.protocol=0;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));fmt.protocol=UAC_VERSION_2;
 fmt.endpoint=0x81;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));fmt.endpoint=1;
 fmt.channels=1;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));fmt.channels=2;
 fmt.fmt_bits=24;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));fmt.fmt_bits=32;
 fmt.altsetting=1;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));fmt.altsetting=2;
 iface.num_altsetting=2;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));iface.num_altsetting=3;
 dev.iface=NULL;assert(!fostex_dsd_format_quirk(&chip,&fmt,4));dev.iface=&iface;
 reset();assert(snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)==1);
 assert(set_count==1&&ctl_count==1&&delay_count==2&&last_value==1&&last_index==3&&last_iface==3&&last_alt==0);
 reset();assert(snd_usb_select_mode_quirk(&chip,&fmt,10,88200)==1);
 assert(last_value==0&&last_index==3&&ctl_count==1&&rate_count==1&&validation_count==1); /* SAME bitmap but actual PCM selected */
 reset();set_rc=-19;assert(snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)==-19&&ctl_count==0&&delay_count==0);
 reset();ctl_rc=-32;assert(snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)==-32&&ctl_count==1&&delay_count==1);
 reset();ctl_rc=-32;assert(snd_usb_select_mode_quirk(&chip,&fmt,10,88200)==-32&&ctl_count==1&&last_value==0);
 reset();clock_rc=-19;assert(snd_usb_select_mode_quirk(&chip,&fmt,52,88200)==-19&&rate_count==0);
 reset();rate_rc=-32;assert(snd_usb_select_mode_quirk(&chip,&fmt,52,88200)==-32);
 reset();rate_rc=0;assert(snd_usb_select_mode_quirk(&chip,&fmt,52,88200)==-EIO);
 reset();rate_rc=48000;assert(snd_usb_select_mode_quirk(&chip,&fmt,52,88200)==-EIO);
 reset();validation_rc=-6;assert(snd_usb_select_mode_quirk(&chip,&fmt,52,88200)==-6&&rate_count==1);
 reset();chip.usb_id=USB_ID(0x0644,0x8043);chip.quirk_flags=QUIRK_FLAG_ITF_USB_DSD_DAC;
 assert(!snd_usb_select_mode_quirk(&chip,&fmt,SNDRV_PCM_FORMAT_DSD_U32_BE,88200)&&last_index==1&&last_value==1);
 reset();fmt.formats=4;assert(!snd_usb_select_mode_quirk(&chip,&fmt,10,88200)&&last_index==1&&last_value==0);
 puts("Patched-function identity, descriptor guards, USB request, actual-format reset, error and existing-device regression assertions passed");
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'test.c';binary=Path(d)/'test';src.write_text(head+functions+tests)
            subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(src),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)

if __name__=='__main__':unittest.main()
